"""Phase 13.1-04 enrichment lineage audit export contracts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
            email="enrichment-export@example.com",
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
            shop_domain="enrichment-export.myshopify.com",
            shop_name="Enrichment Export",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        product = Product(
            store_id=store.id,
            title="Enrichment Export Product",
            sku="ENRICH-EXPORT-001",
            barcode="900001",
            vendor_code="PENTART",
            description="seed",
            price=10.0,
            is_active=True,
            is_published=True,
        )
        db.session.add(product)
        db.session.flush()

        run = ProductEnrichmentRun(
            user_id=user.id,
            store_id=store.id,
            vendor_code="PENTART",
            run_profile="deep",
            target_language="de",
            status="approved",
            policy_version=4,
            mapping_version=2,
            idempotency_hash="hash-export-001",
            dry_run_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            alt_text_policy="preserve",
            protected_columns_json=["price"],
            capability_audit_json={},
            metadata_json={"oracle_decision": "approved_ready_for_apply"},
        )
        db.session.add(run)
        db.session.flush()

        db.session.add_all(
            [
                    ProductEnrichmentItem(
                        run_id=run.id,
                        product_id=product.id,
                    field_group="text",
                    field_name="title",
                    decision_state="approved",
                    before_value="old title",
                    after_value="new title",
                    confidence=0.91,
                    provenance={"source": "ai_inferred"},
                    reason_codes=["allowed"],
                    evidence_refs=[],
                    requires_user_action=True,
                    is_protected_column=False,
                    alt_text_preserved=True,
                    policy_version=4,
                    mapping_version=2,
                    metadata_json={"oracle_decision": "accept"},
                ),
                    ProductEnrichmentItem(
                        run_id=run.id,
                        product_id=product.id,
                    field_group="pricing",
                    field_name="price",
                    decision_state="blocked",
                    before_value=10.0,
                    after_value=12.0,
                    confidence=0.88,
                    provenance={"source": "ai_inferred"},
                    reason_codes=["protected_field"],
                    evidence_refs=[],
                    requires_user_action=True,
                    is_protected_column=True,
                    alt_text_preserved=True,
                    policy_version=4,
                    mapping_version=2,
                    metadata_json={},
                ),
            ]
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, store, run


def test_enrichment_audit_export_returns_lineage_retention_contract(authenticated_context):
    client, _store, run = authenticated_context

    response = client.post(
        "/api/v1/ops/enrichment/audit-export",
        json={"run_id": run.id, "include_blocked": True, "include_protected": True, "limit": 100},
    )
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["retention_class"] == "enrichment_lineage"
    assert payload["retention_policy"]["audit_export_days"] == 365
    assert payload["scope"]["run_id"] == run.id
    assert payload["counts"]["run_count"] == 1
    assert payload["counts"]["lineage_count"] == 2
    assert payload["counts"]["blocked_count"] == 1
    assert payload["counts"]["protected_count"] == 1
    assert isinstance(payload["rows"]["lineage"], list)
    assert payload["rows"]["lineage"][0]["policy_version"] == 4
    assert "oracle_decision" in payload["rows"]["lineage"][0]


def test_enrichment_audit_export_honors_blocked_filter(authenticated_context):
    client, _store, run = authenticated_context
    response = client.post(
        "/api/v1/ops/enrichment/audit-export",
        json={"run_id": run.id, "include_blocked": False, "include_protected": True},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["counts"]["lineage_count"] == 1
    assert payload["counts"]["blocked_count"] == 0
    assert all(row["decision_state"] != "blocked" for row in payload["rows"]["lineage"])
