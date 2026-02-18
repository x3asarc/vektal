"""Products search API contract tests for Phase 11 wave 01."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.api.app import create_openapi_app
from src.models import Product, ShopifyStore, User, UserTier, AccountStatus, db
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
            email="products-search@example.com",
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
            shop_domain="products-search.myshopify.com",
            shop_name="Products Search",
            access_token_encrypted=b"test-token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        base_time = datetime.now(timezone.utc)
        products = [
            Product(
                store_id=store.id,
                title="Blue Ceramic Vase",
                sku="SKU-001",
                barcode="111",
                vendor_code="PENTART",
                product_type="decor",
                tags=["ceramic", "blue"],
                price=Decimal("19.99"),
                hs_code="6909",
                is_active=True,
                is_published=True,
                created_at=base_time - timedelta(minutes=3),
                updated_at=base_time - timedelta(minutes=3),
            ),
            Product(
                store_id=store.id,
                title="Blue Acrylic Paint",
                sku="SKU-002",
                barcode="222",
                vendor_code="PENTART",
                product_type="paint",
                tags=["paint", "blue"],
                price=Decimal("8.50"),
                hs_code="3208",
                is_active=True,
                is_published=False,
                created_at=base_time - timedelta(minutes=2),
                updated_at=base_time - timedelta(minutes=2),
            ),
            Product(
                store_id=store.id,
                title="Green Sculpting Tool",
                sku="SKU-003",
                barcode="333",
                vendor_code="TOOLSCO",
                product_type="tool",
                tags=["tool", "green"],
                price=Decimal("12.00"),
                hs_code="8205",
                is_active=False,
                is_published=False,
                created_at=base_time - timedelta(minutes=1),
                updated_at=base_time - timedelta(minutes=1),
            ),
        ]
        db.session.add_all(products)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def test_search_supports_combined_filters_and_scope_metadata(authenticated_client):
    client, _, _ = authenticated_client

    response = client.get(
        "/api/v1/products/search"
        "?vendor_code=PENTART"
        "&status=active"
        "&q=Blue"
        "&sort_by=created_at"
        "&sort_dir=desc"
        "&scope_mode=filtered"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["scope"]["scope_mode"] == "filtered"
    assert payload["scope"]["total_matching"] == 1
    assert payload["scope"]["selection_token"]
    assert len(payload["data"]) == 1
    assert payload["data"][0]["sku"] == "SKU-001"


def test_search_cursor_pagination_is_deterministic(authenticated_client):
    client, _, _ = authenticated_client

    first = client.get("/api/v1/products/search?limit=1&sort_by=created_at&sort_dir=desc")
    assert first.status_code == 200
    first_payload = first.get_json()
    assert first_payload["pagination"]["has_next"] is True
    assert first_payload["pagination"]["next_cursor"]
    first_id = first_payload["data"][0]["id"]

    second = client.get(
        f"/api/v1/products/search?limit=1&sort_by=created_at&sort_dir=desc&cursor={first_payload['pagination']['next_cursor']}"
    )
    assert second.status_code == 200
    second_payload = second.get_json()
    assert second_payload["data"][0]["id"] != first_id


def test_search_rejects_unknown_filter_fields(authenticated_client):
    client, _, _ = authenticated_client

    response = client.get("/api/v1/products/search?unknown_field=1")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["type"].endswith("/validation-error")
    assert any("unknown_field" in key for key in payload["fields"])


def test_search_rejects_cursor_sort_mismatch(authenticated_client):
    client, _, _ = authenticated_client
    initial = client.get("/api/v1/products/search?limit=1&sort_by=title&sort_dir=asc")
    assert initial.status_code == 200
    cursor = initial.get_json()["pagination"]["next_cursor"]
    assert cursor

    mismatch = client.get(f"/api/v1/products/search?limit=1&sort_by=price&sort_dir=asc&cursor={cursor}")
    assert mismatch.status_code == 400
    payload = mismatch.get_json()
    assert payload["type"].endswith("/invalid-cursor")


def test_search_surface_includes_protected_column_metadata(authenticated_client):
    client, _, _ = authenticated_client

    response = client.get("/api/v1/products/search?limit=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]
    protected_columns = payload["data"][0]["protected_columns"]
    assert "id" in protected_columns
    assert "store_id" in protected_columns
    assert "shopify_product_id" in protected_columns


def test_search_rejects_inventory_filter_until_supported(authenticated_client):
    client, _, _ = authenticated_client

    response = client.get("/api/v1/products/search?inventory_total_min=10")
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["type"].endswith("/unsupported-filter")
    assert "inventory_total" in payload["unsupported_fields"]
