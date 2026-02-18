"""Dispatcher contract tests."""
from datetime import datetime, timezone

from src.jobs import dispatcher
from src.models import AuditDispatchStatus


class _ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.committed = False

    def execute(self, _stmt):
        return _ScalarResult(self._rows)

    def commit(self):
        self.committed = True


class _Row:
    def __init__(self):
        self.id = 1
        self.job_id = 42
        self.checkpoint = 25
        self.dispatch_status = AuditDispatchStatus.PENDING_DISPATCH
        self.dispatch_attempts = 0
        self.next_dispatch_at = None
        self.dispatched_at = None
        self.last_error = None
        self.task_id = None


def test_backoff_caps_and_grows_exponentially():
    assert dispatcher._backoff_seconds(1) == 15
    assert dispatcher._backoff_seconds(2) == 30
    assert dispatcher._backoff_seconds(3) == 60
    assert dispatcher._backoff_seconds(10) == 300


def test_dispatcher_no_rows_is_noop(monkeypatch):
    session = _FakeSession(rows=[])
    monkeypatch.setattr(dispatcher.db, "session", session)
    result = dispatcher.dispatch_pending_audits(batch_size=50, publisher=lambda *_: "task-1")
    assert result == {"claimed": 0, "dispatched": 0, "scheduled_retry": 0}
    assert session.committed is True


def test_dispatcher_schedules_retry_on_publish_failure(monkeypatch):
    row = _Row()
    session = _FakeSession(rows=[row])
    monkeypatch.setattr(dispatcher.db, "session", session)

    def _boom(*_):
        raise RuntimeError("broker down")

    result = dispatcher.dispatch_pending_audits(batch_size=1, publisher=_boom)
    assert result["claimed"] == 1
    assert result["scheduled_retry"] == 1
    assert row.last_error == "broker down"
    assert row.next_dispatch_at is not None
    assert row.dispatch_status == AuditDispatchStatus.PENDING_DISPATCH

