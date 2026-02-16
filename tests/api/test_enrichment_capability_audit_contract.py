"""Phase 13.1 capability audit preflight contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import (
    AccountStatus,
    AssistantFieldPolicy,
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
            email="enrichment-capability@example.com",
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
            shop_domain="enrichment-capability.myshopify.com",
            shop_name="Enrichment Capability",
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

        db.session.add_all(
            [
                VendorFieldMapping(
                    store_id=store.id,
                    vendor_code="PENTART",
                    field_group="text",
                    mapping_version=2,
                    coverage_status="ready",
                    canonical_mapping={"title": "title"},
                    required_fields=["title"],
                    is_active=True,
                ),
                VendorFieldMapping(
                    store_id=store.id,
                    vendor_code="PENTART",
                    field_group="pricing",
                    mapping_version=2,
                    coverage_status="ready",
                    canonical_mapping={"price": "price"},
                    required_fields=["price"],
                    is_active=True,
                ),
                VendorFieldMapping(
                    store_id=store.id,
                    vendor_code="PENTART",
                    field_group="images",
                    mapping_version=2,
                    coverage_status="ready",
                    canonical_mapping={"alt_text": "alt"},
                    required_fields=["alt_text"],
                    is_active=True,
                ),
                AssistantFieldPolicy(
                    store_id=store.id,
                    policy_version=3,
                    immutable_fields_json=["price"],
                    hitl_thresholds_json={"price_change_percent": 15.0},
                    dr_objectives_json={"single_tenant_rto_seconds": 120},
                    is_active=True,
                ),
            ]
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client


def test_capability_audit_returns_allowed_blocked_and_policy_lineage(authenticated_context):
    payload = {
        "supplier_code": "PENTART",
        "supplier_verified": True,
        "requested_fields": ["title", "price", "alt_text"],
        "mapping_version": 2,
        "alt_text_policy": "preserve",
        "run_profile": "standard",
        "target_language": "de",
    }
    response = authenticated_context.post("/api/v1/products/enrichment/capability-audit", json=payload)
    assert response.status_code == 200
    body = response.get_json()

    allowed = {row["field_name"]: row for row in body["allowed_write_plan"]}
    blocked = {row["field_name"]: row for row in body["blocked_write_plan"]}

    assert body["supplier_code"] == "PENTART"
    assert body["policy_version"] == 3
    assert body["mapping_version"] == 2
    assert "title" in allowed
    assert "price" in blocked
    assert blocked["price"]["reason_code"] == "protected_field"
    assert "alt_text" in blocked
    assert blocked["alt_text"]["reason_code"] == "alt_text_policy_preserve"
    assert any("alt_text_policy" in hint for hint in body["upgrade_guidance"])
