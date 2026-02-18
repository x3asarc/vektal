"""Contract checks for canonical Phase 9 progress payload usage."""

from types import SimpleNamespace

from src.api.jobs.schemas import JobProgressEvent
from src.jobs.progress import build_progress_payload
from src.models import JobStatus


def _job(**overrides):
    base = {
        "id": 7,
        "status": JobStatus.RUNNING,
        "total_items": 20,
        "processed_items": 10,
        "total_products": 20,
        "processed_count": 10,
        "successful_items": 9,
        "failed_items": 1,
        "error_message": None,
        "parameters": {},
        "started_at": None,
        "created_at": None,
        "completed_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_progress_payload_emits_phase9_contract_fields():
    payload = build_progress_payload(_job())
    assert payload["job_id"] == 7
    assert "current_step" in payload
    assert "current_step_label" in payload
    assert "step_index" in payload
    assert "step_total" in payload
    assert "eta_seconds" in payload
    assert "can_retry" in payload
    assert "retry_url" in payload
    assert "results_url" in payload


def test_sse_progress_event_from_job_uses_canonical_payload():
    event = JobProgressEvent.from_job(_job())
    assert event.job_id == 7
    assert event.current_step is not None
    assert event.current_step_label is not None
    assert event.step_total >= 1
    assert event.retry_url.endswith("/api/v1/jobs/7/retry")


def test_failed_terminal_maps_to_retryable_contract():
    event = JobProgressEvent.from_job(
        _job(
            status=JobStatus.FAILED_TERMINAL,
            error_message="strict_failed_chunk",
            processed_items=20,
            processed_count=20,
            total_items=20,
            total_products=20,
        )
    )
    assert event.can_retry is True
    assert event.current_step == "failed"
