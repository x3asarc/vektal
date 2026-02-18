"""Idempotency middleware for terminal replay-safe action execution."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from src.models import AssistantExecutionLedger, db


@dataclass(frozen=True)
class IdempotencyClaim:
    """Result of an idempotency claim attempt."""

    state: str
    http_status: int
    idempotency_key: str
    ledger_id: int | None
    status_url: str | None = None
    response_json: dict[str, Any] | None = None
    retry_allowed: bool = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_payload_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_idempotency_key(
    *,
    store_id: int | None,
    action_type: str,
    resource_id: str | None,
    payload_hash: str,
) -> str:
    raw = f"{store_id or 0}:{action_type}:{resource_id or '-'}:{payload_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _create_processing_ledger(
    *,
    idempotency_key: str,
    store_id: int | None,
    user_id: int | None,
    action_type: str,
    resource_id: str | None,
    payload_hash: str,
    correlation_id: str | None,
    policy_snapshot_hash: str | None,
    status_url: str | None,
    ttl_hours: int,
    attempt_count: int,
) -> AssistantExecutionLedger:
    now_utc = _now()
    ledger = AssistantExecutionLedger(
        idempotency_key=idempotency_key,
        store_id=store_id,
        user_id=user_id,
        action_type=action_type,
        resource_id=resource_id,
        payload_hash=payload_hash,
        correlation_id=correlation_id,
        policy_snapshot_hash=policy_snapshot_hash,
        status="PROCESSING",
        status_url=status_url,
        attempt_count=attempt_count,
        started_at=now_utc,
        completed_at=None,
        expires_at=now_utc + timedelta(hours=max(1, int(ttl_hours))),
    )
    db.session.add(ledger)
    db.session.commit()
    return ledger


def claim_execution_slot(
    *,
    store_id: int | None,
    user_id: int | None,
    action_type: str,
    resource_id: str | None,
    payload: Any,
    status_url: str | None = None,
    correlation_id: str | None = None,
    policy_snapshot_hash: str | None = None,
    ttl_hours: int = 24,
) -> IdempotencyClaim:
    """
    Claim idempotency slot for execution.

    Semantics:
    - PROCESSING -> 202 with status_url
    - SUCCESS -> cached response replay
    - FAILED -> 422 unless reset path is invoked once
    - EXPIRED -> purged and treated as new
    """
    payload_hash = compute_payload_hash(payload)
    key = build_idempotency_key(
        store_id=store_id,
        action_type=action_type,
        resource_id=resource_id,
        payload_hash=payload_hash,
    )
    now_utc = _now()
    existing = AssistantExecutionLedger.query.filter_by(idempotency_key=key).first()
    if existing is not None:
        if existing.expires_at <= now_utc:
            existing.status = "EXPIRED"
            existing.completed_at = now_utc
            db.session.flush()
            next_attempt = existing.attempt_count + 1
            db.session.delete(existing)
            db.session.commit()
            new_ledger = _create_processing_ledger(
                idempotency_key=key,
                store_id=store_id,
                user_id=user_id,
                action_type=action_type,
                resource_id=resource_id,
                payload_hash=payload_hash,
                correlation_id=correlation_id,
                policy_snapshot_hash=policy_snapshot_hash,
                status_url=status_url,
                ttl_hours=ttl_hours,
                attempt_count=next_attempt,
            )
            return IdempotencyClaim(
                state="created",
                http_status=202,
                idempotency_key=key,
                ledger_id=new_ledger.id,
                status_url=new_ledger.status_url,
            )

        if existing.status == "PROCESSING":
            return IdempotencyClaim(
                state="processing_replay",
                http_status=202,
                idempotency_key=key,
                ledger_id=existing.id,
                status_url=existing.status_url,
            )
        if existing.status == "SUCCESS":
            cached = existing.response_json if isinstance(existing.response_json, dict) else {}
            return IdempotencyClaim(
                state="success_replay",
                http_status=200,
                idempotency_key=key,
                ledger_id=existing.id,
                status_url=existing.status_url,
                response_json=cached,
            )
        if existing.status == "FAILED":
            retry_allowed = existing.attempt_count < 2
            return IdempotencyClaim(
                state="failed",
                http_status=422,
                idempotency_key=key,
                ledger_id=existing.id,
                status_url=existing.status_url,
                retry_allowed=retry_allowed,
            )

    created = _create_processing_ledger(
        idempotency_key=key,
        store_id=store_id,
        user_id=user_id,
        action_type=action_type,
        resource_id=resource_id,
        payload_hash=payload_hash,
        correlation_id=correlation_id,
        policy_snapshot_hash=policy_snapshot_hash,
        status_url=status_url,
        ttl_hours=ttl_hours,
        attempt_count=1,
    )
    return IdempotencyClaim(
        state="created",
        http_status=202,
        idempotency_key=key,
        ledger_id=created.id,
        status_url=created.status_url,
    )


def reset_failed_execution(
    *,
    idempotency_key: str,
    correlation_id: str | None = None,
    status_url: str | None = None,
    ttl_hours: int = 24,
) -> AssistantExecutionLedger | None:
    """Reset one FAILED execution into PROCESSING for the single retry path."""
    ledger = AssistantExecutionLedger.query.filter_by(idempotency_key=idempotency_key).first()
    if ledger is None or ledger.status != "FAILED" or ledger.attempt_count >= 2:
        return None
    now_utc = _now()
    ledger.status = "PROCESSING"
    ledger.error_message = None
    ledger.last_error_class = None
    ledger.completed_at = None
    ledger.status_url = status_url or ledger.status_url
    ledger.correlation_id = correlation_id or ledger.correlation_id
    ledger.started_at = now_utc
    ledger.expires_at = now_utc + timedelta(hours=max(1, int(ttl_hours)))
    ledger.attempt_count = ledger.attempt_count + 1
    db.session.commit()
    return ledger


def mark_execution_success(
    *,
    idempotency_key: str,
    response_json: dict[str, Any] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> AssistantExecutionLedger | None:
    """Mark a PROCESSING execution as SUCCESS with cached response payload."""
    ledger = AssistantExecutionLedger.query.filter_by(idempotency_key=idempotency_key).first()
    if ledger is None:
        return None
    ledger.status = "SUCCESS"
    ledger.response_json = response_json or {}
    ledger.metadata_json = metadata_json or ledger.metadata_json
    ledger.completed_at = _now()
    db.session.commit()
    return ledger


def mark_execution_failed(
    *,
    idempotency_key: str,
    error_message: str,
    error_class: str | None = None,
) -> AssistantExecutionLedger | None:
    """Mark a PROCESSING execution as FAILED."""
    ledger = AssistantExecutionLedger.query.filter_by(idempotency_key=idempotency_key).first()
    if ledger is None:
        return None
    ledger.status = "FAILED"
    ledger.error_message = error_message
    ledger.last_error_class = error_class
    ledger.completed_at = _now()
    db.session.commit()
    return ledger

