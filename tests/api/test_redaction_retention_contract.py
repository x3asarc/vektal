"""Phase 13-03 redaction and retention contract tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.app import create_openapi_app
from src.assistant.deployment.redaction import (
    purge_deadline,
    redact_structured,
    redact_unstructured,
    retention_deadline,
)
from src.models import db
from src.models.user import AccountStatus, User, UserTier
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    with client.application.app_context():
        user = User(
            email="ops-redaction@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client


def test_structured_and_unstructured_redaction_masks_secrets():
    payload = {
        "token": "abc123",
        "nested": {
            "api-key": "secret-value",
            "refresh_token": "refresh-secret",
            "safe": "visible",
        },
        "items": [{"password": "plaintext"}],
    }
    redacted = redact_structured(payload)
    assert redacted["token"] == "********"
    assert redacted["nested"]["api-key"] == "********"
    assert redacted["nested"]["refresh_token"] == "********"
    assert redacted["nested"]["safe"] == "visible"
    assert redacted["items"][0]["password"] == "********"

    text = "sk_live_1234567890 and pk_test_ABCDEFGHI password=letmein"
    redacted_text = redact_unstructured(text)
    assert "sk_live_1234567890" not in redacted_text
    assert "pk_test_ABCDEFGHI" not in redacted_text
    assert "letmein" not in redacted_text


def test_retention_and_purge_deadlines_match_locked_windows():
    created = datetime(2026, 2, 1, tzinfo=timezone.utc)
    assert retention_deadline(created_at=created, data_class="trace") == datetime(2026, 2, 15, tzinfo=timezone.utc)
    assert retention_deadline(created_at=created, data_class="audit") == datetime(2027, 2, 1, tzinfo=timezone.utc)

    requested = datetime(2026, 2, 1, tzinfo=timezone.utc)
    assert purge_deadline(requested_at=requested, storage_class="live") == datetime(2026, 2, 3, tzinfo=timezone.utc)
    assert purge_deadline(requested_at=requested, storage_class="backup") == datetime(2026, 2, 15, tzinfo=timezone.utc)


def test_ops_redaction_preview_and_retention_policy_endpoints(authenticated_client):
    preview = authenticated_client.post(
        "/api/v1/ops/redaction/preview",
        json={
            "payload": {"api_key": "k123", "child": {"token": "tok_1"}},
            "trace_text": "password:supersecret sk_live_12345678",
        },
    )
    assert preview.status_code == 200
    preview_payload = preview.get_json()
    assert preview_payload["structured_redacted"]["api_key"] == "********"
    assert preview_payload["structured_redacted"]["child"]["token"] == "********"
    assert "supersecret" not in preview_payload["trace_redacted"]
    assert "sk_live_12345678" not in preview_payload["trace_redacted"]

    retention = authenticated_client.get("/api/v1/ops/retention/policy")
    assert retention.status_code == 200
    retention_payload = retention.get_json()
    assert retention_payload["trace_retention_days"] == 14
    assert retention_payload["audit_retention_days"] == 365
    assert retention_payload["live_purge_hours"] == 48
    assert retention_payload["backup_purge_days"] == 14
