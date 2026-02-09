"""Jobs API routes."""
from flask import request, url_for
from flask_login import login_required, current_user
from pydantic import ValidationError

from src.api.v1.jobs import jobs_api_bp
from src.api.v1.jobs.schemas import (
    JobQuery, JobResponse, JobDetailResponse,
    JobListResponse, JobResultResponse, JobCancelResponse
)
from src.api.core.errors import ProblemDetails
from src.models import Job, JobResult, JobStatus, db
from datetime import datetime, timezone

@jobs_api_bp.route('', methods=['GET'])
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
        query = query.filter_by(job_type=query_params.job_type)

    jobs = query.order_by(Job.created_at.desc()).limit(query_params.limit).all()

    job_responses = []
    for job in jobs:
        job_data = JobResponse(
            id=job.id,
            job_type=job.job_type.value if job.job_type else None,
            job_name=job.job_name,
            status=job.status.value,
            total_items=job.total_items or 0,
            processed_items=job.processed_items or 0,
            successful_items=job.successful_items or 0,
            failed_items=job.failed_items or 0,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_message=job.error_message,
            stream_url=f"/api/v1/jobs/{job.id}/stream"
        )
        job_responses.append(job_data)

    return JobListResponse(
        jobs=job_responses,
        total=len(job_responses)
    ).model_dump(), 200

@jobs_api_bp.route('/<int:job_id>', methods=['GET'])
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

    job_response = JobResponse(
        id=job.id,
        job_type=job.job_type.value if job.job_type else None,
        job_name=job.job_name,
        status=job.status.value,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
        successful_items=job.successful_items or 0,
        failed_items=job.failed_items or 0,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
        stream_url=f"/api/v1/jobs/{job.id}/stream"
    )

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

@jobs_api_bp.route('/<int:job_id>/cancel', methods=['POST'])
@login_required
def cancel_job(job_id: int):
    """Cancel a running job."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return ProblemDetails.not_found("job", job_id)

    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        return ProblemDetails.business_error(
            "invalid-job-state",
            "Cannot Cancel Job",
            f"Job is {job.status.value}, can only cancel pending or running jobs",
            409
        )

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    return JobCancelResponse(
        message="Job cancelled successfully",
        job_id=job.id,
        new_status=job.status.value
    ).model_dump(), 200
