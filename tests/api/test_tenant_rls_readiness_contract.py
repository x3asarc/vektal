"""Phase 12 tenant scope and RLS-readiness contract checks."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import (
    AssistantDelegationEvent,
    AssistantMemoryEmbedding,
    AssistantMemoryFact,
    AssistantProfile,
    AssistantRouteEvent,
    AssistantTenantToolPolicy,
    db,
)
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
            email="rls-contract@example.com",
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
            shop_domain="rls-contract.myshopify.com",
            shop_name="RLS Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        other_user = User(
            email="rls-other@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other_user.set_password("password123")
        db.session.add(other_user)
        db.session.flush()

        other_store = ShopifyStore(
            user_id=other_user.id,
            shop_domain="rls-other.myshopify.com",
            shop_name="RLS Other",
            access_token_encrypted=b"token-2",
            is_active=True,
        )
        db.session.add(other_store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store, other_store


def test_assistant_models_include_tenant_scope_column():
    models = [
        AssistantTenantToolPolicy,
        AssistantProfile,
        AssistantMemoryFact,
        AssistantMemoryEmbedding,
        AssistantRouteEvent,
        AssistantDelegationEvent,
    ]
    for model in models:
        assert "store_id" in model.__table__.columns


def test_route_endpoint_blocks_cross_tenant_store_access(authenticated_client):
    client, _, _, other_store = authenticated_client
    response = client.post(
        "/api/v1/chat/route",
        json={"content": "help", "store_id": other_store.id},
    )
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["type"].endswith("/forbidden")


def test_tools_resolve_blocks_cross_tenant_store_access(authenticated_client):
    client, _, _, other_store = authenticated_client
    response = client.post(
        "/api/v1/chat/tools/resolve",
        json={"store_id": other_store.id},
    )
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["type"].endswith("/forbidden")
