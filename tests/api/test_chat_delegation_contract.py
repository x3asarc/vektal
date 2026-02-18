"""Phase 12 Tier-3 delegation contract tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.models import AssistantDelegationEvent, ChatAction, ChatSession, db
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
def tier3_client(client):
    with client.application.app_context():
        user = User(
            email="delegation-tier3@example.com",
            tier=UserTier.TIER_3,
            account_status=AccountStatus.ACTIVE,
            email_verified=True,
            api_version="v1",
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()

        store = ShopifyStore(
            user_id=user.id,
            shop_domain="delegation-tier3.myshopify.com",
            shop_name="Delegation Tier3",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        session = ChatSession(
            user_id=user.id,
            store_id=store.id,
            title="Tier3 Delegation",
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
            payload_json={
                "runtime": {"action_kind": "write"},
                "dry_run_required": True,
                "dry_run_id": 1,
            },
        )
        db.session.add(action)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, user, store, session, action


@pytest.fixture
def tier2_client(client):
    with client.application.app_context():
        user = User(
            email="delegation-tier2@example.com",
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
            shop_domain="delegation-tier2.myshopify.com",
            shop_name="Delegation Tier2",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        session = ChatSession(
            user_id=user.id,
            store_id=store.id,
            title="Tier2 Delegation",
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
            payload_json={"runtime": {"action_kind": "write"}, "dry_run_required": True, "dry_run_id": 1},
        )
        db.session.add(action)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        yield client, session, action


def test_tier3_delegation_enforces_scope_and_lineage(tier3_client):
    client, _, _, session, action = tier3_client
    response = client.post(
        f"/api/v1/chat/sessions/{session.id}/actions/{action.id}/delegate",
        json={
            "parent_request_id": "parent-1",
            "depth": 1,
            "fan_out": 2,
            "requested_tools": ["chat.respond", "agent.spawn_sub_agent", "unknown.tool"],
            "budget": {"max_steps": 8, "max_runtime_seconds": 60},
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "running"
    assert payload["queue"] == "assistant.t3"
    assert isinstance(payload["task_id"], str) and payload["task_id"]
    assert "unknown.tool" in payload["blocked_tools"]
    assert "agent.spawn_sub_agent" in payload["worker_tool_scope"]

    with client.application.app_context():
        row = db.session.get(AssistantDelegationEvent, payload["delegation_event_id"])
        assert row is not None
        assert row.parent_request_id == "parent-1"
        assert row.worker_tool_scope_json == payload["worker_tool_scope"]
        assert row.status == "running"
        assert row.fallback_stage == "delegation_running"


def test_delegation_guardrails_block_excess_depth(tier3_client):
    client, _, _, session, action = tier3_client
    response = client.post(
        f"/api/v1/chat/sessions/{session.id}/actions/{action.id}/delegate",
        json={"depth": 10, "fan_out": 1},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "blocked"
    assert "exceeds max" in (payload["reason"] or "")


def test_non_tier3_user_cannot_delegate(tier2_client):
    client, session, action = tier2_client
    response = client.post(
        f"/api/v1/chat/sessions/{session.id}/actions/{action.id}/delegate",
        json={"depth": 1, "fan_out": 1},
    )
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["type"].endswith("/tier-insufficient")
