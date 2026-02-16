"""Phase 13.1 dry-run write-plan policy contract tests."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.api.app import create_openapi_app
from src.models import (
    AccountStatus,
    Product,
    ProductEnrichmentItem,
    ProductEnrichmentRun,
    ShopifyStore,
    User,
    UserTier,
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
            email="enrichment-dry-run@example.com",
            tier=UserTier.TIER_2,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        store = ShopifyStore(
            user_id=user.id,
            shop_domain="enrichment-dry-run.myshopify.com",
            shop_name="Enrichment Dry Run",
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
            title="Original Title",
            sku="ENRICH-001",
            barcode="ENRICHBAR",
            vendor_code="PENTART",
            description="Original description",
            price=Decimal("10.00"),
            is_active=True,
            is_published=True,
        )
        db.session.add(product)
        db.session.flush()

        db.session.add_all(
            [
                VendorFieldMapping(
                    store_id=store.id,
                    vendor_code="PENTART",
                    field_group="text",
                    mapping_version=1,
                    coverage_status="ready",
                    canonical_mapping={"title": "title"},
                    required_fields=["title"],
                    is_active=True,
                ),
                VendorFieldMapping(
                    store_id=store.id,
                    vendor_code="PENTART",
                    field_group="images",
                    mapping_version=1,
                    coverage_status="ready",
                    canonical_mapping={"alt_text": "alt"},
                    required_fields=["alt_text"],
                    is_active=True,
                ),
            ]
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, product


def test_dry_run_plan_persists_items_and_enforces_alt_text_policy(authenticated_context):
    client, product = authenticated_context
    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "mapping_version": 1,
        "alt_text_policy": "preserve",
        "run_profile": "standard",
        "target_language": "de",
        "dry_run_ttl_minutes": 30,
        "mutations": [
            {
                "product_id": product.id,
                "field_name": "title",
                "current_value": "Original Title",
                "proposed_value": "Updated Title",
                "confidence": 0.92,
                "provenance": {"source": "ai_inferred"},
            },
            {
                "product_id": product.id,
                "field_name": "alt_text",
                "current_value": "old alt",
                "proposed_value": "new alt",
                "confidence": 0.84,
                "provenance": {"source": "ai_inferred"},
            },
        ],
    }

    response = client.post("/api/v1/products/enrichment/dry-run-plan", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["write_plan"]["counts"]["allowed"] == 1
    assert body["write_plan"]["counts"]["blocked"] == 1
    assert body["status"] == "dry_run_ready"
    assert body["dry_run_expires_at"] is not None

    blocked_fields = {row["field_name"]: row for row in body["write_plan"]["blocked"]}
    assert "alt_text" in blocked_fields
    assert "alt_text_policy_preserve" in blocked_fields["alt_text"]["reason_codes"]

    with client.application.app_context():
        run = ProductEnrichmentRun.query.get(body["run_id"])
        assert run is not None
        assert run.policy_version >= 1
        assert run.mapping_version == 1
        assert run.alt_text_policy == "preserve"

        items = ProductEnrichmentItem.query.filter_by(run_id=run.id).all()
        assert len(items) == 2
        assert any(item.decision_state == "blocked" for item in items)
        assert any(item.decision_state == "suggested" for item in items)

    second = client.post("/api/v1/products/enrichment/dry-run-plan", json=payload)
    assert second.status_code == 200
    second_body = second.get_json()
    assert second_body["run_id"] == body["run_id"]
