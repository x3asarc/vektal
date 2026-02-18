"""Integration tests for Phase 8 resolution rules + lock endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.resolution_batch import ResolutionBatch
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
def authenticated_client(app, client):
    with app.app_context():
        user = User(
            email="resolution@example.com",
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
            shop_domain="resolution-test.myshopify.com",
            shop_name="Resolution Test",
            access_token_encrypted=b"test-token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def test_rule_crud_flow(authenticated_client):
    client, _, _ = authenticated_client

    create_resp = client.post(
        "/api/v1/resolution/rules",
        json={
            "supplier_code": "PENTART",
            "field_group": "pricing",
            "rule_type": "auto_apply",
            "action": "auto_apply",
            "consented": True,
            "enabled": True,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    rule_id = created["id"]

    list_resp = client.get("/api/v1/resolution/rules")
    assert list_resp.status_code == 200
    listed = list_resp.get_json()
    assert listed["total"] >= 1
    assert any(rule["id"] == rule_id for rule in listed["rules"])

    patch_resp = client.patch(
        f"/api/v1/resolution/rules/{rule_id}",
        json={"enabled": False, "action": "require_approval"},
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.get_json()
    assert patched["enabled"] is False
    assert patched["action"] == "require_approval"

    delete_resp = client.delete(f"/api/v1/resolution/rules/{rule_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["deleted"] is True


def test_lock_acquire_and_conflict(authenticated_client):
    client, user, store = authenticated_client

    with client.application.app_context():
        second_user = User(
            email="resolution-other@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        second_user.set_password("password123")
        db.session.add(second_user)
        db.session.flush()
        second_user_id = second_user.id

        batch = ResolutionBatch(
            user_id=user.id,
            store_id=store.id,
            status="ready_for_review",
            apply_mode="immediate",
            created_by_user_id=user.id,
        )
        db.session.add(batch)
        db.session.commit()
        batch_id = batch.id

    acquire_resp = client.post(f"/api/v1/resolution/locks/{batch_id}/acquire", json={"lease_seconds": 180})
    assert acquire_resp.status_code == 200
    acquired = acquire_resp.get_json()
    assert acquired["locked"] is True
    assert acquired["lock_owner_user_id"] == user.id

    with client.application.app_context():
        row = ResolutionBatch.query.get(batch_id)
        row.lock_owner_user_id = second_user_id
        row.lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)
        db.session.commit()

    conflict_resp = client.post(f"/api/v1/resolution/locks/{batch_id}/acquire", json={"lease_seconds": 180})
    assert conflict_resp.status_code == 409
    payload = conflict_resp.get_json()
    assert payload["type"].endswith("/batch-lock-conflict")
