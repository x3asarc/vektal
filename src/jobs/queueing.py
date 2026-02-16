"""Queue topology and routing helpers for Phase 6."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict


CONTROL_QUEUE = "control"

INTERACTIVE_QUEUES: Dict[str, str] = {
    "tier_1": "interactive.t1",
    "tier_2": "interactive.t2",
    "tier_3": "interactive.t3",
}

BATCH_QUEUES: Dict[str, str] = {
    "tier_1": "batch.t1",
    "tier_2": "batch.t2",
    "tier_3": "batch.t3",
}

ASSISTANT_RUNTIME_QUEUES: Dict[str, str] = {
    "tier_1": "assistant.t1",
    "tier_2": "assistant.t2",
    "tier_3": "assistant.t3",
}

ASSISTANT_TIER3_DEAD_LETTER_QUEUE = "assistant.t3.dlq"
ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_DEFAULT = 900
ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_CAP = 3600

ALL_QUEUES = (
    tuple(INTERACTIVE_QUEUES.values())
    + tuple(BATCH_QUEUES.values())
    + tuple(ASSISTANT_RUNTIME_QUEUES.values())
    + (ASSISTANT_TIER3_DEAD_LETTER_QUEUE,)
    + (CONTROL_QUEUE,)
)

WORKER_QUEUE_SPLIT = {
    "celery_worker": [CONTROL_QUEUE, *INTERACTIVE_QUEUES.values()],
    "celery_scraper": [*BATCH_QUEUES.values()],
    "celery_assistant": [*ASSISTANT_RUNTIME_QUEUES.values(), ASSISTANT_TIER3_DEAD_LETTER_QUEUE],
}

TASK_ROUTES = {
    "src.tasks.ingest.start_ingest_task": {"queue": CONTROL_QUEUE},
    "src.tasks.ingest.ingest_chunk_t1": {"queue": BATCH_QUEUES["tier_1"]},
    "src.tasks.ingest.ingest_chunk_t2": {"queue": BATCH_QUEUES["tier_2"]},
    "src.tasks.ingest.ingest_chunk_t3": {"queue": BATCH_QUEUES["tier_3"]},
    "src.tasks.audits.dispatch_pending_audits": {"queue": CONTROL_QUEUE},
    "src.tasks.audits.audit_run": {"queue": INTERACTIVE_QUEUES["tier_2"]},
    "src.tasks.control.finalize_job": {"queue": CONTROL_QUEUE},
    "src.tasks.control.cleanup_old_jobs": {"queue": CONTROL_QUEUE},
    "src.tasks.control.cancel_job": {"queue": CONTROL_QUEUE},
    "src.tasks.resolution_apply.apply_resolution_batch": {"queue": BATCH_QUEUES["tier_2"]},
    "src.tasks.chat_bulk.run_chat_bulk_action": {"queue": BATCH_QUEUES["tier_2"]},
    "src.tasks.enrichment.run_enrichment_batch": {"queue": BATCH_QUEUES["tier_2"]},
    "src.tasks.assistant_runtime.run_tier_runtime": {"queue": ASSISTANT_RUNTIME_QUEUES["tier_2"]},
    "src.tasks.scrape_jobs.run_scraper_job_t1": {"queue": BATCH_QUEUES["tier_1"]},
    "src.tasks.scrape_jobs.run_scraper_job_t2": {"queue": BATCH_QUEUES["tier_2"]},
    "src.tasks.scrape_jobs.run_scraper_job_t3": {"queue": BATCH_QUEUES["tier_3"]},
}


def normalize_tier(tier: str | None) -> str:
    """Normalize model tier enum values to route keys."""
    if not tier:
        return "tier_1"
    value = str(tier).lower()
    if value.endswith("tier_3") or value.endswith("t3"):
        return "tier_3"
    if value.endswith("tier_2") or value.endswith("t2"):
        return "tier_2"
    return "tier_1"


def queue_for_tier(tier: str | None, kind: str = "batch") -> str:
    """Return queue name for tier and workload kind."""
    tier_key = normalize_tier(tier)
    if kind == "interactive":
        return INTERACTIVE_QUEUES[tier_key]
    if kind == "assistant":
        return ASSISTANT_RUNTIME_QUEUES[tier_key]
    return BATCH_QUEUES[tier_key]


def queue_for_tier_runtime(tier: str | None) -> str:
    """Return assistant runtime queue for tier."""
    tier_key = normalize_tier(tier)
    return ASSISTANT_RUNTIME_QUEUES[tier_key]


def cap_tier3_message_ttl(requested_ttl_seconds: int | None) -> int:
    """Clamp requested Tier 3 message TTL to configured bounds."""
    if requested_ttl_seconds is None:
        return ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_DEFAULT
    try:
        value = int(requested_ttl_seconds)
    except Exception:
        return ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_DEFAULT
    if value <= 0:
        return ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_DEFAULT
    return min(value, ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_CAP)


def parse_queued_at(value: str | None) -> datetime | None:
    """Parse queued timestamp from ISO text."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_tier3_payload_expired(payload: dict | None, *, now_utc: datetime | None = None) -> tuple[bool, int, int]:
    """
    Evaluate whether Tier 3 payload exceeded TTL.

    Returns `(expired, age_seconds, ttl_seconds)`.
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    if not isinstance(payload, dict):
        ttl = ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_DEFAULT
        return False, 0, ttl
    ttl = cap_tier3_message_ttl(payload.get("message_ttl_seconds"))
    queued_at = parse_queued_at(payload.get("queued_at") or payload.get("enqueued_at"))
    if queued_at is None:
        return False, 0, ttl
    age_seconds = int(max(0.0, (now_utc - queued_at).total_seconds()))
    return age_seconds > ttl, age_seconds, ttl


def dead_letter_payload_for_expiry(payload: dict | None, *, age_seconds: int, ttl_seconds: int) -> dict:
    """Build deterministic dead-letter metadata for expired Tier 3 work."""
    return {
        "queue": ASSISTANT_TIER3_DEAD_LETTER_QUEUE,
        "reason": "expired_not_run",
        "age_seconds": age_seconds,
        "ttl_seconds": ttl_seconds,
        "original_payload": payload or {},
    }
