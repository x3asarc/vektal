"""Recovery Logs API integration tests for Phase 8."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.resolution_snapshot import ResolutionSnapshot
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
            email="recovery@example.com",
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
            shop_domain="recovery-test.myshopify.com",
            shop_name="Recovery Test",
            access_token_encrypted=b"test-token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _seed_recovery_log(*, user_id: int, store_id: int, reason_code: str = "deleted_target") -> RecoveryLog:
    batch = ResolutionBatch(
        user_id=user_id,
        store_id=store_id,
        status="approved",
        apply_mode="scheduled",
        created_by_user_id=user_id,
    )
    db.session.add(batch)
    db.session.flush()

    item = ResolutionItem(
        batch_id=batch.id,
        status="failed",
        product_label="Failed Product",
    )
    db.session.add(item)
    db.session.flush()

    snapshot = ResolutionSnapshot(
        batch_id=batch.id,
        item_id=item.id,
        snapshot_type="product_pre_change",
        payload={"title": "Failed Product"},
    )
    db.session.add(snapshot)
    db.session.flush()

    log = RecoveryLog(
        batch_id=batch.id,
        item_id=item.id,
        store_id=store_id,
        reason_code=reason_code,
        reason_detail="Target product was removed after dry-run approval.",
        payload={"shopify_product_id": None, "product_label": "Failed Product"},
        snapshot_id=snapshot.id,
        created_by_user_id=user_id,
    )
    db.session.add(log)
    db.session.commit()
    return log


def test_recovery_logs_list_and_detail_scoped_to_current_user(authenticated_client):
    client, user, store = authenticated_client

    with client.application.app_context():
        own_log = _seed_recovery_log(user_id=user.id, store_id=store.id)
        own_log_id = own_log.id

        other_user = User(
            email="other-recovery@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other_user.set_password("password123")
        db.session.add(other_user)
        db.session.flush()
        other_store = ShopifyStore(
            user_id=other_user.id,
            shop_domain="other-recovery.myshopify.com",
            shop_name="Other Recovery",
            access_token_encrypted=b"other-token",
            is_active=True,
        )
        db.session.add(other_store)
        db.session.flush()
        other_log = _seed_recovery_log(user_id=other_user.id, store_id=other_store.id)
        other_log_id = other_log.id

    list_resp = client.get("/api/v1/resolution/recovery-logs")
    assert list_resp.status_code == 200
    payload = list_resp.get_json()
    assert payload["total"] >= 1
    ids = {row["id"] for row in payload["logs"]}
    assert own_log_id in ids
    assert other_log_id not in ids

    detail_resp = client.get(f"/api/v1/resolution/recovery-logs/{own_log_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.get_json()["id"] == own_log_id

    forbidden_resp = client.get(f"/api/v1/resolution/recovery-logs/{other_log_id}")
    assert forbidden_resp.status_code == 404


def test_recovery_logs_support_batch_filter(authenticated_client):
    client, user, store = authenticated_client
    with client.application.app_context():
        first = _seed_recovery_log(user_id=user.id, store_id=store.id)
        second = _seed_recovery_log(user_id=user.id, store_id=store.id, reason_code="preflight_conflict")
        first_id = first.id
        first_batch_id = first.batch_id
        second_id = second.id

    filtered = client.get(f"/api/v1/resolution/recovery-logs?batch_id={first_batch_id}")
    assert filtered.status_code == 200
    payload = filtered.get_json()
    assert payload["total"] == 1
    assert payload["logs"][0]["batch_id"] == first_batch_id
    assert payload["logs"][0]["id"] == first_id
    assert payload["logs"][0]["id"] != second_id
