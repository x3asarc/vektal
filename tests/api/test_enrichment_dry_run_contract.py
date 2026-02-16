"""Phase 13.1-03 enrichment lifecycle API contracts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.api.app import create_openapi_app
from src.models import (
    AccountStatus,
    Job,
    JobType,
    Product,
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
            email="enrichment-lifecycle@example.com",
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
            shop_domain="enrichment-lifecycle.myshopify.com",
            shop_name="Enrichment Lifecycle",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Vendor(
                user_id=user.id,
                code="PENTART",
                name="Pentart",
                is_active=True,
            )
        )

        product = Product(
            store_id=store.id,
            title="Original",
            sku="ENRICH-LIFE-001",
            barcode="ENRICH-LIFE-BAR",
            vendor_code="PENTART",
            description="Original description",
            price=Decimal("9.90"),
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

        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        yield client, product, store


def _payload(product_id: int) -> dict:
    return {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "mapping_version": 1,
        "alt_text_policy": "preserve",
        "run_profile": "standard",
        "target_language": "en",
        "dry_run_ttl_minutes": 30,
        "mutations": [
            {
                "product_id": product_id,
                "field_name": "title",
                "current_value": "Original",
                "proposed_value": "Updated title",
                "confidence": 0.93,
                "provenance": {"source": "ai_inferred"},
            },
            {
                "product_id": product_id,
                "field_name": "alt_text",
                "current_value": "old alt",
                "proposed_value": "new alt",
                "confidence": 0.81,
                "provenance": {"source": "ai_inferred"},
            },
        ],
    }


def test_enrichment_lifecycle_start_review_approve_apply(authenticated_context):
    client, product, _store = authenticated_context

    start = client.post("/api/v1/products/enrichment/runs/start", json=_payload(product.id))
    assert start.status_code == 201
    start_body = start.get_json()
    run_id = start_body["run_id"]
    assert start_body["status"] == "dry_run_ready"
    assert start_body["target_language"] == "en"
    assert start_body["write_plan"]["counts"]["blocked"] == 1

    review = client.get(f"/api/v1/products/enrichment/runs/{run_id}/review")
    assert review.status_code == 200
    review_body = review.get_json()
    assert review_body["run_id"] == run_id
    assert review_body["is_stale"] is False
    assert review_body["write_plan"]["counts"]["allowed"] >= 1

    approve = client.post(
        f"/api/v1/products/enrichment/runs/{run_id}/approve",
        json={"approve_all": True, "reviewer_note": "Ship it"},
    )
    assert approve.status_code == 200
    approve_body = approve.get_json()
    assert approve_body["status"] == "approved"
    assert approve_body["write_plan"]["counts"]["approved"] >= 1

    apply = client.post(
        f"/api/v1/products/enrichment/runs/{run_id}/apply",
        json={"confirm_apply": True, "apply_mode": "immediate"},
    )
    assert apply.status_code == 202
    apply_body = apply.get_json()
    assert apply_body["run_id"] == run_id
    assert apply_body["queue"] == "batch.t2"
    assert isinstance(apply_body["job_id"], int)

    with client.application.app_context():
        job = Job.query.get(apply_body["job_id"])
        assert job is not None
        assert job.job_type == JobType.PRODUCT_ENRICH
        assert isinstance(job.parameters, dict)
        assert job.parameters.get("target_language") == "en"


def test_apply_rejects_stale_run(authenticated_context):
    client, product, store = authenticated_context

    start = client.post("/api/v1/products/enrichment/runs/start", json=_payload(product.id))
    assert start.status_code == 201
    run_id = start.get_json()["run_id"]

    with client.application.app_context():
        run = ProductEnrichmentRun.query.filter_by(id=run_id, store_id=store.id).first()
        assert run is not None
        run.dry_run_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        run.status = "dry_run_ready"
        db.session.commit()

    stale_apply = client.post(
        f"/api/v1/products/enrichment/runs/{run_id}/apply",
        json={"confirm_apply": True, "apply_mode": "immediate"},
    )
    assert stale_apply.status_code == 409
    assert stale_apply.get_json()["type"].endswith("/stale-dry-run")
