"""Phase 12 effective tool projection contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import AssistantTenantToolPolicy, db
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
            email="tool-projection@example.com",
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
            shop_domain="tool-projection.myshopify.com",
            shop_name="Tool Projection",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _resolve_tools(client, payload: dict):
    response = client.post("/api/v1/chat/tools/resolve", json=payload)
    assert response.status_code == 200
    return response.get_json()


def test_projection_respects_tier_role_and_integration(authenticated_client):
    client, _, store = authenticated_client

    member = _resolve_tools(
        client,
        {
            "store_id": store.id,
            "rbac_role": "member",
            "active_integrations": {"shopify": True},
        },
    )
    member_tool_ids = {tool["tool_id"] for tool in member["effective_toolset"]}
    assert "chat.respond" in member_tool_ids
    assert "resolution.dry_run" in member_tool_ids
    assert "resolution.apply" not in member_tool_ids
    assert "agent.spawn_sub_agent" not in member_tool_ids

    manager = _resolve_tools(
        client,
        {
            "store_id": store.id,
            "rbac_role": "manager",
            "active_integrations": {"shopify": True},
        },
    )
    manager_tool_ids = {tool["tool_id"] for tool in manager["effective_toolset"]}
    assert "resolution.apply" in manager_tool_ids

    disconnected = _resolve_tools(
        client,
        {
            "store_id": store.id,
            "rbac_role": "manager",
            "active_integrations": {"shopify": False},
        },
    )
    disconnected_tool_ids = {tool["tool_id"] for tool in disconnected["effective_toolset"]}
    assert disconnected_tool_ids == {"chat.respond"}


def test_tenant_deny_policy_precedence(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        db.session.add(
            AssistantTenantToolPolicy(
                store_id=store.id,
                tool_id="products.read",
                policy_action="deny",
                role_scope="*",
                is_active=True,
                created_by_user_id=user.id,
            )
        )
        db.session.commit()

    payload = _resolve_tools(
        client,
        {
            "store_id": store.id,
            "rbac_role": "member",
            "active_integrations": {"shopify": True},
        },
    )
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert "products.read" not in tool_ids
    assert any("products.read: denied by tenant tool policy" in note for note in payload["notes"])


def test_tenant_allowlist_limits_toolset(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        db.session.add_all(
            [
                AssistantTenantToolPolicy(
                    store_id=store.id,
                    tool_id="products.read",
                    policy_action="allow",
                    role_scope="*",
                    is_active=True,
                    created_by_user_id=user.id,
                ),
                AssistantTenantToolPolicy(
                    store_id=store.id,
                    tool_id="chat.respond",
                    policy_action="allow",
                    role_scope="*",
                    is_active=True,
                    created_by_user_id=user.id,
                ),
            ]
        )
        db.session.commit()

    payload = _resolve_tools(
        client,
        {
            "store_id": store.id,
            "rbac_role": "member",
            "active_integrations": {"shopify": True},
        },
    )
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert tool_ids == {"chat.respond", "products.read"}
    assert any("excluded by tenant allowlist policy" in note for note in payload["notes"])
