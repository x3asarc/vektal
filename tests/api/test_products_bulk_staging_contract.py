"""Products bulk staging API contract tests for Phase 11 wave 02."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.api.app import create_openapi_app
from src.models import (
    Product,
    ResolutionBatch,
    ShopifyStore,
    User,
    UserTier,
    AccountStatus,
    Vendor,
    VendorFieldMapping,
    db,
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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_context(client):
    with client.application.app_context():
        user = User(
            email="products-bulk-stage@example.com",
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
            shop_domain="products-bulk-stage.myshopify.com",
            shop_name="Products Bulk Stage",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        vendor = Vendor(
            user_id=user.id,
            code="PENTART",
            name="Pentart",
            is_active=True,
        )
        db.session.add(vendor)
        db.session.flush()

        product = Product(
            store_id=store.id,
            title="Base Product",
            sku="STAGE-001",
            barcode="STAGEBAR",
            vendor_code="PENTART",
            description="Initial",
            price=Decimal("10.00"),
            is_active=True,
            is_published=True,
        )
        db.session.add(product)
        db.session.flush()
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store, vendor, product


def _create_mapping(*, store_id: int, vendor_code: str, field_group: str, version: int = 1, status: str = "ready"):
    mapping = VendorFieldMapping(
        store_id=store_id,
        vendor_code=vendor_code,
        field_group=field_group,
        mapping_version=version,
        coverage_status=status,
        canonical_mapping={"example": "value"},
        required_fields=["title"],
        is_active=True,
    )
    db.session.add(mapping)
    db.session.flush()
    return mapping


def test_bulk_stage_accepts_semantic_blocks_and_returns_admission(authenticated_context):
    client, _, store, _, product = authenticated_context
    with client.application.app_context():
        _create_mapping(store_id=store.id, vendor_code="PENTART", field_group="text")
        db.session.commit()

    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "selection": {
            "scope_mode": "explicit",
            "total_matching": 1,
            "selection_token": "tok-12345678",
            "selected_ids": [product.id],
        },
        "action_blocks": [
            {"operation": "set", "field_name": "title", "value": "Updated Product Title"},
        ],
        "apply_mode": "immediate",
    }
    response = client.post("/api/v1/products/bulk/stage", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["admission"]["schema_ok"] is True
    assert body["admission"]["policy_ok"] is True
    assert body["admission"]["eligible_to_apply"] is True
    assert body["counts"]["selected_products"] == 1
    assert body["mapping_version"] == 1

    with client.application.app_context():
        batch = ResolutionBatch.query.get(body["batch_id"])
        assert batch is not None
        assert (batch.metadata_json or {}).get("action_blocks")


def test_bulk_stage_blocks_on_mapping_gaps_with_remediation(authenticated_context):
    client, _, _, _, product = authenticated_context

    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "selection": {
            "scope_mode": "explicit",
            "total_matching": 1,
            "selection_token": "tok-12345678",
            "selected_ids": [product.id],
        },
        "action_blocks": [
            {"operation": "set", "field_name": "price", "value": 14.5},
        ],
        "apply_mode": "immediate",
    }
    response = client.post("/api/v1/products/bulk/stage", json=payload)
    assert response.status_code == 422
    body = response.get_json()
    assert body["type"].endswith("/vendor-mapping-incomplete")
    assert body["mapping_gaps"]
    assert body["mapping_gaps"][0]["field_group"] == "pricing"
    assert body["admission"]["eligible_to_apply"] is False


def test_bulk_stage_blocks_protected_field_mutation(authenticated_context):
    client, _, store, _, product = authenticated_context
    with client.application.app_context():
        _create_mapping(store_id=store.id, vendor_code="PENTART", field_group="text")
        db.session.commit()

    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "selection": {
            "scope_mode": "explicit",
            "total_matching": 1,
            "selection_token": "tok-12345678",
            "selected_ids": [product.id],
        },
        "action_blocks": [
            {"operation": "set", "field_name": "store_id", "value": 999},
        ],
        "apply_mode": "immediate",
    }
    response = client.post("/api/v1/products/bulk/stage", json=payload)
    assert response.status_code == 422
    body = response.get_json()
    assert body["type"].endswith("/staging-policy-blocked")
    assert "protected" in body["admission"]["reasons"][0]


def test_bulk_stage_alt_text_overwrite_requires_explicit_policy(authenticated_context):
    client, _, store, _, product = authenticated_context
    with client.application.app_context():
        _create_mapping(store_id=store.id, vendor_code="PENTART", field_group="images")
        db.session.commit()

    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "selection": {
            "scope_mode": "explicit",
            "total_matching": 1,
            "selection_token": "tok-12345678",
            "selected_ids": [product.id],
        },
        "action_blocks": [
            {"operation": "set", "field_name": "alt_text", "value": "new alt"},
        ],
        "apply_mode": "immediate",
        "alt_text_policy": "preserve",
    }
    response = client.post("/api/v1/products/bulk/stage", json=payload)
    assert response.status_code == 422
    body = response.get_json()
    assert body["type"].endswith("/staging-policy-blocked")
    assert any("Alt-text overwrite" in reason for reason in body["admission"]["reasons"])
