"""Phase 13-01 idempotency terminal state contract tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.assistant.reliability.idempotency import (
    claim_execution_slot,
    mark_execution_failed,
    mark_execution_success,
    reset_failed_execution,
)
from src.models import AssistantExecutionLedger, db
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
def seeded_context(app):
    with app.app_context():
        user = User(
            email="idempotency-contract@example.com",
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
            shop_domain="idempotency-contract.myshopify.com",
            shop_name="Idempotency Contract",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.commit()
        return {"user_id": user.id, "store_id": store.id}


def test_processing_and_success_replay_paths(app, seeded_context):
    user_id = seeded_context["user_id"]
    store_id = seeded_context["store_id"]
    payload = {"sku": "SKU-100", "price": "9.99"}
    with app.app_context():
        claim_1 = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:100",
            payload=payload,
            status_url="/api/v1/chat/sessions/1/actions/100",
            correlation_id="corr-1",
        )
        assert claim_1.state == "created"
        assert claim_1.http_status == 202

        claim_2 = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:100",
            payload=payload,
            status_url="/api/v1/chat/sessions/1/actions/100",
            correlation_id="corr-1",
        )
        assert claim_2.state == "processing_replay"
        assert claim_2.http_status == 202

        mark_execution_success(
            idempotency_key=claim_1.idempotency_key,
            response_json={"status": "completed", "applied": 1},
        )
        claim_3 = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:100",
            payload=payload,
        )
        assert claim_3.state == "success_replay"
        assert claim_3.http_status == 200
        assert claim_3.response_json["status"] == "completed"


def test_failed_path_allows_single_reset_retry(app, seeded_context):
    user_id = seeded_context["user_id"]
    store_id = seeded_context["store_id"]
    payload = {"sku": "SKU-200", "price": "19.99"}
    with app.app_context():
        claim = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:200",
            payload=payload,
            status_url="/api/v1/chat/sessions/1/actions/200",
        )
        mark_execution_failed(
            idempotency_key=claim.idempotency_key,
            error_message="shopify-timeout",
            error_class="timeout",
        )

        failed = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:200",
            payload=payload,
        )
        assert failed.state == "failed"
        assert failed.http_status == 422
        assert failed.retry_allowed is True

        reset = reset_failed_execution(idempotency_key=claim.idempotency_key, correlation_id="corr-reset")
        assert reset is not None
        assert reset.status == "PROCESSING"
        assert reset.attempt_count == 2

        mark_execution_failed(
            idempotency_key=claim.idempotency_key,
            error_message="shopify-timeout-repeat",
            error_class="timeout",
        )
        failed_again = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:200",
            payload=payload,
        )
        assert failed_again.state == "failed"
        assert failed_again.retry_allowed is False


def test_expired_entry_is_purged_and_recreated(app, seeded_context):
    user_id = seeded_context["user_id"]
    store_id = seeded_context["store_id"]
    payload = {"sku": "SKU-300", "price": "29.99"}
    with app.app_context():
        claim = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:300",
            payload=payload,
        )

        ledger = AssistantExecutionLedger.query.filter_by(idempotency_key=claim.idempotency_key).first()
        assert ledger is not None
        ledger.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

        recreated = claim_execution_slot(
            store_id=store_id,
            user_id=user_id,
            action_type="chat.apply",
            resource_id="action:300",
            payload=payload,
        )
        assert recreated.state == "created"
        latest = AssistantExecutionLedger.query.filter_by(idempotency_key=claim.idempotency_key).first()
        assert latest is not None
        assert latest.status == "PROCESSING"
        assert latest.attempt_count == 2
