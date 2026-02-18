"""Phase 13-01 reliability policy and breaker contract tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.assistant.reliability.breakers import evaluate_breaker_gate, evaluate_failure_transition
from src.assistant.reliability.policy_store import ensure_default_runtime_policy, get_runtime_policy_snapshot
from src.assistant.reliability.retry_matrix import (
    RETRY_CLASS_RATE_LIMIT,
    RETRY_CLASS_SERVER_ERROR,
    evaluate_retry_decision,
)
from src.models import db
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_default_runtime_policy_snapshot_contains_locked_thresholds(app):
    with app.app_context():
        ensure_default_runtime_policy()
        snapshot = get_runtime_policy_snapshot(skill_name="chat.apply", provider_name="shopify")

    assert snapshot.policy_version == 1
    assert snapshot.breaker_error_rate_threshold == pytest.approx(0.25)
    assert snapshot.breaker_latency_p95_tier12_seconds == pytest.approx(15.0)
    assert snapshot.breaker_latency_p95_tier3_seconds == pytest.approx(45.0)
    assert snapshot.breaker_min_sample_size == 10
    assert snapshot.breaker_open_cooldown_seconds == 60
    assert snapshot.breaker_half_open_successes == 3
    assert snapshot.retry_policy["rate_limit"]["max_retries"] == 3
    assert snapshot.retry_policy["server_error"]["max_retries"] == 2


def test_breaker_gate_open_respects_cooldown_then_half_open(app):
    with app.app_context():
        snapshot = get_runtime_policy_snapshot()
    opened_at = datetime.now(timezone.utc)

    opening = replace(
        snapshot,
        breaker_state="open",
        breaker_opened_at=opened_at,
    )
    blocked = evaluate_breaker_gate(snapshot=opening, now_utc=opening.breaker_opened_at + timedelta(seconds=30))
    assert blocked.allow_request is False
    assert blocked.next_state == "open"
    assert blocked.reason == "cooldown_active"

    released = evaluate_breaker_gate(snapshot=opening, now_utc=opening.breaker_opened_at + timedelta(seconds=61))
    assert released.allow_request is True
    assert released.next_state == "half_open"
    assert released.reason == "cooldown_elapsed"


def test_failure_transition_and_retry_matrix_are_deterministic(app):
    with app.app_context():
        snapshot = get_runtime_policy_snapshot()

    loaded = replace(
        snapshot,
        breaker_state="closed",
        breaker_error_count=3,
        breaker_request_count=10,
    )
    transition = evaluate_failure_transition(snapshot=loaded, tier="tier_2")
    assert transition.next_state == "open"
    assert transition.reason == "error_rate_threshold_breach"

    rate_limit_attempt_1 = evaluate_retry_decision(
        retry_class=RETRY_CLASS_RATE_LIMIT,
        attempt_number=1,
        retry_policy=snapshot.retry_policy,
    )
    assert rate_limit_attempt_1.should_retry is True
    assert rate_limit_attempt_1.delay_seconds > 2.0

    server_attempt_3 = evaluate_retry_decision(
        retry_class=RETRY_CLASS_SERVER_ERROR,
        attempt_number=3,
        retry_policy=snapshot.retry_policy,
    )
    assert server_attempt_3.should_retry is False
