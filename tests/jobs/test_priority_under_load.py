"""Tier-priority routing tests."""

from src.jobs.queueing import WORKER_QUEUE_SPLIT, queue_for_tier


def test_tier_routing_prefers_higher_tier_queue_names():
    assert queue_for_tier("tier_3", kind="batch") == "batch.t3"
    assert queue_for_tier("tier_2", kind="batch") == "batch.t2"
    assert queue_for_tier("tier_1", kind="batch") == "batch.t1"


def test_worker_split_isolated_between_interactive_and_batch():
    interactive = set(WORKER_QUEUE_SPLIT["celery_worker"])
    batch = set(WORKER_QUEUE_SPLIT["celery_scraper"])
    assert "control" in interactive
    assert "control" not in batch
    assert interactive.intersection(batch) == set()

