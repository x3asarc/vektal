"""Phase 13-02 tenant field policy and threshold enforcement tests."""
from __future__ import annotations

import pytest

from src.api.app import create_openapi_app
from src.api.v1.chat.approvals import approve_product_action
from src.models import ChatAction, ChatSession, ResolutionBatch, ResolutionChange, ResolutionItem, db
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


def test_immutable_fields_are_blocked_and_threshold_hits_are_tracked(app):
    with app.app_context():
        user = User(
            email="field-policy-contract@example.com",
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
            shop_domain="field-policy-contract.myshopify.com",
            shop_name="Field Policy Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        session = ChatSession(
            user_id=user.id,
            store_id=store.id,
            title="Field Policy Session",
            state="in_house",
            status="active",
            context_json={},
        )
        db.session.add(session)
        db.session.flush()

        batch = ResolutionBatch(
            user_id=user.id,
            store_id=store.id,
            status="ready_for_review",
            apply_mode="immediate",
            created_by_user_id=user.id,
        )
        db.session.add(batch)
        db.session.flush()

        item = ResolutionItem(
            batch_id=batch.id,
            status="awaiting_approval",
            product_label="Policy Product",
        )
        db.session.add(item)
        db.session.flush()

        immutable_change = ResolutionChange(
            item_id=item.id,
            field_group="ids",
            field_name="store_currency",
            before_value="USD",
            after_value="EUR",
            status="awaiting_approval",
        )
        threshold_change = ResolutionChange(
            item_id=item.id,
            field_group="pricing",
            field_name="price",
            before_value=100.0,
            after_value=130.0,
            status="awaiting_approval",
        )
        db.session.add_all([immutable_change, threshold_change])
        db.session.flush()

        action = ChatAction(
            session_id=session.id,
            user_id=user.id,
            store_id=store.id,
            action_type="update_product",
            status="awaiting_approval",
            payload_json={
                "dry_run_required": True,
                "dry_run_id": batch.id,
                "runtime": {"action_kind": "write"},
            },
        )
        db.session.add(action)
        db.session.commit()

        approved_action = approve_product_action(action=action, actor_user_id=user.id)
        db.session.refresh(immutable_change)
        db.session.refresh(threshold_change)
        immutable_status = immutable_change.status
        threshold_status = threshold_change.status

        policy_payload = approved_action.payload_json["approval"]["policy"]
        blocked_ids = {row["change_id"] for row in policy_payload["immutable_blocked"]}
        threshold_hit_ids = {row["change_id"] for row in policy_payload["threshold_hits"]}

    assert immutable_status == "blocked_exclusion"
    assert threshold_status == "approved"
    assert immutable_change.id in blocked_ids
    assert threshold_change.id in threshold_hit_ids
    assert policy_payload["requires_hitl"] is True
