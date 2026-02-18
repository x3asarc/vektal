"""Pre-flight validation and Recovery Log routing tests for Phase 8."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.product import Product
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.resolution_snapshot import ResolutionSnapshot
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.resolution.preflight import run_preflight
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
        email="preflight@example.com",
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
        shop_domain="preflight-test.myshopify.com",
        shop_name="Preflight Test",
        access_token_encrypted=b"test-token",
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return user, store


def test_run_preflight_routes_deleted_targets_to_recovery_logs(app):
    with app.app_context():
        user, store = _seed_user_store()
        product = Product(
            store_id=store.id,
            title="Ceramic Vase",
            sku="PREFLIGHT-1",
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
        )
        db.session.add(batch)
        db.session.flush()

        item = ResolutionItem(
            batch_id=batch.id,
            product_id=product.id,
            status="approved",
            product_label="Ceramic Vase",
        )
        db.session.add(item)
        db.session.flush()

        snapshot = ResolutionSnapshot(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
            payload={"title": "Ceramic Vase"},
        )
        db.session.add(snapshot)
        db.session.commit()

        product.is_active = False
        db.session.commit()

        report = run_preflight(batch_id=batch.id, actor_user_id=user.id)
        assert item.id in report.conflicted_item_ids
        assert report.reasons[item.id] == "deleted_target"

        logs = RecoveryLog.query.filter_by(
            batch_id=batch.id,
            item_id=item.id,
            reason_code="deleted_target",
        ).all()
        assert len(logs) == 1
        assert logs[0].snapshot_id == snapshot.id
        assert logs[0].created_by_user_id == user.id

        run_preflight(batch_id=batch.id, actor_user_id=user.id)
        assert (
            RecoveryLog.query.filter_by(
                batch_id=batch.id,
                item_id=item.id,
                reason_code="deleted_target",
            ).count()
            == 1
        )


def test_run_preflight_routes_structural_conflicts_to_recovery_logs(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch = ResolutionBatch(
            user_id=user.id,
            store_id=store.id,
            status="approved",
            apply_mode="immediate",
            created_by_user_id=user.id,
        )
        db.session.add(batch)
        db.session.flush()

        item = ResolutionItem(
            batch_id=batch.id,
            status="structural_conflict",
            structural_state="new_variants_detected",
            conflict_reason="Missing variant Blue in Shopify.",
            product_label="Paint Set",
        )
        db.session.add(item)
        db.session.commit()

        report = run_preflight(batch_id=batch.id, actor_user_id=user.id)
        assert item.id in report.conflicted_item_ids
        assert report.reasons[item.id] == "preflight_conflict"

        log = RecoveryLog.query.filter_by(
            batch_id=batch.id,
            item_id=item.id,
            reason_code="preflight_conflict",
        ).first()
        assert log is not None
        assert "Missing variant Blue" in (log.reason_detail or "")


def test_run_preflight_marks_window_violation(app):
    with app.app_context():
        user, store = _seed_user_store()
        product = Product(
            store_id=store.id,
            title="Notebook",
            sku="PREFLIGHT-2",
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
        )
        db.session.add(batch)
        db.session.flush()

        item = ResolutionItem(
            batch_id=batch.id,
            product_id=product.id,
            status="approved",
            product_label="Notebook",
        )
        db.session.add(item)
        db.session.commit()

        report = run_preflight(
            batch_id=batch.id,
            actor_user_id=user.id,
            mutation_started_at=datetime.now(timezone.utc) - timedelta(seconds=120),
            max_window_seconds=60,
        )
        assert report.within_window is False
        assert report.eligible_item_ids == [item.id]
        assert report.conflicted_item_ids == []

