"""Finalizer behavior tests."""

from src.jobs import finalizer
from src.models import JobStatus


class _FakeQuery:
    def __init__(self, job):
        self._job = job

    def filter_by(self, **_kwargs):
        return self

    def with_for_update(self):
        return self

    def first(self):
        return self._job


class _FakeJob:
    def __init__(self, status):
        self.status = status
        self.is_terminal = True


class _FakeJobModel:
    query = None


def test_finalizer_mode_defaults_to_strict(monkeypatch):
    monkeypatch.delenv("PHASE6_FINALIZER_MODE", raising=False)
    assert finalizer._resolve_mode(None) == "strict"


def test_finalizer_respects_explicit_mode():
    assert finalizer._resolve_mode("lenient") == "lenient"
    assert finalizer._resolve_mode("strict") == "strict"


def test_finalizer_short_circuits_terminal_jobs(monkeypatch):
    job = _FakeJob(status=JobStatus.COMPLETED)
    _FakeJobModel.query = _FakeQuery(job)
    monkeypatch.setattr(finalizer, "Job", _FakeJobModel)
    result = finalizer.finalize_job(job_id=1)
    assert result["status"] == "already-terminal"
    assert result["job_status"] == "completed"
