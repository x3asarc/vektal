"""SSE/polling contract parity checks for jobs progress routes."""

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_stream_route_emits_named_job_event():
    text = _read("src/api/jobs/events.py")
    assert 'event=f"job_{job_id}"' in text
    assert "mimetype='text/event-stream'" in text
    assert "'X-Accel-Buffering': 'no'" in text


def test_status_route_uses_canonical_progress_builder_fields():
    text = _read("src/api/jobs/events.py")
    assert "progress_payload = build_progress_payload(job)" in text
    assert 'current_step=progress_payload["current_step"]' in text
    assert 'eta_seconds=progress_payload["eta_seconds"]' in text
    assert 'can_retry=progress_payload["can_retry"]' in text
    assert 'retry_url=progress_payload["retry_url"]' in text
    assert 'results_url=progress_payload["results_url"]' in text


def test_list_and_detail_routes_are_enriched_from_canonical_payload():
    text = _read("src/api/v1/jobs/routes.py")
    assert "progress = build_progress_payload(job)" in text
    assert 'current_step=progress["current_step"]' in text
    assert 'eta_seconds=progress["eta_seconds"]' in text
    assert 'can_retry=progress["can_retry"]' in text
    assert 'retry_url=progress["retry_url"]' in text
    assert 'results_url=progress["results_url"]' in text


def test_broadcast_path_uses_shared_announcer_helper():
    text = _read("src/api/jobs/events.py")
    assert "announce_job_progress(job_id=job_id, job=job)" in text
