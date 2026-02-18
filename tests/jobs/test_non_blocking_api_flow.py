"""Static checks for non-blocking API launch behavior."""
from pathlib import Path


def test_create_job_route_uses_send_task_and_accepted_status():
    text = Path("src/api/v1/jobs/routes.py").read_text(encoding="utf-8")
    assert "def create_job()" in text
    assert "send_task(" in text
    assert "}, 202" in text


def test_cancel_route_uses_cancel_requested_semantics():
    text = Path("src/api/v1/jobs/routes.py").read_text(encoding="utf-8")
    assert "Cancellation requested" in text
    assert "request_cancellation(" in text

