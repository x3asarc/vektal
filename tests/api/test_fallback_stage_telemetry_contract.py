"""Phase 12 fallback-stage telemetry contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import ChatMessage, db
from src.models.shopify import ShopifyStore
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
            email="fallback-telemetry@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        store = ShopifyStore(
            user_id=user.id,
            shop_domain="fallback-telemetry.myshopify.com",
            shop_name="Fallback Telemetry",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Fallback Telemetry"})
    assert response.status_code == 201
    return response.get_json()


def test_route_endpoint_exposes_fallback_stage_with_runtime_payload(authenticated_client):
    client, _, store = authenticated_client
    response = client.post(
        "/api/v1/chat/route",
        json={"content": "sku", "store_id": store.id},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["fallback_stage"] == "safe_tier_fallback"
    assert payload["runtime_payload"]["mode"] == "read_safe"
    assert any("fallback_stage=safe_tier_fallback" in reason for reason in payload["reasons"])


def test_message_source_metadata_carries_route_and_runtime_summary(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "q", "idempotency_key": "fallback-msg"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    source_metadata = payload["assistant_message"]["source_metadata"]
    route_summary = source_metadata.get("route_summary")
    runtime_payload = source_metadata.get("runtime_payload")
    assert isinstance(route_summary, dict)
    assert isinstance(runtime_payload, dict)
    assert route_summary.get("fallback_stage") == "safe_tier_fallback"
    assert runtime_payload.get("mode") == "read_safe"


def test_blocked_write_telemetry_propagates_to_message(authenticated_client):
    client, user, _ = authenticated_client
    with client.application.app_context():
        user.tier = UserTier.TIER_1
        db.session.commit()

    session = _create_session(client)
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "update SKU-200 price", "idempotency_key": "blocked-telemetry"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    route_summary = payload["assistant_message"]["source_metadata"]["route_summary"]
    assert route_summary["fallback_stage"] == "tier_upgrade_required"
    assert route_summary["approval_mode"] == "blocked_write"

    blocks = payload["assistant_message"]["blocks"]
    escalation_blocks = [block for block in blocks if block.get("title") == "tier_upgrade_required"]
    assert escalation_blocks

    with client.application.app_context():
        row = ChatMessage.query.get(payload["assistant_message"]["id"])
        assert row is not None
        assert isinstance(row.source_metadata, dict)
