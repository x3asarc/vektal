"""API contracts for snapshot-chain and stale-preflight behavior."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.product import Product
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.resolution.snapshot_lifecycle import capture_snapshot, ensure_store_baseline
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
def authenticated_context(client):
    with client.application.app_context():
        user = User(
            email="snapshot-chain@example.com",
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
            shop_domain="snapshot-chain.myshopify.com",
            shop_name="Snapshot Chain",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        product = Product(
            store_id=store.id,
            title="Snapshot Product",
            sku="SNAP-001",
            is_active=True,
        )
        db.session.add(product)
        db.session.flush()

        batch = ResolutionBatch(
            user_id=user.id,
            store_id=store.id,
            status="approved",
            apply_mode="scheduled",
            created_by_user_id=user.id,
            metadata_json={
                "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "dry_run_ttl_minutes": 60,
            },
        )
        db.session.add(batch)
        db.session.flush()

        item = ResolutionItem(
            batch_id=batch.id,
            product_id=product.id,
            status="approved",
            product_label="Snapshot Product",
        )
        db.session.add(item)
        db.session.flush()

        ensure_store_baseline(batch=batch)
        capture_snapshot(
            batch_id=batch.id,
            item_id=None,
            snapshot_type="batch_manifest",
            payload={"rows_total": 1},
            allow_dedupe=False,
        )
        capture_snapshot(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
            payload={"title": "Snapshot Product"},
            allow_dedupe=False,
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, batch, item


def test_snapshot_chain_endpoint_returns_baseline_manifest_prechange(authenticated_context):
    client, _, batch, item = authenticated_context
    response = client.get(f"/api/v1/resolution/dry-runs/{batch.id}/snapshot-chain?item_id={item.id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["batch_id"] == batch.id
    assert payload["item_id"] == item.id
    assert payload["baseline_snapshot_id"] is not None
    assert payload["manifest_snapshot_id"] is not None
    assert payload["product_pre_change_snapshot_id"] is not None


def test_preflight_flags_stale_batches_and_routes_items_to_conflict(authenticated_context):
    client, _, batch, item = authenticated_context
    response = client.post(f"/api/v1/resolution/dry-runs/{batch.id}/preflight")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["within_window"] is False
    assert item.id in payload["conflicted_item_ids"]
    assert payload["reasons"][str(item.id)] == "stale_target"
