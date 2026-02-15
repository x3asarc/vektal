"""Contract tests for Phase 10 chat API foundation."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.chat_session import ChatSession
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
            email="chat-contract@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        store = ShopifyStore(
            user_id=user.id,
            shop_domain="chat-contract.myshopify.com",
            shop_name="Chat Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Ops"})
    assert response.status_code == 201
    return response.get_json()


def test_sessions_require_auth(client):
    response = client.get("/api/v1/chat/sessions")
    assert response.status_code in {401, 302}


def test_create_list_get_sessions(authenticated_client):
    client, _, store = authenticated_client

    created = _create_session(client)
    assert created["state"] == "at_door"
    assert created["store_id"] == store.id

    listed = client.get("/api/v1/chat/sessions")
    assert listed.status_code == 200
    payload = listed.get_json()
    assert payload["total"] >= 1
    assert any(row["id"] == created["id"] for row in payload["sessions"])

    fetched = client.get(f"/api/v1/chat/sessions/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["id"] == created["id"]


def test_post_message_generates_assistant_blocks_and_action(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)

    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "R0530", "idempotency_key": "chat-action-1"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["session"]["state"] == "in_house"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["blocks"][0]["type"] == "text"
    assert payload["action"] is not None
    assert payload["action"]["status"] == "drafted"
    assert payload["action"]["idempotency_key"] == "chat-action-1"

    action_id = payload["action"]["id"]
    action_resp = client.get(f"/api/v1/chat/sessions/{session['id']}/actions/{action_id}")
    assert action_resp.status_code == 200
    action_payload = action_resp.get_json()
    assert action_payload["id"] == action_id
    assert action_payload["session_id"] == session["id"]


def test_help_message_does_not_create_action(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)

    response = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "help"},
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is None
    assert payload["assistant_message"]["intent_type"] == "help"

    list_resp = client.get(f"/api/v1/chat/sessions/{session['id']}/messages")
    assert list_resp.status_code == 200
    messages = list_resp.get_json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_message_validation_and_state_errors_are_deterministic(authenticated_client):
    client, _, _ = authenticated_client
    session = _create_session(client)

    invalid = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": ""},
    )
    assert invalid.status_code == 400
    invalid_payload = invalid.get_json()
    assert invalid_payload["type"].endswith("/validation-error")
    assert "fields" in invalid_payload

    with client.application.app_context():
        row = db.session.get(ChatSession, session["id"])
        row.status = "closed"
        db.session.commit()

    state_error = client.post(
        f"/api/v1/chat/sessions/{session['id']}/messages",
        json={"content": "R0530"},
    )
    assert state_error.status_code == 409
    state_payload = state_error.get_json()
    assert state_payload["type"].endswith("/invalid-session-state")


def test_chat_session_ownership_scope(authenticated_client, client):
    auth_client, _, _ = authenticated_client
    session = _create_session(auth_client)

    with client.application.app_context():
        other = User(
            email="other-chat-user@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()

        other_store = ShopifyStore(
            user_id=other.id,
            shop_domain="other-chat.myshopify.com",
            shop_name="Other Chat",
            access_token_encrypted=b"other-token",
            is_active=True,
        )
        db.session.add(other_store)

        moved = db.session.get(ChatSession, session["id"])
        moved.user_id = other.id
        moved.store_id = other_store.id
        db.session.commit()

    forbidden = auth_client.get(f"/api/v1/chat/sessions/{session['id']}")
    assert forbidden.status_code == 403
    payload = forbidden.get_json()
    assert payload["type"].endswith("/forbidden")
