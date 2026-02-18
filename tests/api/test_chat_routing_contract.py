"""Phase 12 routing contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import AssistantRouteEvent, db
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
            email="route-contract@example.com",
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
            shop_domain="route-contract.myshopify.com",
            shop_name="Route Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _route(client, payload: dict):
    response = client.post("/api/v1/chat/route", json=payload)
    assert response.status_code == 200
    return response.get_json()


def test_low_confidence_defaults_to_safe_tier_with_escalation(authenticated_client):
    client, _, store = authenticated_client
    payload = _route(
        client,
        {
            "content": "sku",
            "store_id": store.id,
            "active_integrations": {"shopify": True},
        },
    )
    assert payload["route_decision"] == "tier_1"
    assert payload["fallback_stage"] == "safe_tier_fallback"
    assert payload["suggested_escalation"] == "tier_2"
    assert payload["approval_mode"] == "none"
    assert isinstance(payload["route_event_id"], int)

    with client.application.app_context():
        event = db.session.get(AssistantRouteEvent, payload["route_event_id"])
        assert event is not None
        assert event.route_decision == "tier_1"
        assert event.fallback_stage == "safe_tier_fallback"
        assert len(event.policy_snapshot_hash) == 64
        assert len(event.effective_toolset_hash) == 64


def test_tier1_mutation_route_is_blocked_write(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        user.tier = UserTier.TIER_1
        db.session.commit()

    payload = _route(
        client,
        {
            "content": "update SKU-100 price to 9.99",
            "store_id": store.id,
        },
    )
    assert payload["route_decision"] == "tier_1"
    assert payload["approval_mode"] == "blocked_write"
    assert payload["fallback_stage"] == "tier_upgrade_required"
    assert payload["suggested_escalation"] == "tier_2"


def test_route_hashes_are_stable_for_same_input(authenticated_client):
    client, _, store = authenticated_client
    request_payload = {
        "content": "update SKU-100 price to 9.99",
        "store_id": store.id,
        "rbac_role": "manager",
        "active_integrations": {"shopify": True},
    }

    first = _route(client, request_payload)
    second = _route(client, request_payload)

    assert first["route_decision"] == second["route_decision"]
    assert first["policy_snapshot_hash"] == second["policy_snapshot_hash"]
    assert first["effective_toolset_hash"] == second["effective_toolset_hash"]


def test_integration_disconnect_strips_shopify_tools(authenticated_client):
    client, _, store = authenticated_client
    payload = _route(
        client,
        {
            "content": "show me product status",
            "store_id": store.id,
            "active_integrations": {"shopify": False},
        },
    )
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert "chat.respond" in tool_ids
    assert "products.read" not in tool_ids
    assert "products.search" not in tool_ids
    assert "resolution.dry_run" not in tool_ids
