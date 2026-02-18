"""Contract checks for jobs retry endpoint semantics."""

from pathlib import Path


def test_retry_endpoint_exists_and_is_post():
    text = Path("src/api/v1/jobs/routes.py").read_text(encoding="utf-8")
    assert '@jobs_api_bp.route("/<int:job_id>/retry", methods=["POST"])' in text
    assert "def retry_job(job_id: int):" in text


def test_retry_endpoint_allows_terminal_retryable_states_only():
    text = Path("src/api/v1/jobs/routes.py").read_text(encoding="utf-8")
    assert "JobStatus.FAILED" in text
    assert "JobStatus.FAILED_TERMINAL" in text
    assert "JobStatus.CANCELLED" in text
    assert "can only retry failed or cancelled jobs" in text
    assert '"invalid-job-state"' in text
    assert "409" in text


def test_retry_endpoint_returns_accepted_with_lineage_and_stream_url():
    text = Path("src/api/v1/jobs/routes.py").read_text(encoding="utf-8")
    assert '"retry_of_job_id": job.id' in text
    assert "Retry job accepted for background processing" in text
    assert "stream_url=f\"/api/v1/jobs/{retry_job_row.id}/stream\"" in text
    assert ").model_dump(), 202" in text


def test_retry_schema_contains_required_response_fields():
    text = Path("src/api/v1/jobs/schemas.py").read_text(encoding="utf-8")
    assert "class JobRetryResponse(BaseModel):" in text
    assert "retry_of_job_id: int" in text
    assert "stream_url: Optional[str] = None" in text
