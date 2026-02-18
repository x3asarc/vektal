"""Products history + diff API contract tests for Phase 11 wave 02."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.api.app import create_openapi_app
from src.models import Product, ProductChangeEvent, ShopifyStore, User, UserTier, AccountStatus, db
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
            email="products-history@example.com",
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
            shop_domain="products-history.myshopify.com",
            shop_name="Products History",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        product = Product(
            store_id=store.id,
            title="Ceramic Vase",
            sku="HIST-001",
            barcode="HISTBAR",
            vendor_code="PENTART",
            description="Original description",
            product_type="decor",
            tags=["ceramic", "home"],
            price=Decimal("12.00"),
            hs_code="6909",
            is_active=True,
            is_published=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            updated_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.session.add(product)
        db.session.flush()

        first_event = ProductChangeEvent(
            product_id=product.id,
            store_id=store.id,
            actor_user_id=user.id,
            source="workspace",
            event_type="bulk_stage",
            before_payload={"title": "Ceramic Vase", "price": 12.0},
            after_payload={"title": "Ceramic Vase Premium", "price": 14.0},
            diff_payload={"title": {"before": "Ceramic Vase", "after": "Ceramic Vase Premium"}},
        )
        second_event = ProductChangeEvent(
            product_id=product.id,
            store_id=store.id,
            actor_user_id=user.id,
            source="workspace",
            event_type="apply",
            before_payload={"title": "Ceramic Vase Premium", "price": 14.0},
            after_payload={"title": "Ceramic Vase Premium", "price": 15.5},
            diff_payload={"price": {"before": 14.0, "after": 15.5}},
        )
        db.session.add_all([first_event, second_event])
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, product, first_event, second_event


def test_product_detail_returns_precision_payload(authenticated_context):
    client, product, _, _ = authenticated_context

    response = client.get(f"/api/v1/products/{product.id}")
    assert response.status_code == 200
    payload = response.get_json()

    assert payload["id"] == product.id
    assert payload["store_id"] == product.store_id
    assert payload["title"] == "Ceramic Vase"
    assert payload["description"] == "Original description"
    assert payload["tags"] == ["ceramic", "home"]
    assert payload["images"] == []


def test_product_history_returns_timeline_with_pagination(authenticated_context):
    client, product, first_event, second_event = authenticated_context

    response = client.get(f"/api/v1/products/{product.id}/history?limit=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["product_id"] == product.id
    assert len(payload["events"]) == 1
    assert payload["events"][0]["id"] == second_event.id
    assert payload["pagination"]["has_next"] is True
    assert payload["pagination"]["next_cursor"] == second_event.id

    next_response = client.get(
        f"/api/v1/products/{product.id}/history?limit=1&cursor={payload['pagination']['next_cursor']}"
    )
    assert next_response.status_code == 200
    next_payload = next_response.get_json()
    assert len(next_payload["events"]) == 1
    assert next_payload["events"][0]["id"] == first_event.id


def test_product_diff_returns_before_after_and_changed_fields(authenticated_context):
    client, product, first_event, second_event = authenticated_context

    response = client.get(
        f"/api/v1/products/{product.id}/diff?from_event_id={first_event.id}&to_event_id={second_event.id}"
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["product_id"] == product.id
    assert payload["from_event_id"] == first_event.id
    assert payload["to_event_id"] == second_event.id
    assert "price" in payload["changed_fields"]
    assert payload["diff_payload"]["price"]["before"] == 14.0
    assert payload["diff_payload"]["price"]["after"] == 15.5
