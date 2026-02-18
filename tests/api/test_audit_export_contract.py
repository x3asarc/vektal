"""API contracts for resolution audit export (JSON + CSV)."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.resolution_batch import ResolutionBatch, ResolutionChange, ResolutionItem
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.resolution.snapshot_lifecycle import capture_snapshot
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
            email="audit-export@example.com",
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
            shop_domain="audit-export.myshopify.com",
            shop_name="Audit Export",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

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
            status="approved",
            product_label="Export Product",
        )
        db.session.add(item)
        db.session.flush()

        change = ResolutionChange(
            item_id=item.id,
            field_group="pricing",
            field_name="price",
            before_value=10,
            after_value=12,
            status="approved",
            reason_sentence="Price updated from supplier delta.",
        )
        db.session.add(change)

        capture_snapshot(
            batch_id=batch.id,
            item_id=None,
            snapshot_type="batch_manifest",
            payload={"rows_total": 1, "items_ready": 1},
            allow_dedupe=False,
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, batch


def test_audit_export_json_contract(authenticated_batch):
    client, batch = authenticated_batch
    response = client.get(f"/api/v1/resolution/dry-runs/{batch.id}/audit-export?format=json")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["batch"]["id"] == batch.id
    assert payload["manifest"]["rows_total"] == 1
    assert payload["rows"]
    first = payload["rows"][0]
    assert first["field_name"] == "price"
    assert first["change_status"] == "approved"


def test_audit_export_csv_contract(authenticated_batch):
    client, batch = authenticated_batch
    response = client.get(f"/api/v1/resolution/dry-runs/{batch.id}/audit-export?format=csv")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("text/csv")
    text = response.data.decode("utf-8")
    assert "batch_id,item_id,product_label" in text
    assert "price" in text
