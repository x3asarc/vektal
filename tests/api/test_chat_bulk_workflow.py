"""Phase 10-03 bulk chat workflow integration tests."""
from __future__ import annotations

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
            email="chat-bulk@example.com",
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
            shop_domain="chat-bulk.myshopify.com",
            shop_name="Chat Bulk",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Bulk Ops"})
    assert response.status_code == 201
    return response.get_json()["id"]


def test_bulk_action_requires_approval_then_queues_apply(authenticated_client):
    client, _, _ = authenticated_client
    session_id = _create_session(client)

    create_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/bulk/actions",
        json={
            "content": "Update these SKUs",
            "operation": "update_product",
            "skus": ["SKU-100", "SKU-200", "SKU-100", "SKU-300"],
            "idempotency_key": "bulk-approval-1",
        },
    )
    assert create_resp.status_code == 201
    payload = create_resp.get_json()
    action = payload["action"]
    assert action["status"] == "awaiting_approval"
    assert action["payload"]["bulk"] is True
    assert action["payload"]["chunk_plan"]["total_skus"] == 3
    assert action["payload"]["chunk_plan"]["chunk_count"] >= 1

    apply_before_approval = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={},
    )
    assert apply_before_approval.status_code == 409
    assert apply_before_approval.get_json()["type"].endswith("/approval-required")

    approve_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={"comment": "approve bulk"},
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.get_json()
    assert approved["status"] == "approved"
    assert approved["payload"]["approval"]["scope"] == "product"

    apply_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={},
    )
    assert apply_resp.status_code == 200
    applied = apply_resp.get_json()
    assert applied["status"] == "applying"
    assert applied["result"]["status"] == "queued"
    assert isinstance(applied["result"]["task_id"], str)
    assert isinstance(applied["result"]["job_id"], int)


def test_bulk_action_rejects_over_limit_inputs(authenticated_client):
    client, _, _ = authenticated_client
    session_id = _create_session(client)
    over_limit = [f"SKU-{idx:05d}" for idx in range(1, 1002)]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/bulk/actions",
        json={
            "content": "too many skus",
            "operation": "update_product",
            "skus": over_limit,
        },
    )
    assert response.status_code == 422
    assert response.get_json()["type"].endswith("/bulk-limit-exceeded")
