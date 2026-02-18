"""Phase 13-02 kill-switch enforcement contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.governance.kill_switch import get_kill_switch_decision
from src.models import ChatAction, ChatSession, db
from src.models.assistant_kill_switch import AssistantKillSwitch
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
            email="kill-switch-contract@example.com",
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
            shop_domain="kill-switch-contract.myshopify.com",
            shop_name="Kill Switch Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Kill Switch Session"})
    assert response.status_code == 201
    return response.get_json()


def test_global_kill_switch_forces_safe_degraded_message_flow(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)

    with client.application.app_context():
        db.session.add(
            AssistantKillSwitch(
                scope_kind="global",
                store_id=None,
                mode="safe_degraded",
                is_enabled=True,
                reason="Maintenance window",
            )
        )
        db.session.commit()

    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "update SKU-100 price to 19.99", "idempotency_key": "kill-switch-message"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is None
    blocks = payload["assistant_message"]["blocks"]
    assert any(block.get("title") == "execution_paused" for block in blocks if block.get("type") == "action")


def test_tenant_kill_switch_blocks_action_apply_contract(authenticated_client):
    client, user, store = authenticated_client
    session = _create_session(client)

    with client.application.app_context():
        session_row = db.session.get(ChatSession, session["id"])
        action = ChatAction(
            session_id=session_row.id,
            user_id=user.id,
            store_id=store.id,
            action_type="update_product",
            status="approved",
            payload_json={"runtime": {"action_kind": "write"}, "dry_run_required": True, "dry_run_id": 99999},
        )
        db.session.add(action)
        db.session.flush()

        db.session.add(
            AssistantKillSwitch(
                scope_kind="tenant",
                store_id=store.id,
                mode="blocked",
                is_enabled=True,
                reason="Tenant emergency freeze",
            )
        )
        db.session.commit()
        action_id = action.id

    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/actions/{action_id}/apply",
        json={},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["type"].endswith("/kill-switch-active")
    assert payload["kill_switch"]["scope_kind"] == "tenant"


def test_no_active_kill_switch_returns_open_decision(authenticated_client):
    client, _, store = authenticated_client
    with client.application.app_context():
        decision = get_kill_switch_decision(store_id=store.id)
    assert decision.is_blocked is False
    assert decision.scope_kind is None
