"""Queue topology and routing helpers for Phase 6."""
from __future__ import annotations

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

ALL_QUEUES = tuple(INTERACTIVE_QUEUES.values()) + tuple(BATCH_QUEUES.values()) + (
    CONTROL_QUEUE,
)

WORKER_QUEUE_SPLIT = {
    "celery_worker": [CONTROL_QUEUE, *INTERACTIVE_QUEUES.values()],
    "celery_scraper": [*BATCH_QUEUES.values()],
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
    return BATCH_QUEUES[tier_key]
