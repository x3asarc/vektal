"""Phase 12 Tier 1/2 runtime and semantic firewall contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import ChatAction, ChatSession, db
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
            email="tier-runtime@example.com",
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
            shop_domain="tier-runtime.myshopify.com",
            shop_name="Tier Runtime",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Tier Runtime"})
    assert response.status_code == 201
    return response.get_json()


def test_route_runtime_payload_tier2_mutation(authenticated_client):
    client, _, store = authenticated_client
    response = client.post(
        "/api/v1/chat/route",
        json={
            "content": "update SKU-100 price to 9.99",
            "store_id": store.id,
            "active_integrations": {"shopify": True},
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["route_decision"] == "tier_2"
    assert payload["runtime_payload"]["mode"] == "governed_skill_runtime"
    assert payload["runtime_payload"]["requires_dry_run"] is True
    assert payload["runtime_payload"]["requires_product_approval"] is True


def test_blocked_write_for_tier1_creates_no_action(authenticated_client):
    client, user, _ = authenticated_client
    with client.application.app_context():
        user.tier = UserTier.TIER_1
        db.session.commit()

    session = _create_session(client)
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "update SKU-100 price to 12.99", "idempotency_key": "tier1-blocked-write"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is None
    blocks = payload["assistant_message"]["blocks"]
    assert any(block.get("title") == "tier_upgrade_required" for block in blocks if block.get("type") == "action")


def test_write_actions_carry_runtime_metadata_and_require_approval(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)
    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "update SKU-100", "idempotency_key": "tier2-write-runtime"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is not None
    runtime = payload["action"]["payload"]["runtime"]
    assert runtime["action_kind"] == "write"
    assert runtime["route_decision"] in {"tier_2", "tier_3"}

    apply_response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/actions/{payload['action']['id']}/apply",
        json={},
    )
    assert apply_response.status_code == 409
    error_payload = apply_response.get_json()
    assert error_payload["type"].endswith("/approval-required")


def test_read_actions_are_blocked_from_apply_flow(authenticated_client):
    client, user, store = authenticated_client
    session = _create_session(client)

    with client.application.app_context():
        session_row = db.session.get(ChatSession, session["id"])
        action = ChatAction(
            session_id=session_row.id,
            user_id=user.id,
            store_id=store.id,
            action_type="read_summary",
            status="approved",
            payload_json={
                "runtime": {"action_kind": "read"},
                "dry_run_required": False,
            },
        )
        db.session.add(action)
        db.session.commit()
        action_id = action.id

    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/actions/{action_id}/apply",
        json={},
    )
    assert response.status_code == 409
    payload = response.get_json()
    assert payload["type"].endswith("/read-action-apply-forbidden")
