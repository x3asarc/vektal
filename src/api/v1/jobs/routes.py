"""Jobs API routes."""

from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.api.core.errors import ProblemDetails
from src.api.v1.jobs import jobs_api_bp
from src.api.v1.jobs.schemas import (
    JobCancelResponse,
    JobCreateRequest,
    JobDetailResponse,
    JobListResponse,
    JobQuery,
    JobRetryResponse,
    JobResponse,
    JobResultResponse,
)
from src.celery_app import app as celery_app
from src.jobs.cancellation import request_cancellation
from src.jobs.progress import announce_job_progress, build_progress_payload
from src.models import Job, JobResult, JobStatus, JobType, db


def _job_to_response(job: Job) -> JobResponse:
    progress = build_progress_payload(job)
    return JobResponse(
        id=job.id,
        job_type=job.job_type.value if job.job_type else None,
        job_name=job.job_name,
        status=job.status.value,
        total_items=progress["total_items"],
        processed_items=progress["processed_items"],
        successful_items=progress["successful_items"],
        failed_items=progress["failed_items"],
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
        stream_url=f"/api/v1/jobs/{job.id}/stream",
        percent_complete=progress["percent_complete"],
        current_step=progress["current_step"],
        current_step_label=progress["current_step_label"],
        step_index=progress["step_index"],
        step_total=progress["step_total"],
        eta_seconds=progress["eta_seconds"],
        can_retry=progress["can_retry"],
        retry_url=progress["retry_url"],
        results_url=progress["results_url"],
    )

@jobs_api_bp.route("", methods=["GET"])
@login_required
def list_jobs():
    """
    List jobs for current user.

    Query params:
        status: Filter by status (pending, running, completed, failed, cancelled)
        job_type: Filter by job type
        limit: Max items to return (1-100, default 50)
    """
    try:
        query_params = JobQuery(**request.args.to_dict())
    except ValidationError as e:
        return ProblemDetails.validation_error(e)

    query = Job.query.filter_by(user_id=current_user.id)

    # Apply filters
    if query_params.status:
        try:
            status_enum = JobStatus(query_params.status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter

    if query_params.job_type:
        try:
            query = query.filter_by(job_type=JobType(query_params.job_type))
        except ValueError:
            pass

    jobs = query.order_by(Job.created_at.desc()).limit(query_params.limit).all()

    job_responses = [_job_to_response(job) for job in jobs]

    return JobListResponse(
        jobs=job_responses,
        total=len(job_responses)
    ).model_dump(), 200

@jobs_api_bp.route("", methods=["POST"])
@login_required
def create_job():
    """Create async ingest job and return immediately."""
    try:
        payload = JobCreateRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as e:
        return ProblemDetails.validation_error(e)

    store = getattr(current_user, "shopify_store", None)
    if not store:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before launching ingest jobs.",
            409,
        )

    store_id = payload.store_id or store.id
    if store_id != store.id:
        return ProblemDetails.business_error(
            "store-mismatch",
            "Invalid Store",
            "Current user can only launch jobs for their connected store.",
            403,
        )

    job = Job(
        user_id=current_user.id,
        store_id=store_id,
        job_type=JobType.INGEST_CATALOG,
        job_name=payload.job_name or "Catalog ingest",
        status=JobStatus.PENDING,
        total_products=0,
        processed_count=0,
        total_items=0,
        processed_items=0,
        parameters={"chunk_size": payload.chunk_size},
    )
    db.session.add(job)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return ProblemDetails.business_error(
            "active-ingest-exists",
            "Active Ingest Exists",
            "Only one active ingest job is allowed per store.",
            409,
        )

    task = celery_app.send_task(
        "src.tasks.ingest.start_ingest_task",
        kwargs={
            "job_id": job.id,
            "store_id": store_id,
            "user_id": current_user.id,
            "chunk_size": payload.chunk_size,
        },
        queue="control",
    )
    job.celery_task_id = task.id
    db.session.commit()
    announce_job_progress(job_id=job.id, job=job)

    return {
        "job_id": job.id,
        "status": job.status.value,
        "message": "Job accepted for background processing",
        "task_id": task.id,
        "stream_url": f"/api/v1/jobs/{job.id}/stream",
    }, 202


@jobs_api_bp.route("/<int:job_id>", methods=["GET"])
@login_required
def get_job(job_id: int):
    """Get job details with results."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return ProblemDetails.not_found("job", job_id)

    # Get results
    results = JobResult.query.filter_by(job_id=job_id).order_by(
        JobResult.created_at.desc()
    ).all()

    job_response = _job_to_response(job)

    result_responses = [
        JobResultResponse(
            id=r.id,
            item_sku=r.item_sku,
            item_barcode=r.item_barcode,
            item_identifier=r.item_identifier,
            status=r.status,
            error_message=r.error_message,
            result_data=r.result_data,
            created_at=r.created_at.isoformat() if r.created_at else None
        ) for r in results
    ]

    return JobDetailResponse(
        job=job_response,
        results=result_responses
    ).model_dump(), 200

@jobs_api_bp.route("/<int:job_id>/cancel", methods=["POST"])
@login_required
def cancel_job(job_id: int):
    """Cancel a running job."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return ProblemDetails.not_found("job", job_id)

    cancellable = {
        JobStatus.PENDING,
        JobStatus.QUEUED,
        JobStatus.RUNNING,
        JobStatus.CANCEL_REQUESTED,
    }
    if job.status not in cancellable:
        return ProblemDetails.business_error(
            "invalid-job-state",
            "Cannot Cancel Job",
            f"Job is {job.status.value}, can only cancel active jobs",
            409
        )

    result = request_cancellation(job_id=job.id, terminate=False)
    if result.get("status") not in {"cancel_requested", "already-requested"}:
        return ProblemDetails.business_error(
            "cancel-failed",
            "Cancel Request Failed",
            f"Could not request cancellation for job {job.id}.",
            500,
        )

    db.session.refresh(job)

    return JobCancelResponse(
        message="Cancellation requested",
        job_id=job.id,
        new_status=job.status.value
    ).model_dump(), 200


@jobs_api_bp.route("/<int:job_id>/retry", methods=["POST"])
@login_required
def retry_job(job_id: int):
    """Create a new ingest job by retrying a terminal failed/cancelled job."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return ProblemDetails.not_found("job", job_id)

    retryable = {
        JobStatus.FAILED,
        JobStatus.FAILED_TERMINAL,
        JobStatus.CANCELLED,
    }
    if job.status not in retryable:
        return ProblemDetails.business_error(
            "invalid-job-state",
            "Cannot Retry Job",
            f"Job is {job.status.value}, can only retry failed or cancelled jobs.",
            409,
        )

    chunk_size = 100
    if isinstance(job.parameters, dict):
        raw_chunk_size = job.parameters.get("chunk_size")
        if isinstance(raw_chunk_size, int) and 10 <= raw_chunk_size <= 1000:
            chunk_size = raw_chunk_size

    retry_job_row = Job(
        user_id=current_user.id,
        store_id=job.store_id,
        job_type=job.job_type or JobType.INGEST_CATALOG,
        job_name=f"{job.job_name or 'Catalog ingest'} (retry)",
        status=JobStatus.PENDING,
        total_products=0,
        processed_count=0,
        total_items=0,
        processed_items=0,
        parameters={
            "chunk_size": chunk_size,
            "retry_of_job_id": job.id,
        },
    )
    db.session.add(retry_job_row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return ProblemDetails.business_error(
            "active-ingest-exists",
            "Active Ingest Exists",
            "Only one active ingest job is allowed per store.",
            409,
        )

    task = celery_app.send_task(
        "src.tasks.ingest.start_ingest_task",
        kwargs={
            "job_id": retry_job_row.id,
            "store_id": retry_job_row.store_id,
            "user_id": current_user.id,
            "chunk_size": chunk_size,
        },
        queue="control",
    )
    retry_job_row.celery_task_id = task.id
    db.session.commit()
    announce_job_progress(job_id=retry_job_row.id, job=retry_job_row)

    return JobRetryResponse(
        message="Retry job accepted for background processing",
        job_id=retry_job_row.id,
        retry_of_job_id=job.id,
        status=retry_job_row.status.value,
        task_id=task.id,
        stream_url=f"/api/v1/jobs/{retry_job_row.id}/stream",
    ).model_dump(), 202
