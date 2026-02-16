"""Shared job progress payloads and SSE broadcasting helpers."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from src.api.core.sse import job_announcer
from src.models import Job, JobStatus, JobType


PROGRESS_STEP_ORDER = [
    "queued",
    "searching_shopify",
    "searching_supplier_data",
    "enrichment_review",
    "scraping_web",
    "analyzing_images",
    "applying_updates",
]

PROGRESS_STEP_LABELS = {
    "queued": "Queued",
    "searching_shopify": "Searching Shopify",
    "searching_supplier_data": "Searching Supplier Data",
    "enrichment_review": "Reviewing Enrichment Decisions",
    "scraping_web": "Scraping Web",
    "analyzing_images": "Analyzing Images",
    "applying_updates": "Applying Updates",
    "completed": "Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
}

RETRYABLE_STATUSES = {
    JobStatus.FAILED,
    JobStatus.FAILED_TERMINAL,
    JobStatus.CANCELLED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _get_status(job: Job) -> JobStatus:
    if isinstance(job.status, JobStatus):
        return job.status
    return JobStatus(str(job.status))


def _totals(job: Job) -> tuple[int, int]:
    total_items = int(getattr(job, "total_items", 0) or getattr(job, "total_products", 0) or 0)
    processed_items = int(getattr(job, "processed_items", 0) or getattr(job, "processed_count", 0) or 0)
    return total_items, processed_items


def _percent_complete(total_items: int, processed_items: int) -> float:
    if total_items <= 0:
        return 0.0
    return round((processed_items / total_items) * 100, 1)


def infer_current_step(job: Job) -> str:
    params = _as_dict(getattr(job, "parameters", None))
    explicit_step = params.get("current_step")
    if isinstance(explicit_step, str) and explicit_step in PROGRESS_STEP_LABELS:
        return explicit_step

    status = _get_status(job)
    if status == JobStatus.COMPLETED:
        return "completed"
    if status in {JobStatus.FAILED, JobStatus.FAILED_TERMINAL}:
        return "failed"
    if status == JobStatus.CANCELLED:
        return "cancelled"
    if status in {JobStatus.PENDING, JobStatus.QUEUED}:
        return "queued"

    total_items, processed_items = _totals(job)
    percent = _percent_complete(total_items, processed_items)
    job_type = getattr(job, "job_type", None)
    if job_type == JobType.PRODUCT_ENRICH or str(job_type).lower() == "product_enrich":
        if percent < 20:
            return "enrichment_review"
        return "applying_updates"
    if percent < 10:
        return "searching_shopify"
    if percent < 35:
        return "searching_supplier_data"
    if percent < 70:
        return "scraping_web"
    if percent < 95:
        return "analyzing_images"
    return "applying_updates"


def estimate_eta_seconds(job: Job, now: datetime | None = None) -> int | None:
    status = _get_status(job)
    if status != JobStatus.RUNNING:
        return None

    total_items, processed_items = _totals(job)
    if total_items <= 0 or processed_items <= 0 or not job.started_at:
        return None

    started_at = job.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    current = now or _now()
    elapsed_seconds = max((current - started_at).total_seconds(), 1.0)
    rate = processed_items / elapsed_seconds
    if rate <= 0:
        return None

    remaining_items = max(total_items - processed_items, 0)
    return int(math.ceil(remaining_items / rate))


def build_progress_payload(job: Job) -> dict[str, Any]:
    total_items, processed_items = _totals(job)
    step = infer_current_step(job)
    status = _get_status(job)
    step_index = (
        PROGRESS_STEP_ORDER.index(step) + 1
        if step in PROGRESS_STEP_ORDER
        else len(PROGRESS_STEP_ORDER)
    )

    return {
        "job_id": job.id,
        "status": status.value,
        "processed_items": processed_items,
        "total_items": total_items,
        "successful_items": int(getattr(job, "successful_items", 0) or 0),
        "failed_items": int(getattr(job, "failed_items", 0) or 0),
        "error_message": getattr(job, "error_message", None),
        "percent_complete": _percent_complete(total_items, processed_items),
        "current_step": step,
        "current_step_label": PROGRESS_STEP_LABELS.get(step, step.replace("_", " ").title()),
        "step_index": step_index,
        "step_total": len(PROGRESS_STEP_ORDER),
        "eta_seconds": estimate_eta_seconds(job),
        "can_retry": status in RETRYABLE_STATUSES,
        "retry_url": f"/api/v1/jobs/{job.id}/retry",
        "results_url": f"/jobs/{job.id}?tab=results",
    }


def announce_job_progress(job_id: int, job: Job | None = None) -> None:
    current_job = job
    if current_job is None:
        current_job = Job.query.get(job_id)
    if not current_job:
        return
    payload = build_progress_payload(current_job)
    job_announcer.announce(job_id, json.dumps(payload))
