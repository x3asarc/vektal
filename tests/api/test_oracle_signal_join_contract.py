"""Phase 13-04 oracle/preference join integrity contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.assistant.instrumentation.export import export_instrumentation_dataset
from src.models import (
    AssistantPreferenceSignal,
    AssistantVerificationSignal,
    ChatAction,
    ChatSession,
    Product,
    User,
    db,
)
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
            email="oracle-join@example.com",
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
            shop_domain="oracle-join.myshopify.com",
            shop_name="Oracle Join",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        db.session.add(
            Product(
                store_id=store.id,
                title="Oracle Product",
                sku="SKU-ORACLE-100",
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
    response = client.post("/api/v1/chat/sessions", json={"title": "Oracle Join"})
    assert response.status_code == 201
    return response.get_json()["id"]


def _create_update_action(client, session_id: int, idempotency_key: str):
    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "update SKU-ORACLE-100", "idempotency_key": idempotency_key},
    )
    assert response.status_code == 201
    action = response.get_json()["action"]
    assert action is not None
    return action


def test_preference_and_oracle_signals_join_one_to_many(authenticated_client):
    client, store = authenticated_client
    session_id = _create_session(client)
    action = _create_update_action(client, session_id, idempotency_key="oracle-join-idemp")
    groups = action["payload"]["preview"]["groups"]
    change_ids = [change["change_id"] for group in groups for change in group["changes"]]

    first_approve = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={"selected_change_ids": change_ids, "comment": "first"},
    )
    assert first_approve.status_code == 200
    second_approve = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/approve",
        json={"selected_change_ids": change_ids[:1], "comment": "second"},
    )
    assert second_approve.status_code == 200

    apply_response = client.post(
        f"/api/v1/chat/sessions/{session_id}/actions/{action['id']}/apply",
        json={"mode": "immediate"},
    )
    assert apply_response.status_code == 200

    with client.application.app_context():
        preferences = AssistantPreferenceSignal.query.filter_by(action_id=action["id"]).all()
        verifications = AssistantVerificationSignal.query.filter_by(action_id=action["id"]).all()
        assert len(preferences) >= 2
        assert len(verifications) >= 1
        correlation_id = preferences[0].correlation_id

        exported = export_instrumentation_dataset(
            store_id=store.id,
            correlation_id=correlation_id,
            action_id=action["id"],
            limit=200,
        )

    assert exported["join_integrity"]["joined_count"] >= 2
    assert exported["join_integrity"]["missing_verification_links"] == []


def test_join_integrity_reports_missing_links(authenticated_client):
    client, store = authenticated_client

    with client.application.app_context():
        user = User.query.filter_by(email="oracle-join@example.com").first()
        session = ChatSession(
            user_id=user.id,
            store_id=store.id,
            title="Join Integrity Session",
            state="in_house",
            status="active",
            context_json={},
        )
        db.session.add(session)
        db.session.flush()
        pref_action = ChatAction(
            session_id=session.id,
            user_id=user.id,
            store_id=store.id,
            action_type="update_product",
            status="approved",
            payload_json={"runtime": {"route_decision": "tier_2", "correlation_id": "corr-missing-pref"}},
        )
        ver_action = ChatAction(
            session_id=session.id,
            user_id=user.id,
            store_id=store.id,
            action_type="update_product",
            status="completed",
            payload_json={"runtime": {"route_decision": "tier_2", "correlation_id": "corr-missing-ver"}},
        )
        db.session.add(pref_action)
        db.session.add(ver_action)
        db.session.flush()

        pref = AssistantPreferenceSignal(
            action_id=pref_action.id,
            session_id=session.id,
            store_id=store.id,
            user_id=user.id,
            correlation_id="corr-missing-pref",
            tier="tier_2",
            signal_kind="approval",
            preference_signal="approved_all",
        )
        ver = AssistantVerificationSignal(
            action_id=ver_action.id,
            session_id=session.id,
            store_id=store.id,
            user_id=user.id,
            verification_event_id=None,
            correlation_id="corr-missing-ver",
            tier="tier_2",
            verification_status="verified",
            oracle_signal=True,
            attempt_count=1,
            waited_seconds=0,
        )
        db.session.add(pref)
        db.session.add(ver)
        db.session.commit()

        exported = export_instrumentation_dataset(store_id=store.id, limit=200)

    assert pref.id in exported["join_integrity"]["missing_verification_links"]
    assert ver.id in exported["join_integrity"]["missing_preference_links"]
