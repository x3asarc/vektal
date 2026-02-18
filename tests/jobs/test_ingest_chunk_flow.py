"""Core ingest orchestration contract tests."""

from src.jobs.checkpoints import crossed_checkpoints, milestone_policy
from src.jobs.orchestrator import _ingest_task_name_for_tier, _split_chunks


def test_milestone_policy_matches_locked_rules():
    assert milestone_policy(999) == [25, 35, 45, 55, 65, 75, 85, 95, 100]
    assert milestone_policy(1000) == [100]


def test_crossed_checkpoints_detects_new_boundaries_only():
    checkpoints = crossed_checkpoints(previous_count=20, new_count=40, total_products=100)
    assert checkpoints == [25, 35]

    no_duplicates = crossed_checkpoints(previous_count=35, new_count=35, total_products=100)
    assert no_duplicates == []


def test_chunk_membership_split_is_frozen_by_index_order():
    chunks = list(_split_chunks(list(range(1, 11)), chunk_size=4))
    assert chunks == [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10]]


def test_ingest_task_name_routes_by_tier():
    assert _ingest_task_name_for_tier("tier_1").endswith("ingest_chunk_t1")
    assert _ingest_task_name_for_tier("tier_2").endswith("ingest_chunk_t2")
    assert _ingest_task_name_for_tier("tier_3").endswith("ingest_chunk_t3")

