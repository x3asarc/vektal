"""API contracts for apply progress and terminal summary payload."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
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
def authenticated_batch(client):
    with client.application.app_context():
        user = User(
            email="apply-progress@example.com",
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
            shop_domain="apply-progress.myshopify.com",
            shop_name="Apply Progress",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        batch = ResolutionBatch(
            user_id=user.id,
            store_id=store.id,
            status="applying",
            apply_mode="immediate",
            created_by_user_id=user.id,
            metadata_json={
                "eta_seconds": 42,
                "current_item_id": 999,
                "current_item_label": "In-flight item",
            },
        )
        db.session.add(batch)
        db.session.flush()

        applied = ResolutionItem(batch_id=batch.id, status="applied", product_label="Applied")
        failed = ResolutionItem(batch_id=batch.id, status="failed", product_label="Failed")
        pending = ResolutionItem(batch_id=batch.id, status="approved", product_label="Pending")
        db.session.add_all([applied, failed, pending])
        db.session.flush()

        db.session.add(
            RecoveryLog(
                batch_id=batch.id,
                item_id=failed.id,
                store_id=store.id,
                reason_code="critical_apply_failure",
                reason_detail="Retries exhausted.",
                payload={"item_status": "failed"},
                replay_metadata={"retryable": True},
                created_by_user_id=user.id,
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, batch


def test_apply_progress_payload_contract(authenticated_batch):
    client, batch = authenticated_batch
    response = client.get(f"/api/v1/resolution/dry-runs/{batch.id}/apply/progress")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["batch_id"] == batch.id
    assert payload["status"] == "applying"
    assert payload["processed"] == 2
    assert payload["total"] == 3
    assert payload["eta_seconds"] == 42
    assert payload["current_item"]["id"] == 999
    assert payload["terminal_summary"]["deferred"] == 1
    assert payload["terminal_summary"]["retryable"] == 1
