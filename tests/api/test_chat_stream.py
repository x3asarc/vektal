"""SSE contract checks for chat streaming."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.api.app import create_openapi_app
from src.models import db
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
            email="chat-stream@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        db.session.add(
            ShopifyStore(
                user_id=user.id,
                shop_domain="chat-stream.myshopify.com",
                shop_name="Chat Stream",
                access_token_encrypted=b"token",
                is_active=True,
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Stream"})
    assert response.status_code == 201
    return response.get_json()["id"]


def test_chat_stream_emits_named_event_and_proxy_safe_headers(authenticated_client):
    client = authenticated_client
    session_id = _create_session(client)

    response = client.get(f"/api/v1/chat/sessions/{session_id}/stream", buffered=False)
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.headers.get("Cache-Control") == "no-cache"
    assert response.headers.get("X-Accel-Buffering") == "no"

    first_chunk = next(response.response).decode("utf-8")
    assert "event: chat_session_state" in first_chunk
    assert "data:" in first_chunk

    response.close()


def test_chat_stream_route_uses_context_safe_generator_and_named_events():
    text = Path("src/api/v1/chat/routes.py").read_text(encoding="utf-8")
    assert "stream_with_context(generate())" in text
    assert 'event="chat_session_state"' in text
    assert 'event="chat_heartbeat"' in text
    assert 'event_type="message"' in text
    assert 'event_type="action"' in text
