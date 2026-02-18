"""Phase 12 user/team assistant profile contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import AssistantProfile, db
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
            email="profile-contract@example.com",
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
            shop_domain="profile-contract.myshopify.com",
            shop_name="Profile Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _resolve_tools(client, store_id: int):
    response = client.post(
        "/api/v1/chat/tools/resolve",
        json={
            "store_id": store_id,
            "rbac_role": "member",
            "active_integrations": {"shopify": True},
        },
    )
    assert response.status_code == 200
    return response.get_json()


def test_team_profile_enabled_skill_set_is_enforced(authenticated_client):
    client, _, store = authenticated_client
    with client.application.app_context():
        db.session.add(
            AssistantProfile(
                store_id=store.id,
                profile_scope="team",
                enabled_skill_set=["chat.respond", "products.read"],
                is_active=True,
                priority=100,
            )
        )
        db.session.commit()

    payload = _resolve_tools(client, store.id)
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert tool_ids == {"chat.respond", "products.read"}


def test_user_profile_overrides_team_profile(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        db.session.add_all(
            [
                AssistantProfile(
                    store_id=store.id,
                    profile_scope="team",
                    enabled_skill_set=["chat.respond", "products.read"],
                    is_active=True,
                    priority=10,
                ),
                AssistantProfile(
                    user_id=user.id,
                    profile_scope="user",
                    enabled_skill_set=["chat.respond"],
                    is_active=True,
                    priority=20,
                ),
            ]
        )
        db.session.commit()

    payload = _resolve_tools(client, store.id)
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert tool_ids == {"chat.respond"}
    assert any("disabled by profile enabled-skill set" in note for note in payload["notes"])


def test_inactive_profile_is_ignored(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        db.session.add(
            AssistantProfile(
                user_id=user.id,
                profile_scope="user",
                enabled_skill_set=["chat.respond"],
                is_active=False,
                priority=100,
            )
        )
        db.session.commit()

    payload = _resolve_tools(client, store.id)
    tool_ids = {tool["tool_id"] for tool in payload["effective_toolset"]}
    assert "products.read" in tool_ids
    assert "products.search" in tool_ids
