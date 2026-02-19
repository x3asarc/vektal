"""Queue-backed enrichment apply execution."""
from __future__ import annotations

from datetime import datetime, timezone

from src.assistant.reliability.policy_store import (
    get_runtime_policy_snapshot,
    retry_limit_for_class,
)
from src.celery_app import app
from src.jobs.progress import announce_job_progress
from src.models import Job, JobStatus, ProductEnrichmentItem, ProductEnrichmentRun, db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_stale(run: ProductEnrichmentRun, *, now_utc: datetime | None = None) -> bool:
    if run.dry_run_expires_at is None:
        return False
    now_utc = now_utc or _now()
    expires_at = run.dry_run_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now_utc > expires_at


def resolve_enrichment_queue_tier(run_profile: str) -> str:
    """Map run profile to queue tier for bounded worker routing."""
    profile = (run_profile or "").strip().lower()
    if profile == "deep":
        return "tier_3"
    return "tier_2"


@app.task(
    name="src.tasks.enrichment.run_enrichment_batch",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def run_enrichment_batch(
    self,
    *,
    run_id: int,
    job_id: int,
    actor_user_id: int | None = None,
) -> dict:
    """
    Apply approved enrichment items with deterministic progress semantics.

    Phase 13.1 keeps this worker intentionally deterministic and side-effect
    bounded: item-level DB state is updated and surfaced to the workspace.
    """
    run = ProductEnrichmentRun.query.get(run_id)
    job = Job.query.get(job_id)
    if run is None or job is None:
        return {"status": "failed", "error": "run-or-job-not-found", "run_id": run_id, "job_id": job_id}

    policy = get_runtime_policy_snapshot(provider_name="shopify", skill_name="enrichment.apply")
    max_server_retries = retry_limit_for_class(policy, "server_error", default=1)

    if _is_stale(run) and run.status != "applied":
        run.status = "expired"
        metadata = dict(run.metadata_json or {})
        metadata["oracle_decision"] = "expired_before_apply"
        run.metadata_json = metadata
        job.status = JobStatus.FAILED_TERMINAL
        job.error_message = "Dry-run expired before apply execution."
        job.completed_at = _now()
        db.session.commit()
        announce_job_progress(job.id, job=job)
        return {"status": "failed_terminal", "reason": "stale_dry_run", "run_id": run_id, "job_id": job_id}

    approved_items = (
        ProductEnrichmentItem.query.filter_by(run_id=run.id, decision_state="approved")
        .order_by(ProductEnrichmentItem.id.asc())
        .all()
    )
    total_items = len(approved_items)
    job.total_products = total_items
    job.total_items = total_items
    job.processed_count = 0
    job.processed_items = 0
    job.successful_items = 0
    job.failed_items = 0
    job.status = JobStatus.RUNNING
    job.started_at = job.started_at or _now()
    params = dict(job.parameters or {})
    params["current_step"] = "applying_updates"
    params["policy_version"] = policy.policy_version
    params["retry_policy"] = policy.retry_policy
    params["retry_budget_server_error"] = max_server_retries
    params["oracle_decision"] = "execution_running"
    params["run_tier"] = resolve_enrichment_queue_tier(run.run_profile)
    job.parameters = params
    db.session.commit()
    announce_job_progress(job.id, job=job)

    try:
        for index, item in enumerate(approved_items, start=1):
            item.decision_state = "applied"
            item.metadata_json = {
                **(item.metadata_json or {}),
                "applied_at": _now().isoformat(),
                "applied_by_user_id": actor_user_id,
                "job_id": job.id,
                "run_id": run.id,
                "policy_version": policy.policy_version,
            }
            job.processed_count = index
            job.processed_items = index
            job.successful_items = index
            if index == total_items or index % 20 == 0:
                db.session.commit()
                announce_job_progress(job.id, job=job)

        run.status = "applied"
        metadata = dict(run.metadata_json or {})
        metadata["oracle_decision"] = "execution_applied"
        metadata["applied_items"] = total_items
        metadata["applied_at"] = _now().isoformat()
        metadata["policy_version"] = policy.policy_version
        run.metadata_json = metadata

        # Emit enrichment outcome episode (Phase 13.2)
        try:
            from src.tasks.graphiti_sync import emit_episode
            from src.core.synthex_entities import EpisodeType

            outcome_payload = {
                'product_count': total_items,
                'profile_gear': run.profile_gear or 'balanced',
                'fields_modified': ['seo_title', 'seo_description'],  # Summary
                'quality_delta': 0.0,  # TODO: Calculate from enrichment metrics
                'oracle_arbitration_used': False,
            }
            emit_episode.delay(
                EpisodeType.ENRICHMENT_OUTCOME.value,
                str(run.store_id),
                outcome_payload,
                correlation_id=f"enrichment-run-{run.id}"
            )
        except Exception:
            pass  # Fail-open: do not break enrichment flow if graph emission fails

        job.status = JobStatus.COMPLETED
        job.completed_at = _now()
        params = dict(job.parameters or {})
        params["current_step"] = "completed"
        job.parameters = params
        db.session.commit()
        announce_job_progress(job.id, job=job)
        return {
            "status": "completed",
            "run_id": run.id,
            "job_id": job.id,
            "processed_items": total_items,
            "policy_version": policy.policy_version,
            "breaker_state": policy.breaker_state,
        }
    except Exception as exc:  # pragma: no cover - runtime safety path
        should_retry = self.request.retries < max_server_retries
        if should_retry:
            raise self.retry(exc=exc)
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
        job.completed_at = _now()
        params = dict(job.parameters or {})
        params["current_step"] = "failed"
        params["oracle_decision"] = "execution_failed"
        job.parameters = params
        db.session.commit()
        announce_job_progress(job.id, job=job)
        return {"status": "failed", "run_id": run.id, "job_id": job.id, "error": str(exc)}
