"""Phase 10-02 single-SKU chat workflow integration tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.chat_action import ChatAction
from src.models.product import Product
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
            email="chat-single-sku@example.com",
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
            shop_domain="chat-single-sku.myshopify.com",
            shop_name="Chat Single SKU",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Product(
                store_id=store.id,
                title="Existing Product",
                sku="SKU-100",
                barcode="100100",
                description="old description",
                price=10.0,
                is_active=True,
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Single SKU"})
    assert response.status_code == 201
    return response.get_json()["id"]


def _create_action(client, session_id: int, *, content: str, action_hints: dict | None = None):
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "content": content,
            "idempotency_key": f"idemp-{content.lower().replace(' ', '-')}",
            "action_hints": action_hints or {},
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is not None
    return payload["action"]


def test_requires_dry_run_and_blocks_apply_without_approval(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_action(client, session_id, content="update SKU-100")

    assert action["status"] == "dry_run_ready"
    assert action["payload"]["dry_run_required"] is True
    assert isinstance(action["payload"]["dry_run_id"], int)

    apply_resp = client.post(f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply", json={})
    assert apply_resp.status_code == 409
    assert apply_resp.get_json()["type"].endswith("/approval-required")


def test_draft_first_create_and_publish_gate_defaults(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_action(client, session_id, content="add SKU-NEW")

    defaults = action["payload"]["create_defaults"]
    assert defaults["draft_first"] is True
    assert defaults["publish_requested"] is False
    assert defaults["publish_allowed"] is False
    assert defaults["publish_policy"] == "explicit"


def test_variant_bulk_path_for_multi_variant_hint(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_action(
        client,
        session_id,
        content="add SKU-VARIANT",
        action_hints={"variant_options": ["Red", "Blue", "Green"]},
    )
    assert action["payload"]["variant_mutation_path"] == "productVariantsBulkCreate"


def test_approve_then_apply_success_path(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_action(client, session_id, content="update SKU-100")
    dry_run_id = action["payload"]["dry_run_id"]

    with client.application.app_context():
        action_row = ChatAction.query.get(action["id"])
        groups = action_row.payload_json["preview"]["groups"]
        change_ids = [change["change_id"] for group in groups for change in group["changes"]]

    approve_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={
            "selected_change_ids": change_ids,
            "overrides": [{"change_id": change_ids[0], "after_value": "overridden description"}],
            "comment": "approve product update",
        },
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.get_json()
    assert approved["status"] == "approved"
    assert approved["payload"]["approval"]["scope"] == "product"

    apply_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={"mode": "immediate"},
    )
    assert apply_resp.status_code == 200
    applied = apply_resp.get_json()
    assert applied["status"] in {"completed", "partial"}
    assert applied["result"]["status"] in {"applied", "applied_with_conflicts"}
    assert isinstance(applied["result"]["applied_item_ids"], list)
    assert applied["payload"]["dry_run_id"] == dry_run_id


def test_conflict_hold_and_recovery_linkage(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_action(client, session_id, content="add SKU-CONFLICT")

    approve_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={},
    )
    assert approve_resp.status_code == 200

    apply_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={},
    )
    assert apply_resp.status_code == 200
    payload = apply_resp.get_json()
    assert payload["status"] == "conflicted"
    assert payload["result"]["status"] == "conflicted"
    assert len(payload["result"]["conflicted_item_ids"]) >= 1
    assert isinstance(payload["result"]["recovery_log_ids"], list)
