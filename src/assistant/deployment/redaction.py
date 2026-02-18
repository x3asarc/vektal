"""Structured masking and retention/deletion SLA helpers."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


TRACE_RETENTION_DAYS = 14
AUDIT_RETENTION_DAYS = 365
LIVE_PURGE_HOURS = 48
BACKUP_PURGE_DAYS = 14

MASKED = "********"
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "client_secret",
}
REGEX_PATTERNS = [
    re.compile(r"\bsk_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\bpk_[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"(?i)(password\s*[=:]\s*)([^\s,;]+)"),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def redact_structured(payload: Any) -> Any:
    """Mask known secret fields from nested structured payloads."""
    if isinstance(payload, dict):
        output = {}
        for key, value in payload.items():
            normalized = _normalize_key(str(key))
            if normalized in SENSITIVE_KEYS or normalized.endswith("_token") or normalized.endswith("_secret"):
                output[key] = MASKED
            else:
                output[key] = redact_structured(value)
        return output
    if isinstance(payload, list):
        return [redact_structured(item) for item in payload]
    return payload


def redact_unstructured(text: str) -> str:
    """Apply regex fallback redaction for free-form logs/traces."""
    redacted = text or ""
    redacted = REGEX_PATTERNS[0].sub("sk_********", redacted)
    redacted = REGEX_PATTERNS[1].sub("pk_********", redacted)
    redacted = REGEX_PATTERNS[2].sub(r"\1********", redacted)
    return redacted


def retention_deadline(*, created_at: datetime, data_class: str) -> datetime:
    """Compute retention deadline for traces/audit classes."""
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    normalized = data_class.strip().lower()
    if normalized == "trace":
        return created_at + timedelta(days=TRACE_RETENTION_DAYS)
    if normalized == "audit":
        return created_at + timedelta(days=AUDIT_RETENTION_DAYS)
    raise ValueError(f"Unsupported data_class: {data_class}")


def purge_deadline(*, requested_at: datetime, storage_class: str) -> datetime:
    """Compute right-to-be-forgotten purge SLA deadline."""
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=timezone.utc)
    normalized = storage_class.strip().lower()
    if normalized == "live":
        return requested_at + timedelta(hours=LIVE_PURGE_HOURS)
    if normalized in {"backup", "snapshot"}:
        return requested_at + timedelta(days=BACKUP_PURGE_DAYS)
    raise ValueError(f"Unsupported storage_class: {storage_class}")


def retention_contract_snapshot(*, at_time: datetime | None = None) -> dict[str, Any]:
    """Return retention/deletion policy constants as a response-safe snapshot."""
    now_utc = at_time or _now()
    return {
        "generated_at": now_utc.isoformat(),
        "trace_retention_days": TRACE_RETENTION_DAYS,
        "audit_retention_days": AUDIT_RETENTION_DAYS,
        "live_purge_hours": LIVE_PURGE_HOURS,
        "backup_purge_days": BACKUP_PURGE_DAYS,
    }

