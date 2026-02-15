"""Phase 10-03 fairness and adaptive concurrency tests for chat bulk."""
from __future__ import annotations

from src.api.v1.chat.bulk import AdaptiveBulkConcurrency, fair_chunk_order
from src.celery_app import app
from src.jobs.queueing import TASK_ROUTES
from src.tasks.chat_bulk import CHAT_BULK_FAIRNESS_PROFILE, TERMINAL_CHUNK_STATUSES


def test_chat_bulk_worker_fairness_profile_is_locked():
    assert CHAT_BULK_FAIRNESS_PROFILE["task_acks_late"] is True
    assert CHAT_BULK_FAIRNESS_PROFILE["worker_prefetch_multiplier"] == 1
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1
    assert TASK_ROUTES["src.tasks.chat_bulk.run_chat_bulk_action"]["queue"] == "batch.t2"


def test_adaptive_concurrency_tracks_throttle_and_headroom():
    controller = AdaptiveBulkConcurrency(initial=4, admin_cap=6)
    assert controller.current == 4

    controller.observe(
        graphql_payload={
            "extensions": {
                "cost": {
                    "throttleStatus": {
                        "currentlyAvailable": 20,
                        "maximumAvailable": 100,
                        "restoreRate": 10,
                    }
                }
            }
        }
    )
    assert controller.current <= 4

    controller.observe(
        graphql_payload={
            "extensions": {
                "cost": {
                    "throttleStatus": {
                        "currentlyAvailable": 90,
                        "maximumAvailable": 100,
                        "restoreRate": 10,
                    }
                }
            }
        }
    )
    controller.observe(
        graphql_payload={
            "extensions": {
                "cost": {
                    "throttleStatus": {
                        "currentlyAvailable": 95,
                        "maximumAvailable": 100,
                        "restoreRate": 10,
                    }
                }
            }
        }
    )
    assert controller.current <= controller.hard_cap
    assert controller.current >= 1


def test_mixed_duration_chunk_order_avoids_starvation():
    chunks = [
        {"chunk_id": "c1", "skus": [str(i) for i in range(120)]},
        {"chunk_id": "c2", "skus": [str(i) for i in range(130)]},
        {"chunk_id": "c3", "skus": [str(i) for i in range(8)]},
        {"chunk_id": "c4", "skus": [str(i) for i in range(9)]},
    ]
    ordered = fair_chunk_order(chunks)
    ordered_ids = [chunk["chunk_id"] for chunk in ordered]

    assert ordered_ids[0] in {"c1", "c2"}
    assert ordered_ids[1] in {"c3", "c4"}
    assert {"c1", "c2", "c3", "c4"} == set(ordered_ids)


def test_terminal_chunk_statuses_support_idempotent_replay_skip():
    assert "completed" in TERMINAL_CHUNK_STATUSES
    assert "conflicted" in TERMINAL_CHUNK_STATUSES
    assert "failed" in TERMINAL_CHUNK_STATUSES
