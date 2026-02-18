"""Snapshot lifecycle contracts for Phase 11 wave 3."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.resolution.snapshot_lifecycle import (
    capture_snapshot,
    ensure_store_baseline,
    is_batch_fresh,
    resolve_snapshot_chain,
    stamp_batch_ttl,
)
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _seed_user_store() -> tuple[User, ShopifyStore]:
    user = User(
        email="snapshot-lifecycle@example.com",
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
        shop_domain="snapshot-lifecycle.myshopify.com",
        shop_name="Snapshot Lifecycle",
        access_token_encrypted=b"token",
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return user, store


def _seed_batch(*, user_id: int, store_id: int) -> ResolutionBatch:
    batch = ResolutionBatch(
        user_id=user_id,
        store_id=store_id,
        status="ready_for_review",
        apply_mode="immediate",
        created_by_user_id=user_id,
    )
    db.session.add(batch)
    db.session.flush()
    return batch


def test_baseline_snapshot_reused_within_policy_window(app):
    with app.app_context():
        user, store = _seed_user_store()
        first_batch = _seed_batch(user_id=user.id, store_id=store.id)
        first_baseline, created = ensure_store_baseline(batch=first_batch)
        assert created is True

        second_batch = _seed_batch(user_id=user.id, store_id=store.id)
        second_baseline, created_second = ensure_store_baseline(batch=second_batch)
        assert created_second is False
        assert second_baseline.id == first_baseline.id


def test_manifest_snapshot_dedup_uses_canonical_pointer(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch = _seed_batch(user_id=user.id, store_id=store.id)

        first = capture_snapshot(
            batch_id=batch.id,
            item_id=None,
            snapshot_type="batch_manifest",
            payload={"rows_total": 2, "items_ready": 2},
            allow_dedupe=True,
        )
        second = capture_snapshot(
            batch_id=batch.id,
            item_id=None,
            snapshot_type="batch_manifest",
            payload={"rows_total": 2, "items_ready": 2},
            allow_dedupe=True,
        )

        assert second.canonical_snapshot_id == first.id
        assert second.payload["deduped_from"] == first.id


def test_snapshot_chain_and_ttl_helpers(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch = _seed_batch(user_id=user.id, store_id=store.id)
        item = ResolutionItem(
            batch_id=batch.id,
            status="approved",
            product_label="Chain Product",
        )
        db.session.add(item)
        db.session.flush()

        baseline, _ = ensure_store_baseline(batch=batch)
        manifest = capture_snapshot(
            batch_id=batch.id,
            item_id=None,
            snapshot_type="batch_manifest",
            payload={"rows_total": 1},
            allow_dedupe=False,
        )
        pre_change = capture_snapshot(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
            payload={"title": "Before"},
            allow_dedupe=False,
        )

        stamp_batch_ttl(batch, ttl_minutes=1)
        db.session.commit()
        assert is_batch_fresh(batch) is True

        metadata = dict(batch.metadata_json or {})
        metadata["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        batch.metadata_json = metadata
        db.session.commit()
        assert is_batch_fresh(batch) is False

        chain = resolve_snapshot_chain(batch_id=batch.id, item_id=item.id)
        assert chain["baseline_snapshot_id"] == baseline.id
        assert chain["manifest_snapshot_id"] == manifest.id
        assert chain["product_pre_change_snapshot_id"] == pre_change.id
