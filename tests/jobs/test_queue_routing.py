"""Queue routing tests for Phase 6."""

from src.celery_app import app
from src.jobs.queueing import ALL_QUEUES, TASK_ROUTES


def test_all_expected_queues_present():
    assert "interactive.t1" in ALL_QUEUES
    assert "interactive.t2" in ALL_QUEUES
    assert "interactive.t3" in ALL_QUEUES
    assert "batch.t1" in ALL_QUEUES
    assert "batch.t2" in ALL_QUEUES
    assert "batch.t3" in ALL_QUEUES
    assert "control" in ALL_QUEUES


def test_task_routes_include_tiered_ingest_and_control():
    assert TASK_ROUTES["src.tasks.ingest.ingest_chunk_t1"]["queue"] == "batch.t1"
    assert TASK_ROUTES["src.tasks.ingest.ingest_chunk_t2"]["queue"] == "batch.t2"
    assert TASK_ROUTES["src.tasks.ingest.ingest_chunk_t3"]["queue"] == "batch.t3"
    assert TASK_ROUTES["src.tasks.audits.dispatch_pending_audits"]["queue"] == "control"


def test_celery_app_loads_declared_queue_topology():
    queue_names = {queue.name for queue in app.conf.task_queues}
    assert set(ALL_QUEUES).issubset(queue_names)
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1

