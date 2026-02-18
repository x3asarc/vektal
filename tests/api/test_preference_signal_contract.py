"""Phase 13-04 preference signal instrumentation contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.instrumentation import InstrumentationLinkError, capture_preference_signal
from src.models import AssistantPreferenceSignal, ChatAction, ChatSession, Product, db
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
            email="preference-signal@example.com",
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
            shop_domain="preference-signal.myshopify.com",
            shop_name="Preference Signal",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Product(
                store_id=store.id,
                title="Preference Product",
                sku="SKU-PREF-100",
                barcode="100100",
                description="old description",
                price=10.0,
                is_active=True,
            )
        )
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store


def _create_session(client):
    response = client.post("/api/v1/chat/sessions", json={"title": "Preference Signals"})
    assert response.status_code == 201
    return response.get_json()["id"]


def _create_update_action(client, session_id: int):
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={
            "content": "update SKU-PREF-100",
            "idempotency_key": "pref-signal-key",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["action"] is not None
    return payload["action"]


def test_approve_action_emits_preference_signal(authenticated_client):
    client, _, _ = authenticated_client
    session_id = _create_session(client)
    action = _create_update_action(client, session_id)

    groups = action["payload"]["preview"]["groups"]
    change_ids = [change["change_id"] for group in groups for change in group["changes"]]
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={
            "selected_change_ids": change_ids,
            "overrides": [{"change_id": change_ids[0], "after_value": "edited value"}],
            "comment": "ship these changes",
        },
    )
    assert response.status_code == 200

    with client.application.app_context():
        rows = AssistantPreferenceSignal.query.filter_by(action_id=action["id"]).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.tier == "tier_2"
        assert row.signal_kind == "edit"
        assert row.preference_signal == "edited"
        assert row.correlation_id
        assert row.override_count == 1
        assert row.selected_change_count >= 1


def test_tier2_preference_signal_requires_correlation_link(authenticated_client):
    client, user, store = authenticated_client

    with client.application.app_context():
        session = ChatSession(
            user_id=user.id,
            store_id=store.id,
            title="Manual Session",
            state="in_house",
            status="active",
            context_json={},
        )
        db.session.add(session)
        db.session.flush()
        action = ChatAction(
            session_id=session.id,
            user_id=user.id,
            store_id=store.id,
            action_type="update_product",
            status="approved",
            payload_json={"runtime": {"route_decision": "tier_2", "action_kind": "write"}},
        )
        db.session.add(action)
        db.session.flush()

        with pytest.raises(InstrumentationLinkError):
            capture_preference_signal(
                action=action,
                user_id=user.id,
                store_id=store.id,
                session_id=session.id,
                signal_kind="approval",
                preference_signal="approved_all",
                require_link=True,
            )
