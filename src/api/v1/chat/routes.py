"""Chat API routes for session/message/action contracts and SSE streaming."""
from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone
from typing import Any

from flask import Response, request, stream_with_context
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.api.core.errors import ProblemDetails
from src.api.core.sse import format_sse
from src.api.v1.chat import chat_bp
from src.api.v1.chat.schemas import (
    ChatActionResponse,
    ChatBlock,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatStreamEnvelope,
)
from src.core.chat import ChatRouter, IntentType, ProductHandler, VendorHandler
from src.core.chat.handlers.generic import GenericHandler
from src.models import ChatAction, ChatMessage, ChatSession, db


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


def _build_assistant_blocks(route_result) -> list[dict[str, Any]]:
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

    return [block.model_dump(exclude_none=True) for block in blocks]


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

    now = datetime.now(timezone.utc)
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

    route_result = _CHAT_ROUTER.route(payload.content)
    assistant_blocks = _build_assistant_blocks(route_result)
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
        },
        intent_type=route_result.intent.type.value,
        classification_method=route_result.intent.method,
        confidence=route_result.intent.confidence,
    )
    db.session.add(assistant_message)
    db.session.flush()

    action = None
    if route_result.intent.type not in {IntentType.HELP, IntentType.GET_STATUS, IntentType.UNKNOWN}:
        action = ChatAction(
            session_id=session.id,
            user_id=current_user.id,
            store_id=session.store_id,
            message_id=assistant_message.id,
            action_type=route_result.intent.type.value,
            status="drafted",
            idempotency_key=payload.idempotency_key,
            payload_json={
                "intent": route_result.intent.type.value,
                "entities": route_result.intent.entities,
                "router_method": route_result.intent.method,
                "router_response": route_result.response,
            },
        )
        db.session.add(action)
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
