"""Phase 13-02 verification oracle and deferred state contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.governance.verification_oracle import verify_execution_finality
from src.models import AssistantVerificationEvent, db
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_oracle_verified_contract_persists_event(app):
    with app.app_context():
        outcome = verify_execution_finality(
            action_id=None,
            batch_id=None,
            store_id=None,
            user_id=None,
            verification_probe=lambda attempt, waited: {"verified": True, "attempt": attempt},
        )
        event = db.session.get(AssistantVerificationEvent, outcome.event_id)

    assert outcome.status == "verified"
    assert outcome.attempt_count == 1
    assert outcome.poll_schedule_seconds == [5, 10, 15]
    assert event is not None
    assert event.status == "verified"
    assert event.verified_at is not None


def test_oracle_unverified_contract_becomes_deferred(app):
    with app.app_context():
        outcome = verify_execution_finality(
            action_id=None,
            batch_id=None,
            store_id=None,
            user_id=None,
            verification_probe=lambda attempt, waited: {"verified": False, "attempt": attempt},
        )
        event = db.session.get(AssistantVerificationEvent, outcome.event_id)

    assert outcome.status == "deferred"
    assert outcome.waited_seconds == 30
    assert "delayed" in outcome.message.lower()
    assert event is not None
    assert event.status == "deferred"
    assert event.deferred_until is not None

