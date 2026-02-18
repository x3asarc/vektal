"""Retention cleanup task tests."""

from src.tasks import control


class _JobRow:
    def __init__(self, job_id):
        self.id = job_id


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self.rows


class _Expr:
    def in_(self, *_args, **_kwargs):
        return self

    def isnot(self, *_args, **_kwargs):
        return self

    def __le__(self, _other):
        return self


class _FakeJobModel:
    query = None
    status = _Expr()
    completed_at = _Expr()


def test_cleanup_old_jobs_dry_run_returns_candidates(monkeypatch):
    _FakeJobModel.query = _Query([_JobRow(1), _JobRow(2)])
    monkeypatch.setattr(control, "Job", _FakeJobModel)
    result = control.cleanup_old_jobs.run(retention_days=30, dry_run=True)
    assert result["dry_run"] is True
    assert result["candidate_count"] == 2
    assert result["candidate_ids"] == [1, 2]


def test_cleanup_old_jobs_executes_deletes_when_not_dry_run(monkeypatch):
    rows = [_JobRow(7), _JobRow(8)]
    _FakeJobModel.query = _Query(rows)
    monkeypatch.setattr(control, "Job", _FakeJobModel)

    deleted = []
    monkeypatch.setattr(control.db.session, "delete", lambda row: deleted.append(row.id))
    monkeypatch.setattr(control.db.session, "commit", lambda: None)

    result = control.cleanup_old_jobs.run(retention_days=14, dry_run=False)
    assert result["dry_run"] is False
    assert result["deleted_count"] == 2
    assert deleted == [7, 8]
