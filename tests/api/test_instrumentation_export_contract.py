"""Phase 13-04 instrumentation export endpoint contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import Product, db
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
def authenticated_client(client):
    with client.application.app_context():
        user = User(
            email="instrument-export@example.com",
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
            shop_domain="instrument-export.myshopify.com",
            shop_name="Instrumentation Export",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Product(
                store_id=store.id,
                title="Export Product",
                sku="SKU-EXPORT-100",
                barcode="100100",
                description="old description",
                price=10.0,
                is_active=True,
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Instrumentation Export"})
    assert response.status_code == 201
    return response.get_json()["id"]


def _seed_signals_via_action_flow(client, session_id: int):
    message = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "update SKU-EXPORT-100", "idempotency_key": "export-seed-idemp"},
    )
    assert message.status_code == 201
    action = message.get_json()["action"]
    groups = action["payload"]["preview"]["groups"]
    change_ids = [change["change_id"] for group in groups for change in group["changes"]]

    approve = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={"selected_change_ids": change_ids, "comment": "seed export"},
    )
    assert approve.status_code == 200
    apply_response = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={"mode": "immediate"},
    )
    assert apply_response.status_code == 200
    return action


def test_instrumentation_export_endpoint_returns_compliance_envelope(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _seed_signals_via_action_flow(client, session_id)

    export = client.post(
        "/api/v1/ops/instrumentation/export",
        json={"action_id": action["id"], "tier": "tier_2", "limit": 100},
    )
    assert export.status_code == 200
    payload = export.get_json()

    assert payload["retention_class"] == "instrumentation_signals"
    assert payload["autonomy_enabled"] is False
    assert payload["generated_at"]
    assert payload["scope"]["store_id"] is not None
    assert payload["filters"]["tier"] == "tier_2"
    assert isinstance(payload["rows"]["preference_signals"], list)
    assert isinstance(payload["rows"]["verification_signals"], list)
    assert isinstance(payload["rows"]["joined_rows"], list)
    assert "trainer" not in payload


def test_instrumentation_export_honors_correlation_filter(authenticated_client):
    client, _ = authenticated_client
    session_id = _create_session(client)
    action = _seed_signals_via_action_flow(client, session_id)
    correlation_id = action["payload"]["runtime"]["correlation_id"]

    filtered = client.post(
        "/api/v1/ops/instrumentation/export",
        json={"correlation_id": correlation_id, "limit": 100},
    )
    assert filtered.status_code == 200
    payload = filtered.get_json()
    assert payload["filters"]["correlation_id"] == correlation_id
    assert payload["rows"]["preference_signals"]
    assert payload["rows"]["verification_signals"]
    assert all(row["correlation_id"] == correlation_id for row in payload["rows"]["preference_signals"])
    assert all(row["correlation_id"] == correlation_id for row in payload["rows"]["verification_signals"])
