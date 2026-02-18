"""Phase 13-01 Tier 3 queue TTL/dead-letter backlog protection tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.jobs.queueing import (
    ASSISTANT_TIER3_DEAD_LETTER_QUEUE,
    ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_CAP,
    cap_tier3_message_ttl,
    dead_letter_payload_for_expiry,
    is_tier3_payload_expired,
)
from src.tasks.assistant_runtime import run_tier_runtime


def test_tier3_payload_expiry_routes_to_dead_letter():
    queued_at = (datetime.now(timezone.utc) - timedelta(seconds=1200)).isoformat()
    payload = {
        "queued_at": queued_at,
        "message_ttl_seconds": 900,
        "fallback_stage": "delegation_running",
    }

    result = run_tier_runtime(route_decision="tier_3", payload=payload)
    assert result["status"] == "expired_not_run"
    assert result["dead_letter"]["reason"] == "expired_not_run"
    assert result["dead_letter"]["queue"] == ASSISTANT_TIER3_DEAD_LETTER_QUEUE
    assert result["dead_letter"]["age_seconds"] > result["dead_letter"]["ttl_seconds"]


def test_tier3_ttl_cap_and_dead_letter_payload_contract():
    assert cap_tier3_message_ttl(999999) == ASSISTANT_TIER3_MESSAGE_TTL_SECONDS_CAP
    assert cap_tier3_message_ttl(-1) == 900

    expired, age_seconds, ttl_seconds = is_tier3_payload_expired(
        {"queued_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(), "message_ttl_seconds": 10}
    )
    assert expired is True
    dead_letter = dead_letter_payload_for_expiry({}, age_seconds=age_seconds, ttl_seconds=ttl_seconds)
    assert dead_letter["reason"] == "expired_not_run"
    assert dead_letter["queue"] == ASSISTANT_TIER3_DEAD_LETTER_QUEUE


def test_non_expired_tier3_payload_executes_with_reliability_metadata():
    queued_at = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    payload = {"queued_at": queued_at, "message_ttl_seconds": 900}
    result = run_tier_runtime(route_decision="tier_3", payload=payload)
    assert result["status"] == "accepted"
    assert result["queue"] == "assistant.t3"
    assert result["reliability"]["policy_version"] >= 1

