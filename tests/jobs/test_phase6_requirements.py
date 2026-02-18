"""Phase 6 requirement closure smoke tests."""
from pathlib import Path


def test_requirements_file_contains_phase6_ids():
    text = Path(".planning/REQUIREMENTS.md").read_text(encoding="utf-8")
    for req_id in (
        "DOCKER-03",
        "DOCKER-04",
        "DOCKER-06",
        "DOCKER-10",
        "DOCKER-11",
        "JOBS-01",
        "JOBS-02",
        "JOBS-03",
        "JOBS-04",
        "JOBS-05",
        "JOBS-06",
        "JOBS-07",
        "JOBS-08",
    ):
        assert req_id in text


def test_phase6_core_artifacts_exist():
    expected = [
        Path("src/jobs/orchestrator.py"),
        Path("src/jobs/dispatcher.py"),
        Path("src/jobs/finalizer.py"),
        Path("src/jobs/cancellation.py"),
        Path("src/jobs/metrics.py"),
        Path("src/tasks/ingest.py"),
        Path("src/tasks/audits.py"),
        Path("src/tasks/control.py"),
        Path("src/tasks/scrape_jobs.py"),
        Path("src/models/ingest_chunk.py"),
        Path("src/models/audit_checkpoint.py"),
    ]
    for path in expected:
        assert path.exists(), f"missing artifact: {path}"

