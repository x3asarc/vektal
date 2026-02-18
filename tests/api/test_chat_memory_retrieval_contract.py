"""Phase 12 chat memory retrieval contract tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import AssistantMemoryFact, db
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
            email="memory-contract@example.com",
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
            shop_domain="memory-contract.myshopify.com",
            shop_name="Memory Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        other_user = User(
            email="memory-other@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other_user.set_password("password123")
        db.session.add(other_user)
        db.session.flush()

        now = datetime.now(timezone.utc)
        db.session.add_all(
            [
                AssistantMemoryFact(
                    store_id=store.id,
                    user_id=user.id,
                    fact_key="seo-tone",
                    fact_value_text="Use concise professional SEO tone.",
                    source="chat",
                    trust_score=0.95,
                    provenance_json={"origin": "manual", "batch_id": 101},
                    expires_at=now + timedelta(days=30),
                ),
                AssistantMemoryFact(
                    store_id=store.id,
                    user_id=None,
                    fact_key="supplier-pentart",
                    fact_value_text="Images should be downloaded before apply.",
                    source="settings",
                    trust_score=0.9,
                    provenance_json={"origin": "team-setting"},
                    expires_at=now + timedelta(days=30),
                ),
                AssistantMemoryFact(
                    store_id=store.id,
                    user_id=other_user.id,
                    fact_key="private-note",
                    fact_value_text="only for another user",
                    source="chat",
                    trust_score=0.8,
                    provenance_json={"origin": "private"},
                    expires_at=now + timedelta(days=30),
                ),
                AssistantMemoryFact(
                    store_id=store.id,
                    user_id=user.id,
                    fact_key="expired-note",
                    fact_value_text="expired should not return",
                    source="chat",
                    trust_score=0.9,
                    provenance_json={"origin": "stale"},
                    expires_at=now - timedelta(days=1),
                ),
            ]
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store, other_user


def _retrieve(client, payload: dict):
    response = client.post("/api/v1/chat/memory/retrieve", json=payload)
    assert response.status_code == 200
    return response.get_json()


def test_memory_retrieve_team_scope_returns_provenance(authenticated_client):
    client, _, store, _ = authenticated_client
    payload = _retrieve(
        client,
        {
            "store_id": store.id,
            "query": "seo images",
            "scope": "team",
            "top_k": 5,
        },
    )
    assert payload["total"] >= 2
    assert all("provenance" in item for item in payload["items"])
    assert all(item["expires_at"] is None or isinstance(item["expires_at"], str) for item in payload["items"])
    keys = {item["fact_key"] for item in payload["items"]}
    assert "seo-tone" in keys
    assert "supplier-pentart" in keys
    assert "expired-note" not in keys


def test_memory_retrieve_user_scope_excludes_other_users(authenticated_client):
    client, _, store, _ = authenticated_client
    payload = _retrieve(
        client,
        {
            "store_id": store.id,
            "query": "note",
            "scope": "user",
            "top_k": 10,
        },
    )
    keys = {item["fact_key"] for item in payload["items"]}
    assert "private-note" not in keys
