"""Phase 12 tier queue QoS and worker split contract tests."""

from src.jobs.queueing import ALL_QUEUES, WORKER_QUEUE_SPLIT
from src.tasks.assistant_runtime import run_tier_runtime


def test_assistant_queues_in_topology():
    assert "assistant.t1" in ALL_QUEUES
    assert "assistant.t2" in ALL_QUEUES
    assert "assistant.t3" in ALL_QUEUES


def test_assistant_worker_split_isolated():
    queues = WORKER_QUEUE_SPLIT.get("celery_assistant", [])
    assert "assistant.t1" in queues
    assert "assistant.t2" in queues
    assert "assistant.t3" in queues
    assert "control" not in queues


def test_runtime_task_emits_qos_metadata():
    result = run_tier_runtime(route_decision="tier_3", payload={"fallback_stage": "delegation_running"})
    assert result["queue"] == "assistant.t3"
    assert result["qos"]["task_acks_late"] is True
    assert result["qos"]["worker_prefetch_multiplier"] == 1
    assert result["fallback_stage"] == "delegation_running"
