"""Typed event schema and validation for append-only memory logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Mapping
import uuid

SCHEMA_VERSION = 1
MAX_PAYLOAD_BYTES = 64_000
MAX_TEXT_FIELD_LENGTH = 256


class EventType(str, Enum):
    """Canonical event types for memory lifecycle and retrieval."""

    SESSION_START = "session_start"
    PRE_TOOL = "pre_tool"
    POST_TOOL = "post_tool"
    SESSION_END = "session_end"
    TASK_COMPLETE = "task_complete"
    PHASE_COMPLETE = "phase_complete"
    CONTEXT_REFRESH = "context_refresh"
    GRAPH_RETRIEVAL = "graph_retrieval"
    FALLBACK_RETRIEVAL = "fallback_retrieval"
    SENTRY_ISSUE_PULLED = "sentry_issue_pulled"
    SENTRY_ISSUE_ROUTED = "sentry_issue_routed"
    SENTRY_ISSUE_VERIFIED = "sentry_issue_verified"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def generate_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:16]}"


def _require_non_empty_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must be non-empty")
    if len(cleaned) > MAX_TEXT_FIELD_LENGTH:
        raise ValueError(f"{field_name} exceeds max length {MAX_TEXT_FIELD_LENGTH}")
    return cleaned


def _normalize_event_type(value: Any) -> str:
    if isinstance(value, EventType):
        return value.value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned in {member.value for member in EventType}:
            return cleaned
    raise ValueError(f"event_type must be one of {[member.value for member in EventType]}")


def _validate_iso_timestamp(value: Any, field_name: str) -> str:
    candidate = _require_non_empty_text(value, field_name)
    parsed = candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate
    try:
        datetime.fromisoformat(parsed)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO8601") from exc
    return candidate


def _normalize_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return dict(value)


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=True)
    if len(encoded.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError(f"payload exceeds max size {MAX_PAYLOAD_BYTES} bytes")
    return payload


@dataclass(frozen=True)
class EventEnvelope:
    """Canonical event envelope written to .memory/events JSONL files."""

    event_id: str
    event_type: str
    created_at: str
    schema_version: int
    source: str
    provider: str
    session_id: str
    scope: dict[str, Any]
    payload: dict[str, Any]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "source": self.source,
            "provider": self.provider,
            "session_id": self.session_id,
            "scope": self.scope,
            "payload": self.payload,
            "provenance": self.provenance,
        }


def create_event(
    *,
    event_type: EventType | str,
    provider: str,
    session_id: str,
    source: str,
    scope: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
    created_at: str | None = None,
    event_id: str | None = None,
) -> EventEnvelope:
    """Build and validate a canonical event envelope."""

    raw = {
        "event_id": event_id or generate_event_id(),
        "event_type": event_type,
        "created_at": created_at or utc_now_iso(),
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "provider": provider,
        "session_id": session_id,
        "scope": dict(scope or {}),
        "payload": dict(payload or {}),
        "provenance": dict(provenance or {}),
    }
    validated = validate_event(raw)
    return EventEnvelope(**validated)


def validate_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Validate event payload and return normalized dict."""

    if not isinstance(event, Mapping):
        raise ValueError("event must be an object")

    normalized: dict[str, Any] = {}
    normalized["event_id"] = _require_non_empty_text(event.get("event_id"), "event_id")
    normalized["event_type"] = _normalize_event_type(event.get("event_type"))
    normalized["created_at"] = _validate_iso_timestamp(event.get("created_at"), "created_at")

    schema_version = event.get("schema_version")
    if not isinstance(schema_version, int):
        raise ValueError("schema_version must be an integer")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    normalized["schema_version"] = schema_version

    normalized["source"] = _require_non_empty_text(event.get("source"), "source")
    normalized["provider"] = _require_non_empty_text(event.get("provider"), "provider")
    normalized["session_id"] = _require_non_empty_text(event.get("session_id"), "session_id")
    normalized["scope"] = _normalize_mapping(event.get("scope"), "scope")
    normalized["payload"] = _validate_payload(_normalize_mapping(event.get("payload"), "payload"))
    normalized["provenance"] = _normalize_mapping(event.get("provenance"), "provenance")
    return normalized
