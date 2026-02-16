"""Phase 13.1-03 queue-backed enrichment execution contracts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.app import create_openapi_app
from src.jobs.queueing import TASK_ROUTES
from src.models import (
    AccountStatus,
    Job,
    JobStatus,
    JobType,
    ProductEnrichmentItem,
    ProductEnrichmentRun,
    ShopifyStore,
    User,
    UserTier,
    db,
)
from src.tasks.enrichment import resolve_enrichment_queue_tier, run_enrichment_batch
from tests.api.conftest import TestConfig


@pytest.fixture
def app():
    app = create_openapi_app(config_object=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_enrichment_task_route_targets_batch_queue():
    assert TASK_ROUTES["src.tasks.enrichment.run_enrichment_batch"]["queue"] == "batch.t2"


def test_enrichment_profile_routes_deep_to_tier3():
    assert resolve_enrichment_queue_tier("quick") == "tier_2"
    assert resolve_enrichment_queue_tier("standard") == "tier_2"
    assert resolve_enrichment_queue_tier("deep") == "tier_3"


def test_enrichment_batch_task_marks_approved_items_applied(app):
    with app.app_context():
        user = User(
            email="enrichment-worker@example.com",
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
            shop_domain="enrichment-worker.myshopify.com",
            shop_name="Enrichment Worker",
            access_token_encrypted=b"token",
            is_active=True,
        )
        db.session.add(store)
        db.session.flush()

        run = ProductEnrichmentRun(
            user_id=user.id,
            store_id=store.id,
            vendor_code="PENTART",
            run_profile="standard",
            target_language="de",
            status="approved",
            policy_version=1,
            mapping_version=1,
            idempotency_hash="abc123",
            dry_run_expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            alt_text_policy="preserve",
            protected_columns_json=[],
            capability_audit_json={},
            metadata_json={},
        )
        db.session.add(run)
        db.session.flush()

        item = ProductEnrichmentItem(
            run_id=run.id,
            product_id=None,
            field_group="text",
            field_name="title",
            decision_state="approved",
            before_value="old",
            after_value="new",
            confidence=0.91,
            provenance={"source": "ai_inferred"},
            reason_codes=["allowed"],
            evidence_refs=[],
            requires_user_action=True,
            is_protected_column=False,
            alt_text_preserved=True,
            policy_version=1,
            mapping_version=1,
            metadata_json={},
        )
        db.session.add(item)

        job = Job(
            user_id=user.id,
            store_id=store.id,
            job_type=JobType.PRODUCT_ENRICH,
            job_name="Enrichment apply",
            status=JobStatus.PENDING,
            total_products=1,
            processed_count=0,
            total_items=1,
            processed_items=0,
            parameters={"current_step": "queued"},
        )
        db.session.add(job)
        db.session.commit()

        result = run_enrichment_batch(run_id=run.id, job_id=job.id, actor_user_id=user.id)
        db.session.refresh(job)
        db.session.refresh(item)

        assert result["status"] == "completed"
        assert item.decision_state == "applied"
        assert job.status == JobStatus.COMPLETED
        assert job.processed_items == 1
        assert job.successful_items == 1
        assert isinstance(job.parameters, dict)
        assert job.parameters.get("current_step") == "completed"
