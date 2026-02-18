"""Integration tests for Phase 8 dry-run API endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.models import db
from src.models.product import Product
from src.models.resolution_batch import ResolutionBatch
from src.models.shopify import ShopifyStore
from src.models.user import AccountStatus, User, UserTier
from src.models.vendor import Vendor, VendorCatalogItem
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
            email="dryrun@example.com",
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
            shop_domain="dryrun-test.myshopify.com",
            shop_name="DryRun Test",
            access_token_encrypted=b"test-token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Product(
                store_id=store.id,
                title="Ceramic Vase",
                sku="SKU-10",
                barcode="10010",
                price=12.0,
                is_active=True,
            )
        )

        vendor = Vendor(user_id=user.id, name="Pentart", code="PENTART", is_active=True)
        db.session.add(vendor)
        db.session.flush()
        db.session.add(
            VendorCatalogItem(
                vendor_id=vendor.id,
                sku="SKU-10",
                barcode="10010",
                name="Supplier Vase",
                price=13.0,
                is_active=True,
                raw_data={"product_type": "Decor"},
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def test_create_and_read_dry_run(authenticated_client):
    client, _, _ = authenticated_client

    create_resp = client.post(
        "/api/v1/resolution/dry-runs",
        json={
            "supplier_code": "PENTART",
            "supplier_verified": True,
            "rows": [{"sku": "SKU-10", "price": 14.5, "title": "Supplier Vase"}],
        },
    )
    assert create_resp.status_code == 201
    create_payload = create_resp.get_json()
    batch_id = create_payload["batch_id"]
    assert create_payload["status"] == "ready_for_review"

    read_resp = client.get(f"/api/v1/resolution/dry-runs/{batch_id}")
    assert read_resp.status_code == 200
    body = read_resp.get_json()
    assert body["batch_id"] == batch_id
    assert len(body["groups"]) == 1
    change = body["groups"][0]["changes"][0]
    assert "reason_sentence" in change
    assert "confidence_score" in change
    assert "confidence_badge" in change

    lineage_resp = client.get(f"/api/v1/resolution/dry-runs/{batch_id}/lineage")
    assert lineage_resp.status_code == 200
    lineage_payload = lineage_resp.get_json()
    assert lineage_payload["batch_id"] == batch_id
    assert len(lineage_payload["entries"]) >= 1


def test_create_dry_run_invalid_row_returns_422(authenticated_client):
    client, _, _ = authenticated_client
    resp = client.post(
        "/api/v1/resolution/dry-runs",
        json={
            "supplier_code": "PENTART",
            "supplier_verified": True,
            "rows": [{"price": 12.0}],
        },
    )
    assert resp.status_code == 422
    payload = resp.get_json()
    assert payload["type"].endswith("/invalid-dry-run-row")


def test_get_dry_run_forbidden_for_other_user(client, authenticated_client):
    auth_client, _, _ = authenticated_client

    create_resp = auth_client.post(
        "/api/v1/resolution/dry-runs",
        json={
            "supplier_code": "PENTART",
            "supplier_verified": True,
            "rows": [{"sku": "SKU-10", "price": 14.5}],
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.get_json()["batch_id"]

    with client.application.app_context():
        other = User(
            email="other-resolution@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        other_store = ShopifyStore(
            user_id=other.id,
            shop_domain="other-resolution-test.myshopify.com",
            shop_name="Other",
            access_token_encrypted=b"other-token",
            is_active=True,
        )
        db.session.add(other_store)
        batch = db.session.get(ResolutionBatch, batch_id)
        batch.user_id = other.id
        db.session.commit()

    forbidden_resp = auth_client.get(f"/api/v1/resolution/dry-runs/{batch_id}")
    assert forbidden_resp.status_code == 403


def test_get_dry_run_require_lock_returns_409(authenticated_client):
    client, user, store = authenticated_client
    create_resp = client.post(
        "/api/v1/resolution/dry-runs",
        json={
            "supplier_code": "PENTART",
            "supplier_verified": True,
            "rows": [{"sku": "SKU-10", "price": 15.0}],
        },
    )
    assert create_resp.status_code == 201
    batch_id = create_resp.get_json()["batch_id"]

    with client.application.app_context():
        other = User(
            email="lock-owner@example.com",
            tier=UserTier.TIER_1,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        other.set_password("password123")
        db.session.add(other)
        db.session.flush()
        batch = db.session.get(ResolutionBatch, batch_id)
        batch.lock_owner_user_id = other.id
        batch.lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.session.commit()

    conflict = client.get(f"/api/v1/resolution/dry-runs/{batch_id}?require_lock=true")
    assert conflict.status_code == 409
    payload = conflict.get_json()
    assert payload["type"].endswith("/batch-lock-conflict")
