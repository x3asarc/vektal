"""Phase 13-03 provider fallback routing contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.deployment.provider_router import resolve_provider_route
from src.models import AssistantProviderRouteEvent, db
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
            email="provider-fallback@example.com",
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
            shop_domain="provider-fallback.myshopify.com",
            shop_name="Provider Fallback",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, store


def test_provider_route_primary_path_for_tier2_is_deterministic():
    decision = resolve_provider_route(
        correlation_id="corr-primary",
        store_id=1,
        intent_type="mutating_request",
        tier="tier_2",
    )
    assert decision.route_stage == "primary"
    assert decision.fallback_reason_code == "none"
    assert decision.selected_provider == "qwen"
    assert decision.selected_model == "qwen-2.5-coder"
    assert decision.policy_snapshot_hash


def test_provider_route_fallback_and_budget_guard_paths():
    fallback = resolve_provider_route(
        correlation_id="corr-fallback",
        store_id=1,
        intent_type="mutating_request",
        tier="tier_2",
        failure_stage="invalid_tool_call",
    )
    assert fallback.route_stage == "fallback"
    assert fallback.route_index == 1
    assert fallback.fallback_reason_code == "invalid_tool_call"
    assert fallback.selected_provider == "openrouter"

    budget = resolve_provider_route(
        correlation_id="corr-budget",
        store_id=1,
        intent_type="mutating_request",
        tier="tier_2",
        budget_percent=99.0,
    )
    assert budget.route_stage == "budget_guard"
    assert budget.route_index == 1
    assert budget.fallback_reason_code == "budget_guard"
    assert budget.selected_provider == "openrouter"


def test_chat_route_persists_provider_route_event_with_correlation(authenticated_client):
    client, store = authenticated_client
    response = client.post(
        "/api/v1/chat/route",
        json={
            "content": "update SKU-100 price to 12.99",
            "store_id": store.id,
            "provider_failure_stage": "invalid_tool_call",
        },
        headers={"X-Correlation-Id": "corr-route-fallback"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    provider_route = payload["provider_route"]
    assert payload["correlation_id"] == "corr-route-fallback"
    assert provider_route["route_stage"] == "fallback"
    assert provider_route["fallback_reason_code"] == "invalid_tool_call"
    assert provider_route["provider_route_event_id"] > 0

    with client.application.app_context():
        row = db.session.get(AssistantProviderRouteEvent, provider_route["provider_route_event_id"])
        assert row is not None
        assert row.correlation_id == "corr-route-fallback"
        assert row.route_stage == "fallback"
        assert row.fallback_reason_code == "invalid_tool_call"
        assert row.route_event_id is not None
        assert row.policy_snapshot_hash == provider_route["policy_snapshot_hash"]
