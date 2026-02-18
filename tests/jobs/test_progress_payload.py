"""Unit tests for canonical job progress payload helpers."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.jobs.progress import (
    PROGRESS_STEP_ORDER,
    build_progress_payload,
    estimate_eta_seconds,
    infer_current_step,
)
from src.models import JobStatus


def _job(**overrides):
    base = {
        "id": 123,
        "status": JobStatus.RUNNING,
        "total_items": 100,
        "processed_items": 25,
        "total_products": 100,
        "processed_count": 25,
        "successful_items": 24,
        "failed_items": 1,
        "error_message": None,
        "parameters": {},
        "started_at": datetime.now(timezone.utc) - timedelta(seconds=50),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_progress_payload_contains_required_phase9_fields():
    payload = build_progress_payload(_job())
    required = {
        "job_id",
        "status",
        "processed_items",
        "total_items",
        "successful_items",
        "failed_items",
        "error_message",
        "percent_complete",
        "current_step",
        "current_step_label",
        "step_index",
        "step_total",
        "eta_seconds",
        "can_retry",
        "retry_url",
        "results_url",
    }
    assert required.issubset(payload.keys())
    assert payload["step_total"] == len(PROGRESS_STEP_ORDER)


def test_infer_current_step_prefers_explicit_parameter():
    job = _job(parameters={"current_step": "scraping_web"})
    assert infer_current_step(job) == "scraping_web"


def test_estimate_eta_is_none_without_running_progress_signal():
    not_running = _job(status=JobStatus.QUEUED, processed_items=0)
    assert estimate_eta_seconds(not_running) is None

    no_progress = _job(processed_items=0, processed_count=0)
    assert estimate_eta_seconds(no_progress) is None


def test_failed_terminal_is_retryable_in_payload():
    payload = build_progress_payload(
        _job(
            status=JobStatus.FAILED_TERMINAL,
            error_message="strict_failed_chunk",
            processed_items=100,
            processed_count=100,
            total_items=100,
            total_products=100,
        )
    )
    assert payload["can_retry"] is True
    assert payload["current_step"] == "failed"
    assert payload["retry_url"].endswith("/api/v1/jobs/123/retry")
