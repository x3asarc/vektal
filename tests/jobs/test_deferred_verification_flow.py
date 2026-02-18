"""Phase 13-02 deferred verification background processing tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.governance.verification_oracle import (
    process_deferred_verifications,
    verify_execution_finality,
)
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


def test_deferred_event_is_promoted_to_verified_by_background_pass(app):
    with app.app_context():
        deferred = verify_execution_finality(
            action_id=None,
            batch_id=None,
            store_id=None,
            user_id=None,
            verification_probe=lambda attempt, waited: {"verified": False},
        )
        deferred_row = db.session.get(AssistantVerificationEvent, deferred.event_id)
        deferred_row.deferred_until = None
        db.session.commit()
        summary = process_deferred_verifications(
            verification_probe=lambda event: {"verified": event.id == deferred.event_id}
        )
        row = db.session.get(AssistantVerificationEvent, deferred.event_id)

    assert summary["checked"] >= 1
    assert summary["verified"] == 1
    assert row is not None
    assert row.status == "verified"
    assert row.verified_at is not None


def test_deferred_event_stays_deferred_when_background_probe_cannot_verify(app):
    with app.app_context():
        deferred = verify_execution_finality(
            action_id=None,
            batch_id=None,
            store_id=None,
            user_id=None,
            verification_probe=lambda attempt, waited: {"verified": False},
        )
        deferred_row = db.session.get(AssistantVerificationEvent, deferred.event_id)
        deferred_row.deferred_until = None
        db.session.commit()
        summary = process_deferred_verifications(
            verification_probe=lambda event: {"verified": False}
        )
        row = db.session.get(AssistantVerificationEvent, deferred.event_id)

    assert summary["checked"] >= 1
    assert summary["still_deferred"] >= 1
    assert row is not None
    assert row.status == "deferred"
    assert row.deferred_until is not None
