"""Phase 12 assistant tier queue routing tests."""

from src.jobs.queueing import (
    ASSISTANT_RUNTIME_QUEUES,
    TASK_ROUTES,
    normalize_tier,
    queue_for_tier,
    queue_for_tier_runtime,
)


def test_assistant_runtime_queue_mapping_is_tier_aware():
    assert queue_for_tier_runtime("tier_1") == ASSISTANT_RUNTIME_QUEUES["tier_1"]
    assert queue_for_tier_runtime("tier_2") == ASSISTANT_RUNTIME_QUEUES["tier_2"]
    assert queue_for_tier_runtime("tier_3") == ASSISTANT_RUNTIME_QUEUES["tier_3"]
    assert queue_for_tier("tier_3", kind="assistant") == "assistant.t3"


def test_assistant_runtime_task_has_default_route():
    assert TASK_ROUTES["src.tasks.assistant_runtime.run_tier_runtime"]["queue"] == "assistant.t2"


def test_tier_normalization_supports_enum_like_values():
    assert normalize_tier("UserTier.TIER_1") == "tier_1"
    assert normalize_tier("usertier.tier_2") == "tier_2"
    assert normalize_tier("tier_3") == "tier_3"
