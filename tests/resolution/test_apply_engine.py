"""Guarded apply engine tests for Phase 8 throughput and safety policy."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.resolution_batch import ResolutionBatch, ResolutionChange, ResolutionItem
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.resolution.apply_engine import apply_batch
from src.resolution.preflight import PreflightReport
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
        email="apply-engine@example.com",
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
        shop_domain="apply-engine-test.myshopify.com",
        shop_name="Apply Engine Test",
        access_token_encrypted=b"test-token",
        is_active=True,
    )
    db.session.add(store)
    db.session.flush()
    return user, store


def _seed_batch_with_items(
    *,
    user_id: int,
    store_id: int,
    apply_mode: str = "immediate",
    critical_error_threshold: int = 3,
    item_count: int = 3,
) -> tuple[ResolutionBatch, list[ResolutionItem]]:
    batch = ResolutionBatch(
        user_id=user_id,
        store_id=store_id,
        status="approved",
        apply_mode=apply_mode,
        critical_error_threshold=critical_error_threshold,
        created_by_user_id=user_id,
        metadata_json={"initial_concurrency": 5},
    )
    db.session.add(batch)
    db.session.flush()

    items: list[ResolutionItem] = []
    for idx in range(item_count):
        item = ResolutionItem(
            batch_id=batch.id,
            status="approved",
            product_label=f"Product {idx + 1}",
        )
        db.session.add(item)
        db.session.flush()
        db.session.add(
            ResolutionChange(
                item_id=item.id,
                field_group="pricing",
                field_name="price",
                before_value=10 + idx,
                after_value=11 + idx,
                status="awaiting_approval",
            )
        )
        items.append(item)

    db.session.commit()
    return batch, items


def _report(
    *,
    batch_id: int,
    within_window: bool,
    eligible: list[int],
    conflicted: list[int],
    reasons: dict[int, str] | None = None,
) -> PreflightReport:
    return PreflightReport(
        batch_id=batch_id,
        executed_at=datetime.now(timezone.utc),
        within_window=within_window,
        eligible_item_ids=eligible,
        conflicted_item_ids=conflicted,
        reasons=reasons or {},
    )


def test_apply_batch_fails_fast_when_preflight_window_is_invalid(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch, items = _seed_batch_with_items(user_id=user.id, store_id=store.id)
        mutation_calls: list[int] = []

        def _handler(*, item, idempotency_key, mode):
            mutation_calls.append(item.id)
            return {"success": True, "critical": False}

        result = apply_batch(
            batch_id=batch.id,
            actor_user_id=user.id,
            mutation_handler=_handler,
            preflight_report=_report(
                batch_id=batch.id,
                within_window=False,
                eligible=[items[0].id],
                conflicted=[items[1].id],
            ),
        )
        db.session.refresh(batch)

        assert mutation_calls == []
        assert result.status == "failed"
        assert result.conflicted_item_ids == [items[1].id]
        assert batch.metadata_json.get("preflight_window_violation") is True


def test_apply_batch_pauses_when_critical_errors_exceed_threshold(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch, items = _seed_batch_with_items(
            user_id=user.id,
            store_id=store.id,
            critical_error_threshold=1,
            item_count=3,
        )

        def _handler(*, item, idempotency_key, mode):
            return {"success": False, "critical": True}

        result = apply_batch(
            batch_id=batch.id,
            actor_user_id=user.id,
            mutation_handler=_handler,
            preflight_report=_report(
                batch_id=batch.id,
                within_window=True,
                eligible=[item.id for item in items],
                conflicted=[],
            ),
        )
        db.session.refresh(batch)

        assert result.paused is True
        assert result.critical_errors == 2
        assert len(result.failed_item_ids) == 2
        assert batch.status == "failed"
        assert batch.metadata_json.get("paused_due_to_critical_errors") is True


def test_apply_batch_scheduled_mode_reruns_conflicted_items_only(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch, items = _seed_batch_with_items(
            user_id=user.id,
            store_id=store.id,
            apply_mode="scheduled",
            item_count=2,
        )

        def _handler(*, item, idempotency_key, mode):
            return {"success": True, "critical": False}

        result = apply_batch(
            batch_id=batch.id,
            actor_user_id=user.id,
            mode="scheduled",
            mutation_handler=_handler,
            preflight_report=_report(
                batch_id=batch.id,
                within_window=True,
                eligible=[items[0].id],
                conflicted=[items[1].id],
                reasons={items[1].id: "deleted_target"},
            ),
        )
        db.session.refresh(batch)

        assert result.status == "applied_with_conflicts"
        assert result.applied_item_ids == [items[0].id]
        assert result.rerun_conflicted_item_ids == [items[1].id]
        assert batch.metadata_json.get("rerun_conflicted_only") == [items[1].id]


def test_apply_batch_tracks_backoff_events_from_throttle_signals(app):
    with app.app_context():
        user, store = _seed_user_store()
        batch, items = _seed_batch_with_items(user_id=user.id, store_id=store.id, item_count=1)
        sleep_calls: list[float] = []

        def _handler(*, item, idempotency_key, mode):
            return {
                "success": True,
                "critical": False,
                "throttle": {
                    "currently_available": 0,
                    "maximum_available": 40,
                    "restore_rate": 2,
                },
            }

        result = apply_batch(
            batch_id=batch.id,
            actor_user_id=user.id,
            mutation_handler=_handler,
            preflight_report=_report(
                batch_id=batch.id,
                within_window=True,
                eligible=[items[0].id],
                conflicted=[],
            ),
            sleep_fn=lambda seconds: sleep_calls.append(seconds),
        )

        assert result.status == "applied"
        assert result.backoff_events == 1
        assert sleep_calls and sleep_calls[0] >= 1.0

