"""Chat API routes for session/message/action contracts and SSE streaming."""
from __future__ import annotations

import json
import queue
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Response, request, stream_with_context
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.api.core.errors import ProblemDetails
from src.api.core.sse import format_sse
from src.api.v1.chat import chat_bp
from src.api.v1.chat.bulk import BulkPlanError, create_or_get_bulk_job, plan_chunks
from src.api.v1.chat.schemas import (
    ChatBulkActionRequest,
    ChatActionResponse,
    ChatBlock,
    ChatDelegateRequest,
    ChatDelegateResponse,
    ChatMemoryFactResponse,
    ChatMemoryRetrieveRequest,
    ChatMemoryRetrieveResponse,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatRouteRequest,
    ChatRouteResponse,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatStreamEnvelope,
    ChatToolsResolveRequest,
    ChatToolsResolveResponse,
    EffectiveTool,
    ProductActionApprovalRequest,
    ProductActionApplyRequest,
)
from src.api.v1.chat.approvals import ApprovalError, apply_product_action, approve_product_action
from src.assistant.governance import KillSwitchBlockedError, assert_mutation_allowed
from src.assistant.instrumentation import (
    InstrumentationLinkError,
    capture_preference_signal,
    capture_verification_signal,
    extract_action_runtime_context,
)
from src.assistant.deployment import (
    persist_provider_route_event,
    resolve_correlation_id,
    resolve_provider_route,
)
from src.assistant import (
    project_effective_toolset,
    resolve_route_decision,
    retrieve_memory_facts,
    select_worker_scope,
    validate_delegation_request,
)
from src.assistant.reliability import get_runtime_policy_snapshot
from src.assistant.runtime_tier1 import build_tier1_payload
from src.assistant.runtime_tier2 import build_tier2_payload
from src.assistant.runtime_tier3 import build_tier3_payload
from src.api.v1.chat.orchestrator import (
    OrchestrationError,
    is_mutating_intent,
    prepare_single_sku_action,
)
from src.core.chat import ChatRouter, IntentType, ProductHandler, VendorHandler
from src.core.chat.handlers.generic import GenericHandler
from src.jobs.queueing import queue_for_tier_runtime
from src.models import (
    AssistantDelegationEvent,
    AssistantRouteEvent,
    ChatAction,
    ChatMessage,
    ChatSession,
    UserTier,
    db,
)


class SessionEventAnnouncer:
    """Channelized SSE announcer keyed by chat session."""

    def __init__(self) -> None:
        self._listeners: dict[int, list[queue.Queue]] = {}
        self._lock = threading.Lock()

    def listen(self, session_id: int) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=10)
        with self._lock:
            self._listeners.setdefault(session_id, []).append(q)
        return q

    def remove_listener(self, session_id: int, listener: queue.Queue) -> None:
        with self._lock:
            listeners = self._listeners.get(session_id, [])
            try:
                listeners.remove(listener)
            except ValueError:
                return
            if not listeners:
                self._listeners.pop(session_id, None)

    def announce(self, session_id: int, payload_json: str, event_type: str) -> None:
        event_name = f"chat_{event_type}"
        message = format_sse(data=payload_json, event=event_name)
        with self._lock:
            listeners = list(self._listeners.get(session_id, []))
        for listener in listeners:
            try:
                listener.put_nowait(message)
            except queue.Full:
                self.remove_listener(session_id, listener)


def _build_router() -> ChatRouter:
    router = ChatRouter()
    product_handler = ProductHandler()
    vendor_handler = VendorHandler()
    generic_handler = GenericHandler()

    router.register_handler(IntentType.ADD_PRODUCT, product_handler.handle_add_product)
    router.register_handler(IntentType.UPDATE_PRODUCT, product_handler.handle_update_product)
    router.register_handler(IntentType.SEARCH_VENDOR, vendor_handler.handle_search_vendor)
    router.register_handler(IntentType.DISCOVER_VENDOR, vendor_handler.handle_discover_vendor)
    router.register_handler(IntentType.LIST_VENDORS, vendor_handler.handle_list_vendors)
    router.register_handler(IntentType.HELP, generic_handler.handle_help)
    router.register_handler(IntentType.GET_STATUS, generic_handler.handle_status)
    router.register_handler(IntentType.UNKNOWN, generic_handler.handle_unknown)
    return router


_CHAT_ROUTER = _build_router()
_CHAT_ANNOUNCER = SessionEventAnnouncer()


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _user_tier_value() -> str:
    tier = getattr(getattr(current_user, "tier", None), "value", "tier_1")
    return str(tier).lower()


def _preference_signal_from_approval_request(payload: ProductActionApprovalRequest) -> tuple[str, str]:
    if payload.overrides:
        return "edit", "edited"
    if payload.selected_change_ids:
        return "approval", "approved_selection"
    return "approval", "approved_all"


def _session_to_response(session: ChatSession) -> ChatSessionResponse:
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        store_id=session.store_id,
        title=session.title,
        state=session.state,
        status=session.status,
        summary=session.summary,
        last_message_at=_iso(session.last_message_at),
        created_at=_iso(session.created_at),
        updated_at=_iso(session.updated_at),
    )


def _normalize_blocks(raw_blocks: Any) -> list[ChatBlock]:
    blocks: list[ChatBlock] = []
    for candidate in raw_blocks or []:
        if not isinstance(candidate, dict):
            continue
        try:
            blocks.append(ChatBlock(**candidate))
        except ValidationError:
            continue
    return blocks


def _message_to_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        session_id=message.session_id,
        user_id=message.user_id,
        role=message.role,
        content=message.content,
        blocks=_normalize_blocks(message.blocks_json),
        source_metadata=message.source_metadata,
        intent_type=message.intent_type,
        classification_method=message.classification_method,
        confidence=float(message.confidence) if message.confidence is not None else None,
        created_at=_iso(message.created_at),
        updated_at=_iso(message.updated_at),
    )


def _action_to_response(action: ChatAction) -> ChatActionResponse:
    return ChatActionResponse(
        id=action.id,
        session_id=action.session_id,
        user_id=action.user_id,
        store_id=action.store_id,
        message_id=action.message_id,
        action_type=action.action_type,
        status=action.status,
        idempotency_key=action.idempotency_key,
        payload=action.payload_json,
        result=action.result_json,
        error_message=action.error_message,
        approved_at=_iso(action.approved_at),
        applied_at=_iso(action.applied_at),
        completed_at=_iso(action.completed_at),
        created_at=_iso(action.created_at),
        updated_at=_iso(action.updated_at),
    )


def _get_session_or_error(session_id: int):
    session = ChatSession.query.filter_by(id=session_id).first()
    if session is None:
        return None, ProblemDetails.not_found("chat-session", session_id)
    if session.user_id != current_user.id:
        return None, ProblemDetails.forbidden("You do not have access to this chat session.")
    return session, None


def _resolve_store_id_or_error(requested_store_id: int | None):
    user_store = getattr(current_user, "shopify_store", None)
    if requested_store_id is not None:
        if user_store is None or user_store.id != requested_store_id:
            return None, ProblemDetails.forbidden("Requested store_id must belong to the authenticated user.")
        return requested_store_id, None
    if user_store is None:
        return None, ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store to use assistant routing endpoints.",
            status=409,
        )
    return user_store.id, None


def _build_assistant_blocks(route_result, *, extra_blocks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    response_payload = route_result.response or {}
    blocks: list[ChatBlock] = []

    if route_result.error:
        blocks.append(ChatBlock(type="alert", text=route_result.error))

    primary_text = response_payload.get("message")
    if not primary_text:
        primary_text = f"Intent classified as `{route_result.intent.type.value}`."
    blocks.append(ChatBlock(type="text", text=primary_text))

    if isinstance(response_payload.get("commands"), list):
        blocks.append(
            ChatBlock(
                type="table",
                title="commands",
                data={"rows": response_payload["commands"]},
            )
        )

    if isinstance(response_payload.get("vendors"), list):
        blocks.append(
            ChatBlock(
                type="table",
                title="vendors",
                data={"rows": response_payload["vendors"]},
            )
        )

    if isinstance(response_payload.get("actions"), list):
        blocks.append(
            ChatBlock(
                type="action",
                title="actions",
                data={"actions": response_payload["actions"]},
            )
        )

    if isinstance(response_payload.get("workflow"), dict):
        blocks.append(
            ChatBlock(
                type="progress",
                title="workflow",
                data=response_payload["workflow"],
            )
        )

    output = [block.model_dump(exclude_none=True) for block in blocks]
    if extra_blocks:
        output.extend(extra_blocks)
    return output


def _runtime_payload_from_route(route_summary: dict[str, Any], *, mutating: bool) -> dict[str, Any]:
    route_decision = route_summary.get("route_decision")
    if route_decision == "tier_3":
        return build_tier3_payload(route_summary=route_summary)
    if route_decision == "tier_2":
        return build_tier2_payload(route_summary=route_summary, mutating=mutating)
    return build_tier1_payload(route_summary=route_summary)


@chat_bp.route("/route", methods=["POST"])
@login_required
def resolve_route():
    try:
        payload = ChatRouteRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    store_id, store_error = _resolve_store_id_or_error(payload.store_id)
    if store_error:
        return store_error

    default_integrations = {"shopify": bool(getattr(current_user, "shopify_store", None))}
    active_integrations = dict(default_integrations)
    if payload.active_integrations:
        active_integrations.update(payload.active_integrations)

    route_summary = resolve_route_decision(
        user=current_user,
        content=payload.content,
        store_id=store_id,
        session_id=payload.session_id,
        rbac_role=payload.rbac_role,
        active_integrations=active_integrations,
    )
    correlation_id = resolve_correlation_id(
        provided=(payload.correlation_id or request.headers.get("X-Correlation-Id"))
    )
    provider_route = resolve_provider_route(
        correlation_id=correlation_id,
        store_id=store_id,
        intent_type=route_summary["intent_type"],
        tier=_user_tier_value(),
        failure_stage=payload.provider_failure_stage,
        budget_percent=payload.provider_budget_percent,
    )
    runtime_payload = _runtime_payload_from_route(
        route_summary,
        mutating=route_summary.get("intent_type") == "mutating_request",
    )
    runtime_payload["correlation_id"] = correlation_id
    runtime_payload["provider_route"] = {
        "provider": provider_route.selected_provider,
        "model": provider_route.selected_model,
        "route_stage": provider_route.route_stage,
        "route_index": provider_route.route_index,
        "fallback_reason_code": provider_route.fallback_reason_code,
        "policy_snapshot_hash": provider_route.policy_snapshot_hash,
    }

    event = AssistantRouteEvent(
        user_id=current_user.id,
        store_id=store_id,
        session_id=payload.session_id,
        route_decision=route_summary["route_decision"],
        intent_type=route_summary["intent_type"],
        classifier_method=route_summary["classifier_method"],
        confidence=route_summary["confidence"],
        approval_mode=route_summary["approval_mode"],
        fallback_stage=route_summary.get("fallback_stage"),
        reasons_json=route_summary["reasons"],
        effective_toolset_json=route_summary["effective_toolset"],
        policy_snapshot_hash=route_summary["policy_snapshot_hash"],
        effective_toolset_hash=route_summary["effective_toolset_hash"],
        metadata_json={"rbac_role": payload.rbac_role, "correlation_id": correlation_id},
    )
    db.session.add(event)
    provider_event = persist_provider_route_event(
        decision=provider_route,
        user_id=current_user.id,
        store_id=store_id,
        session_id=payload.session_id,
        action_id=None,
        route_event_id=None,
        intent_type=route_summary["intent_type"],
    )
    db.session.flush()
    provider_event.route_event_id = event.id
    db.session.commit()

    response = ChatRouteResponse(
        route_decision=route_summary["route_decision"],
        correlation_id=correlation_id,
        confidence=route_summary["confidence"],
        intent_type=route_summary["intent_type"],
        classifier_method=route_summary["classifier_method"],
        approval_mode=route_summary["approval_mode"],
        fallback_stage=route_summary.get("fallback_stage"),
        suggested_escalation=route_summary.get("suggested_escalation"),
        reasons=route_summary["reasons"],
        effective_toolset=[EffectiveTool(**item) for item in route_summary["effective_toolset"]],
        explainability_payload=route_summary.get("explainability_payload", {}),
        runtime_payload=runtime_payload,
        provider_route={
            "provider_route_event_id": provider_event.id,
            "provider": provider_route.selected_provider,
            "model": provider_route.selected_model,
            "route_stage": provider_route.route_stage,
            "route_index": provider_route.route_index,
            "fallback_reason_code": provider_route.fallback_reason_code,
            "policy_snapshot_hash": provider_route.policy_snapshot_hash,
        },
        route_event_id=event.id,
        policy_snapshot_hash=route_summary.get("policy_snapshot_hash"),
        effective_toolset_hash=route_summary.get("effective_toolset_hash"),
    )
    return response.model_dump(mode="json"), 200


@chat_bp.route("/tools/resolve", methods=["POST"])
@login_required
def resolve_tools():
    try:
        payload = ChatToolsResolveRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    store_id, store_error = _resolve_store_id_or_error(payload.store_id)
    if store_error:
        return store_error

    default_integrations = {"shopify": bool(getattr(current_user, "shopify_store", None))}
    active_integrations = dict(default_integrations)
    if payload.active_integrations:
        active_integrations.update(payload.active_integrations)

    effective_tools, notes = project_effective_toolset(
        user=current_user,
        store_id=store_id,
        rbac_role=payload.rbac_role,
        active_integrations=active_integrations,
    )
    response = ChatToolsResolveResponse(
        effective_toolset=[EffectiveTool(**item) for item in effective_tools],
        notes=notes,
    )
    return response.model_dump(mode="json"), 200


@chat_bp.route("/runtime/policy", methods=["POST"])
@login_required
def resolve_runtime_policy():
    """Return resolved runtime reliability policy snapshot for debug/audit surfaces."""
    payload = request.get_json(silent=True) or {}
    snapshot = get_runtime_policy_snapshot(
        provider_name=payload.get("provider_name"),
        skill_name=payload.get("skill_name"),
    )
    return {"policy": snapshot.to_dict()}, 200


@chat_bp.route("/memory/retrieve", methods=["POST"])
@login_required
def retrieve_memory():
    try:
        payload = ChatMemoryRetrieveRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    store_id, store_error = _resolve_store_id_or_error(payload.store_id)
    if store_error:
        return store_error

    rows = retrieve_memory_facts(
        store_id=store_id,
        user_id=current_user.id,
        query=payload.query,
        top_k=payload.top_k,
        scope=payload.scope,
    )
    response = ChatMemoryRetrieveResponse(
        items=[
            ChatMemoryFactResponse(
                fact_id=item["fact_id"],
                fact_key=item["fact_key"],
                fact_value_text=item["fact_value_text"],
                source=item["source"],
                trust_score=item["trust_score"],
                relevance_score=item["relevance_score"],
                provenance=item["provenance"],
                expires_at=item["expires_at"],
            )
            for item in rows
        ],
        total=len(rows),
    )
    return response.model_dump(mode="json"), 200


@chat_bp.route("/sessions", methods=["POST"])
@login_required
def create_session():
    try:
        payload = ChatSessionCreateRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    user_store = getattr(current_user, "shopify_store", None)
    store_id = payload.store_id
    if store_id is not None:
        if user_store is None or user_store.id != store_id:
            return ProblemDetails.forbidden("Session store_id must belong to the authenticated user.")
    elif user_store is not None:
        store_id = user_store.id

    session = ChatSession(
        user_id=current_user.id,
        store_id=store_id,
        title=payload.title,
        state="at_door",
        status="active",
        context_json={},
    )
    db.session.add(session)
    db.session.commit()
    return _session_to_response(session).model_dump(), 201


@chat_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    limit = min(max(request.args.get("limit", type=int) or 25, 1), 100)
    rows = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .all()
    )
    response = ChatSessionListResponse(
        sessions=[_session_to_response(row) for row in rows],
        total=len(rows),
    )
    return response.model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>", methods=["GET"])
@login_required
def get_session(session_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error
    return _session_to_response(session).model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["GET"])
@login_required
def list_messages(session_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    limit = min(max(request.args.get("limit", type=int) or 50, 1), 200)
    rows = session.messages.order_by(ChatMessage.created_at.asc()).limit(limit).all()
    response = ChatMessageListResponse(
        messages=[_message_to_response(row) for row in rows],
        total=len(rows),
    )
    return response.model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>/messages", methods=["POST"])
@login_required
def create_message(session_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    if session.status != "active":
        return ProblemDetails.business_error(
            "invalid-session-state",
            "Invalid Session State",
            "Messages can only be created while the session is active.",
            status=409,
        )

    try:
        payload = ChatMessageCreateRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    if payload.idempotency_key:
        existing = ChatAction.query.filter_by(idempotency_key=payload.idempotency_key).first()
        if existing is not None:
            return ProblemDetails.business_error(
                "duplicate-idempotency-key",
                "Duplicate Idempotency Key",
                "An action with this idempotency key already exists.",
                status=409,
            )

    now = datetime.now(timezone.utc)
    correlation_id = resolve_correlation_id(
        provided=(payload.correlation_id or request.headers.get("X-Correlation-Id"))
    )
    route_result = _CHAT_ROUTER.route(payload.content)
    rbac_role = "manager" if current_user.tier == UserTier.TIER_3 else "member"
    active_integrations = {"shopify": bool(getattr(current_user, "shopify_store", None))}
    route_summary = resolve_route_decision(
        user=current_user,
        content=payload.content,
        store_id=session.store_id,
        session_id=session.id,
        rbac_role=rbac_role,
        active_integrations=active_integrations,
    )
    mutating_request = is_mutating_intent(route_result.intent.type.value)
    provider_failure_stage = None
    provider_budget_percent = None
    if isinstance(payload.action_hints, dict):
        provider_failure_stage = payload.action_hints.get("provider_failure_stage")
        provider_budget_percent = payload.action_hints.get("provider_budget_percent")
    provider_route = resolve_provider_route(
        correlation_id=correlation_id,
        store_id=session.store_id,
        intent_type=route_summary["intent_type"],
        tier=_user_tier_value(),
        failure_stage=provider_failure_stage,
        budget_percent=provider_budget_percent,
    )
    runtime_payload = _runtime_payload_from_route(route_summary, mutating=mutating_request)
    runtime_payload["correlation_id"] = correlation_id
    runtime_payload["provider_route"] = {
        "provider": provider_route.selected_provider,
        "model": provider_route.selected_model,
        "route_stage": provider_route.route_stage,
        "route_index": provider_route.route_index,
        "fallback_reason_code": provider_route.fallback_reason_code,
        "policy_snapshot_hash": provider_route.policy_snapshot_hash,
    }
    route_event = AssistantRouteEvent(
        user_id=current_user.id,
        store_id=session.store_id,
        session_id=session.id,
        route_decision=route_summary["route_decision"],
        intent_type=route_summary["intent_type"],
        classifier_method=route_summary["classifier_method"],
        confidence=route_summary["confidence"],
        approval_mode=route_summary["approval_mode"],
        fallback_stage=route_summary.get("fallback_stage"),
        reasons_json=route_summary["reasons"],
        effective_toolset_json=route_summary["effective_toolset"],
        policy_snapshot_hash=route_summary["policy_snapshot_hash"],
        effective_toolset_hash=route_summary["effective_toolset_hash"],
        metadata_json={
            "rbac_role": rbac_role,
            "source": "session_message",
            "correlation_id": correlation_id,
        },
    )
    db.session.add(route_event)
    db.session.flush()

    prepared_action = None
    semantic_block = None
    if mutating_request:
        try:
            assert_mutation_allowed(
                store_id=session.store_id,
                action_name="chat.message.mutation",
            )
        except KillSwitchBlockedError as exc:
            semantic_block = {
                "type": "action",
                "title": "execution_paused",
                "data": {
                    "error_type": exc.error_type,
                    "scope_kind": exc.decision.scope_kind,
                    "mode": exc.decision.mode,
                    "switch_id": exc.decision.switch_id,
                    "reason": exc.decision.reason,
                },
            }

    if semantic_block is None and mutating_request and route_summary.get("approval_mode") == "blocked_write":
        semantic_block = {
            "type": "action",
            "title": "tier_upgrade_required",
            "data": {
                "route_decision": route_summary.get("route_decision"),
                "fallback_stage": route_summary.get("fallback_stage"),
                "suggested_escalation": route_summary.get("suggested_escalation"),
                "reason": "Write actions require a higher capability tier.",
            },
        }
    elif semantic_block is None and mutating_request:
        try:
            prepared_action = prepare_single_sku_action(
                session=session,
                intent_type=route_result.intent.type.value,
                intent_entities=route_result.intent.entities,
                route_response=route_result.response or {},
                raw_message=payload.content,
                action_hints=payload.action_hints or {},
                actor_user_id=current_user.id,
            )
        except OrchestrationError as exc:
            return ProblemDetails.business_error(
                exc.error_type,
                exc.title,
                exc.detail,
                status=exc.status,
                **(exc.extensions or {}),
            )

    user_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="user",
        content=payload.content,
        blocks_json=[{"type": "text", "text": payload.content}],
        source_metadata={"origin": "chat-input"},
    )
    db.session.add(user_message)
    db.session.flush()

    extra_blocks = list(prepared_action.assistant_blocks) if prepared_action else []
    if semantic_block:
        extra_blocks.append(semantic_block)
    assistant_blocks = _build_assistant_blocks(route_result, extra_blocks=extra_blocks or None)
    assistant_content = next(
        (block.get("text") for block in assistant_blocks if block.get("type") == "text" and block.get("text")),
        "Acknowledged.",
    )

    assistant_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="assistant",
        content=assistant_content,
        blocks_json=assistant_blocks,
        source_metadata={
            "handler_name": route_result.handler_name,
            "router_error": route_result.error,
            "router_response": route_result.response,
            "route_summary": route_summary,
            "runtime_payload": runtime_payload,
            "correlation_id": correlation_id,
        },
        intent_type=route_result.intent.type.value,
        classification_method=route_result.intent.method,
        confidence=route_result.intent.confidence,
    )
    db.session.add(assistant_message)
    db.session.flush()

    action = None
    if prepared_action is not None:
        payload_json = dict(prepared_action.payload_json)
        payload_json["runtime"] = {
            "route_decision": route_summary.get("route_decision"),
            "runtime_mode": runtime_payload.get("mode"),
            "action_kind": "write",
            "approval_mode": route_summary.get("approval_mode"),
            "fallback_stage": route_summary.get("fallback_stage"),
            "correlation_id": correlation_id,
            "provider_route": runtime_payload.get("provider_route"),
        }
        action = ChatAction(
            session_id=session.id,
            user_id=current_user.id,
            store_id=session.store_id,
            message_id=assistant_message.id,
            action_type=prepared_action.action_type,
            status=prepared_action.status,
            idempotency_key=payload.idempotency_key,
            payload_json=payload_json,
        )
        db.session.add(action)
        session.state = "in_house"

    persist_provider_route_event(
        decision=provider_route,
        user_id=current_user.id,
        store_id=session.store_id,
        session_id=session.id,
        action_id=action.id if action is not None else None,
        route_event_id=route_event.id,
        intent_type=route_summary["intent_type"],
    )

    session.last_message_at = now
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return ProblemDetails.business_error(
            "duplicate-idempotency-key",
            "Duplicate Idempotency Key",
            "An action with this idempotency key already exists.",
            status=409,
        )

    message_envelope = ChatStreamEnvelope(
        session_id=session.id,
        event="assistant_update",
        emitted_at=now,
        payload={
            "message_id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "blocks": assistant_message.blocks_json,
            "intent_type": assistant_message.intent_type,
        },
    )
    _CHAT_ANNOUNCER.announce(
        session.id,
        json.dumps(message_envelope.model_dump(mode="json")),
        event_type="message",
    )

    if action is not None:
        action_envelope = ChatStreamEnvelope(
            session_id=session.id,
            event="action_state",
            emitted_at=now,
            payload={
                "action_id": action.id,
                "action_type": action.action_type,
                "status": action.status,
                "idempotency_key": action.idempotency_key,
            },
        )
        _CHAT_ANNOUNCER.announce(
            session.id,
            json.dumps(action_envelope.model_dump(mode="json")),
            event_type="action",
        )

    response = ChatMessageCreateResponse(
        session=_session_to_response(session),
        user_message=_message_to_response(user_message),
        assistant_message=_message_to_response(assistant_message),
        action=_action_to_response(action) if action is not None else None,
    )
    return response.model_dump(), 201


@chat_bp.route("/sessions/<int:session_id>/bulk/actions", methods=["POST"])
@login_required
def create_bulk_action(session_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    if session.status != "active":
        return ProblemDetails.business_error(
            "invalid-session-state",
            "Invalid Session State",
            "Bulk actions can only be created while the session is active.",
            status=409,
        )
    if session.store_id is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before preparing bulk chat actions.",
            status=409,
        )

    try:
        payload = ChatBulkActionRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    if payload.idempotency_key:
        existing = ChatAction.query.filter_by(idempotency_key=payload.idempotency_key).first()
        if existing is not None:
            return ProblemDetails.business_error(
                "duplicate-idempotency-key",
                "Duplicate Idempotency Key",
                "An action with this idempotency key already exists.",
                status=409,
            )

    try:
        chunk_plan = plan_chunks(raw_skus=payload.skus, requested_chunk_size=payload.requested_chunk_size)
    except BulkPlanError as exc:
        return ProblemDetails.business_error(
            exc.error_type,
            exc.title,
            exc.detail,
            status=exc.status,
        )

    now = datetime.now(timezone.utc)
    correlation_id = resolve_correlation_id(
        provided=request.headers.get("X-Correlation-Id")
    )
    user_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="user",
        content=payload.content,
        blocks_json=[
            {
                "type": "action",
                "title": "bulk_request",
                "data": {
                    "operation": payload.operation,
                    "sku_count": chunk_plan.total_skus,
                    "chunk_count": len(chunk_plan.chunks),
                },
            }
        ],
        source_metadata={
            "origin": "chat-bulk-input",
            "operation": payload.operation,
            "sku_count": chunk_plan.total_skus,
        },
    )
    db.session.add(user_message)
    db.session.flush()

    assistant_blocks = [
        {
            "type": "text",
            "text": (
                f"Prepared bulk {payload.operation} action for {chunk_plan.total_skus} SKU(s) "
                f"across {len(chunk_plan.chunks)} chunk(s). Approve before apply."
            ),
        },
        {
            "type": "progress",
            "title": "bulk_chunk_plan",
            "data": {
                "total_skus": chunk_plan.total_skus,
                "chunk_count": len(chunk_plan.chunks),
                "target_chunk_size": chunk_plan.target_chunk_size,
                "max_chunk_inputs": chunk_plan.max_chunk_inputs,
            },
        },
        {
            "type": "action",
            "title": "product_scope_approval",
            "data": {
                "approval_scope": "product",
                "dry_run_required": True,
                "next": ["approve", "apply"],
            },
        },
    ]
    assistant_message = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="assistant",
        content=assistant_blocks[0]["text"],
        blocks_json=assistant_blocks,
        source_metadata={
            "handler_name": "bulk_action",
            "operation": payload.operation,
        },
        intent_type=payload.operation,
        classification_method="bulk",
        confidence=1.0,
    )
    db.session.add(assistant_message)
    db.session.flush()

    action = ChatAction(
        session_id=session.id,
        user_id=current_user.id,
        store_id=session.store_id,
        message_id=assistant_message.id,
        action_type=payload.operation,
        status="awaiting_approval",
        idempotency_key=payload.idempotency_key,
        payload_json={
            "bulk": True,
            "source": "chat_bulk",
            "correlation_id": correlation_id,
            "tier": _user_tier_value(),
            "operation": payload.operation,
            "mode": payload.mode or "immediate",
            "dry_run_required": True,
            "approval_scope": "product",
            "requires_product_approval": True,
            "runtime": {
                "route_decision": _user_tier_value(),
                "runtime_mode": "governed_skill_runtime",
                "action_kind": "write",
                "correlation_id": correlation_id,
            },
            "action_hints": payload.action_hints or {},
            "admin_concurrency_cap": payload.admin_concurrency_cap,
            "chunk_plan": chunk_plan.to_payload(),
            "chunk_results": {},
        },
    )
    db.session.add(action)
    db.session.flush()

    create_or_get_bulk_job(
        action=action,
        total_items=chunk_plan.total_skus,
        chunk_count=len(chunk_plan.chunks),
    )

    session.state = "in_house"
    session.last_message_at = now
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return ProblemDetails.business_error(
            "duplicate-idempotency-key",
            "Duplicate Idempotency Key",
            "An action with this idempotency key already exists.",
            status=409,
        )

    message_envelope = ChatStreamEnvelope(
        session_id=session.id,
        event="assistant_update",
        emitted_at=now,
        payload={
            "message_id": assistant_message.id,
            "role": assistant_message.role,
            "content": assistant_message.content,
            "blocks": assistant_message.blocks_json,
            "intent_type": assistant_message.intent_type,
        },
    )
    _CHAT_ANNOUNCER.announce(
        session.id,
        json.dumps(message_envelope.model_dump(mode="json")),
        event_type="message",
    )

    action_envelope = ChatStreamEnvelope(
        session_id=session.id,
        event="action_state",
        emitted_at=now,
        payload={
            "action_id": action.id,
            "action_type": action.action_type,
            "status": action.status,
            "idempotency_key": action.idempotency_key,
        },
    )
    _CHAT_ANNOUNCER.announce(
        session.id,
        json.dumps(action_envelope.model_dump(mode="json")),
        event_type="action",
    )

    response = ChatMessageCreateResponse(
        session=_session_to_response(session),
        user_message=_message_to_response(user_message),
        assistant_message=_message_to_response(assistant_message),
        action=_action_to_response(action),
    )
    return response.model_dump(), 201


@chat_bp.route("/sessions/<int:session_id>/actions/<int:action_id>", methods=["GET"])
@login_required
def get_action(session_id: int, action_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    action = ChatAction.query.filter_by(id=action_id, session_id=session.id).first()
    if action is None:
        return ProblemDetails.not_found("chat-action", action_id)
    if action.user_id != current_user.id:
        return ProblemDetails.forbidden("You do not have access to this chat action.")

    return _action_to_response(action).model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>/actions/<int:action_id>/approve", methods=["POST"])
@login_required
def approve_action(session_id: int, action_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    action = ChatAction.query.filter_by(id=action_id, session_id=session.id).first()
    if action is None:
        return ProblemDetails.not_found("chat-action", action_id)
    if action.user_id != current_user.id:
        return ProblemDetails.forbidden("You do not have access to this chat action.")
    try:
        assert_mutation_allowed(
            store_id=action.store_id or session.store_id,
            action_name=f"chat.approve_action:{action.action_type}",
        )
    except KillSwitchBlockedError as exc:
        return ProblemDetails.business_error(
            exc.error_type,
            exc.title,
            exc.detail,
            status=exc.status,
            **(exc.extensions or {}),
        )

    try:
        payload = ProductActionApprovalRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    if bool((action.payload_json or {}).get("bulk")):
        if action.status not in {"awaiting_approval", "approved"}:
            return ProblemDetails.business_error(
                "invalid-action-state",
                "Invalid Action State",
                f"Action is {action.status}. Only awaiting_approval actions may be approved.",
                status=409,
            )
        payload_json = dict(action.payload_json or {})
        payload_json["approval"] = {
            "scope": "product",
            "comment": payload.comment,
            "approved_change_ids": payload.selected_change_ids,
            "rejected_change_ids": [],
        }
        action.payload_json = payload_json
        action.status = "approved"
        action.approved_at = datetime.now(timezone.utc)
        action.error_message = None
        signal_kind, preference_signal = _preference_signal_from_approval_request(payload)
        runtime_ctx = extract_action_runtime_context(action, fallback_tier=_user_tier_value())
        try:
            capture_preference_signal(
                action=action,
                user_id=current_user.id,
                store_id=action.store_id or session.store_id,
                session_id=session.id,
                tier=runtime_ctx.tier,
                correlation_id=runtime_ctx.correlation_id,
                signal_kind=signal_kind,
                preference_signal=preference_signal,
                selected_change_count=len(payload.selected_change_ids),
                override_count=len(payload.overrides),
                comment=payload.comment,
                reasoning_trace_tokens=runtime_ctx.reasoning_trace_tokens,
                cost_usd=runtime_ctx.cost_usd,
                metadata_json={"bulk": True, "approval_scope": "product"},
                require_link=True,
            )
        except InstrumentationLinkError as exc:
            db.session.rollback()
            return ProblemDetails.business_error(
                "instrumentation-correlation-required",
                "Instrumentation Link Required",
                str(exc),
                status=409,
            )
        db.session.commit()
        approved_action = action
    else:
        try:
            approved_action = approve_product_action(
                action=action,
                actor_user_id=current_user.id,
                selected_change_ids=payload.selected_change_ids,
                overrides=[item.model_dump() for item in payload.overrides],
                comment=payload.comment,
            )
        except ApprovalError as exc:
            return ProblemDetails.business_error(
                exc.error_type,
                exc.title,
                exc.detail,
                status=exc.status,
                **(exc.extensions or {}),
            )

    action_envelope = ChatStreamEnvelope(
        session_id=session.id,
        event="action_state",
        emitted_at=datetime.now(timezone.utc),
        payload={
            "action_id": approved_action.id,
            "action_type": approved_action.action_type,
            "status": approved_action.status,
        },
    )
    _CHAT_ANNOUNCER.announce(
        session.id,
        json.dumps(action_envelope.model_dump(mode="json")),
        event_type="action",
    )
    return _action_to_response(approved_action).model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>/actions/<int:action_id>/apply", methods=["POST"])
@login_required
def apply_action(session_id: int, action_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    action = ChatAction.query.filter_by(id=action_id, session_id=session.id).first()
    if action is None:
        return ProblemDetails.not_found("chat-action", action_id)
    if action.user_id != current_user.id:
        return ProblemDetails.forbidden("You do not have access to this chat action.")
    try:
        assert_mutation_allowed(
            store_id=action.store_id or session.store_id,
            action_name=f"chat.apply_action:{action.action_type}",
        )
    except KillSwitchBlockedError as exc:
        return ProblemDetails.business_error(
            exc.error_type,
            exc.title,
            exc.detail,
            status=exc.status,
            **(exc.extensions or {}),
        )

    try:
        payload = ProductActionApplyRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    if bool((action.payload_json or {}).get("bulk")):
        if action.status != "approved":
            return ProblemDetails.business_error(
                "approval-required",
                "Approval Required",
                "Approve this bulk action before apply.",
                status=409,
            )
        from src.celery_app import app as celery_app

        payload_json = dict(action.payload_json or {})
        mode = payload.mode or payload_json.get("mode")
        task_result = celery_app.send_task(
            "src.tasks.chat_bulk.run_chat_bulk_action",
            kwargs={
                "action_id": action.id,
                "actor_user_id": current_user.id,
                "mode": mode,
                "job_id": payload_json.get("job_id"),
            },
        )
        action.status = "applying"
        action.applied_at = datetime.now(timezone.utc)
        action.result_json = {
            "status": "queued",
            "task_id": task_result.id,
            "job_id": payload_json.get("job_id"),
        }
        execution = dict(payload_json.get("bulk_execution") or {})
        execution["task_id"] = task_result.id
        execution["queued_at"] = datetime.now(timezone.utc).isoformat()
        payload_json["bulk_execution"] = execution
        action.payload_json = payload_json
        runtime_ctx = extract_action_runtime_context(action, fallback_tier=_user_tier_value())
        try:
            capture_verification_signal(
                action=action,
                user_id=current_user.id,
                store_id=action.store_id or session.store_id,
                session_id=session.id,
                verification_event_id=None,
                verification_status="deferred",
                oracle_signal=False,
                attempt_count=1,
                waited_seconds=0,
                tier=runtime_ctx.tier,
                correlation_id=runtime_ctx.correlation_id,
                reasoning_trace_tokens=runtime_ctx.reasoning_trace_tokens,
                cost_usd=runtime_ctx.cost_usd,
                metadata_json={
                    "bulk": True,
                    "result_status": "queued",
                    "task_id": task_result.id,
                    "job_id": payload_json.get("job_id"),
                },
                require_link=True,
            )
        except InstrumentationLinkError as exc:
            db.session.rollback()
            return ProblemDetails.business_error(
                "instrumentation-correlation-required",
                "Instrumentation Link Required",
                str(exc),
                status=409,
            )
        db.session.commit()
        applied_action = action
    else:
        try:
            applied_action = apply_product_action(
                action=action,
                actor_user_id=current_user.id,
                mode=payload.mode,
            )
        except ApprovalError as exc:
            return ProblemDetails.business_error(
                exc.error_type,
                exc.title,
                exc.detail,
                status=exc.status,
                **(exc.extensions or {}),
            )

    action_envelope = ChatStreamEnvelope(
        session_id=session.id,
        event="action_state",
        emitted_at=datetime.now(timezone.utc),
        payload={
            "action_id": applied_action.id,
            "action_type": applied_action.action_type,
            "status": applied_action.status,
            "result": applied_action.result_json,
        },
    )
    _CHAT_ANNOUNCER.announce(
        session.id,
        json.dumps(action_envelope.model_dump(mode="json")),
        event_type="action",
    )
    return _action_to_response(applied_action).model_dump(), 200


@chat_bp.route("/sessions/<int:session_id>/actions/<int:action_id>/delegate", methods=["POST"])
@login_required
def delegate_action(session_id: int, action_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    action = ChatAction.query.filter_by(id=action_id, session_id=session.id).first()
    if action is None:
        return ProblemDetails.not_found("chat-action", action_id)
    if action.user_id != current_user.id:
        return ProblemDetails.forbidden("You do not have access to this chat action.")

    if current_user.tier != UserTier.TIER_3:
        return ProblemDetails.business_error(
            "tier-insufficient",
            "Tier Insufficient",
            "Delegation is available only for Tier 3 users.",
            status=403,
        )

    try:
        payload = ChatDelegateRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    budget = payload.budget or {}
    allowed, reason = validate_delegation_request(
        depth=payload.depth,
        fan_out=payload.fan_out,
        budget=budget,
    )

    store_id = session.store_id or getattr(getattr(current_user, "shopify_store", None), "id", None)
    effective_tools, _ = project_effective_toolset(
        user=current_user,
        store_id=store_id,
        rbac_role="manager",
        active_integrations={"shopify": bool(getattr(current_user, "shopify_store", None))},
    )
    effective_tool_ids = [item["tool_id"] for item in effective_tools]
    worker_scope, blocked_tools = select_worker_scope(
        effective_tool_ids=effective_tool_ids,
        requested_tools=payload.requested_tools,
    )

    status = "spawned"
    reason_text = reason
    if not allowed:
        status = "blocked"
    elif not worker_scope:
        status = "blocked"
        reason_text = "No permitted worker tools remain after policy projection."

    event = AssistantDelegationEvent(
        session_id=session.id,
        action_id=action.id,
        user_id=current_user.id,
        store_id=store_id,
        parent_request_id=payload.parent_request_id,
        request_id=f"deleg-{uuid.uuid4().hex[:24]}",
        depth=payload.depth,
        fan_out=payload.fan_out,
        status=status,
        worker_tool_scope_json=worker_scope,
        budget_json=budget,
        reason=reason_text,
        fallback_stage="none" if status == "spawned" else "delegation_blocked",
        metadata_json={"blocked_tools": blocked_tools},
    )
    db.session.add(event)
    db.session.flush()
    task_id = None
    task_queue = None
    if status == "spawned":
        from src.celery_app import app as celery_app

        task_queue = queue_for_tier_runtime("tier_3")
        task_payload = {
            "delegation_event_id": event.id,
            "action_id": action.id,
            "session_id": session.id,
            "worker_tool_scope": worker_scope,
            "depth": payload.depth,
            "fan_out": payload.fan_out,
            "fallback_stage": "delegation_spawned",
        }
        try:
            result = celery_app.send_task(
                "src.tasks.assistant_runtime.run_tier_runtime",
                kwargs={"route_decision": "tier_3", "payload": task_payload},
                queue=task_queue,
            )
            task_id = result.id
        except Exception:
            # Keep delegation auditable even when queue infra is unavailable.
            task_id = f"local-{uuid.uuid4().hex[:20]}"
        metadata_json = dict(event.metadata_json or {})
        metadata_json["task_id"] = task_id
        metadata_json["queue"] = task_queue
        event.metadata_json = metadata_json
        event.status = "running"
        event.fallback_stage = "delegation_running"

    db.session.commit()

    response = ChatDelegateResponse(
        delegation_event_id=event.id,
        status=event.status,
        worker_tool_scope=worker_scope,
        blocked_tools=blocked_tools,
        task_id=task_id,
        queue=task_queue,
        reason=reason_text,
    )
    return response.model_dump(mode="json"), 200


@chat_bp.route("/sessions/<int:session_id>/stream", methods=["GET"])
@login_required
def stream_session(session_id: int):
    session, error = _get_session_or_error(session_id)
    if error:
        return error

    def generate():
        listener = _CHAT_ANNOUNCER.listen(session.id)
        initial = ChatStreamEnvelope(
            session_id=session.id,
            event="session_state",
            emitted_at=datetime.now(timezone.utc),
            payload={
                "session_id": session.id,
                "state": session.state,
                "status": session.status,
            },
        )
        yield format_sse(
            data=json.dumps(initial.model_dump(mode="json")),
            event="chat_session_state",
        )

        try:
            while True:
                try:
                    msg = listener.get(timeout=15)
                    yield msg
                except queue.Empty:
                    heartbeat = ChatStreamEnvelope(
                        session_id=session.id,
                        event="heartbeat",
                        emitted_at=datetime.now(timezone.utc),
                        payload={"state": session.state},
                    )
                    yield format_sse(
                        data=json.dumps(heartbeat.model_dump(mode="json")),
                        event="chat_heartbeat",
                    )
        except GeneratorExit:
            _CHAT_ANNOUNCER.remove_listener(session.id, listener)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
