"""Cancellation flow tests."""

from src.jobs import cancellation
from src.models import JobStatus


class _FakeJob:
    def __init__(self, status):
        self.id = 11
        self.status = status
        self.cancellation_requested_at = None


class _FakeJobQuery:
    def __init__(self, job):
        self._job = job

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self._job


class _FakeJobModel:
    query = None


class _FakeChunk:
    def __init__(self, task_id):
        self.task_id = task_id


class _FakeChunkQuery:
    def __init__(self, chunks):
        self._chunks = chunks

    def filter_by(self, **_kwargs):
        return self

    def all(self):
        return self._chunks


class _FakeChunkModel:
    query = None


def test_request_cancellation_is_idempotent_for_already_requested(monkeypatch):
    job = _FakeJob(status=JobStatus.CANCEL_REQUESTED)
    _FakeJobModel.query = _FakeJobQuery(job)
    monkeypatch.setattr(cancellation, "Job", _FakeJobModel)
    result = cancellation.request_cancellation(job_id=job.id)
    assert result["status"] == "already-requested"


def test_request_cancellation_sets_cancel_requested_and_revokes(monkeypatch):
    job = _FakeJob(status=JobStatus.RUNNING)
    _FakeJobModel.query = _FakeJobQuery(job)
    _FakeChunkModel.query = _FakeChunkQuery([_FakeChunk("abc"), _FakeChunk("def")])
    monkeypatch.setattr(cancellation, "Job", _FakeJobModel)
    monkeypatch.setattr(cancellation, "IngestChunk", _FakeChunkModel)

    revoked = []
    queued = []
    monkeypatch.setattr(cancellation.db.session, "commit", lambda: None)
    monkeypatch.setattr("src.celery_app.app.control.revoke", lambda task_id, terminate=False: revoked.append((task_id, terminate)))
    monkeypatch.setattr("src.celery_app.app.send_task", lambda name, kwargs=None: queued.append((name, kwargs)))

    result = cancellation.request_cancellation(job_id=job.id, terminate=False)
    assert result["status"] == "cancel_requested"
    assert job.status == JobStatus.CANCEL_REQUESTED
    assert len(revoked) == 2
    assert queued[0][0] == "src.tasks.control.finalize_job"
