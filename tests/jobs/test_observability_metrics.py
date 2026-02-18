"""Observability metrics tests."""

from src.jobs import metrics


def test_queue_depth_metrics_aggregates_worker_views():
    sample = {
        "worker-a": [{"name": "control"}, {"name": "interactive.t3"}],
        "worker-b": [{"name": "batch.t1"}, {"name": "batch.t1"}],
    }
    depth = metrics.queue_depth_metrics(active_queues=sample)
    assert depth["control"] == 1
    assert depth["interactive.t3"] == 1
    assert depth["batch.t1"] == 2


def test_phase6_metrics_snapshot_composes_sections(monkeypatch):
    monkeypatch.setattr(metrics, "queue_depth_metrics", lambda active_queues=None: {"control": 1})
    monkeypatch.setattr(metrics, "chunk_staleness_metrics", lambda stale_after_minutes=10: {"stale_chunk_count": 0})
    monkeypatch.setattr(metrics, "pending_dispatch_metrics", lambda: {"pending_dispatch_total": 3})
    monkeypatch.setattr(metrics, "job_staleness_indicator", lambda stale_minutes=30: {"stale_job_count": 1})

    snapshot = metrics.phase6_metrics_snapshot(active_queues={})
    assert snapshot["queue_depth"]["control"] == 1
    assert snapshot["chunks"]["stale_chunk_count"] == 0
    assert snapshot["outbox"]["pending_dispatch_total"] == 3
    assert snapshot["jobs"]["stale_job_count"] == 1

