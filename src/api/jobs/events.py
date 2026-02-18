"""
Job progress streaming endpoints.

Provides:
- SSE endpoint for real-time job progress updates
- Polling fallback endpoint for environments blocking SSE
"""
from flask import Response
from flask_login import login_required, current_user

from src.api.jobs import jobs_bp
from src.api.core.sse import job_announcer, format_sse
from src.api.jobs.schemas import JobProgressEvent, JobStatusResponse
from src.jobs.progress import announce_job_progress, build_progress_payload
from src.models import Job


@jobs_bp.route('/<int:job_id>/stream')
@login_required
def stream_job_progress(job_id: int):
    """
    Stream real-time job progress via Server-Sent Events.

    Client usage:
        const eventSource = new EventSource('/api/v1/jobs/123/stream');
        eventSource.addEventListener('job_123', (e) => {
            const progress = JSON.parse(e.data);
            console.log(`Progress: ${progress.processed_items}/${progress.total_items}`);
        });

    Returns:
        SSE stream with job progress events
    """
    # Verify user owns this job
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return {"error": "Job not found"}, 404

    def generate():
        """Generator that yields SSE messages."""
        messages = job_announcer.listen()

        # Send initial state immediately
        initial_event = JobProgressEvent.from_job(job)
        yield format_sse(
            data=initial_event.model_dump_json(),
            event=f"job_{job_id}"
        )

        try:
            while True:
                # Block until message available
                msg = messages.get()
                yield msg
        except GeneratorExit:
            # Client disconnected
            job_announcer.remove_listener(messages)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Disable Nginx buffering
        }
    )


@jobs_bp.route('/<int:job_id>/status')
@login_required
def get_job_status(job_id: int):
    """
    Get current job status (polling fallback for SSE).

    Use this endpoint if SSE is blocked by corporate firewalls or
    client doesn't support EventSource.

    Recommended polling interval: 2 seconds

    Returns:
        JobStatusResponse with current job state
    """
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not job:
        return {"error": "Job not found"}, 404

    progress_payload = build_progress_payload(job)

    response = JobStatusResponse(
        job_id=job.id,
        status=job.status.value if hasattr(job.status, 'value') else str(job.status),
        processed_items=progress_payload["processed_items"],
        total_items=progress_payload["total_items"],
        successful_items=progress_payload["successful_items"],
        failed_items=progress_payload["failed_items"],
        percent_complete=progress_payload["percent_complete"],
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
        current_step=progress_payload["current_step"],
        current_step_label=progress_payload["current_step_label"],
        step_index=progress_payload["step_index"],
        step_total=progress_payload["step_total"],
        eta_seconds=progress_payload["eta_seconds"],
        can_retry=progress_payload["can_retry"],
        retry_url=progress_payload["retry_url"],
        results_url=progress_payload["results_url"],
    )

    return response.model_dump(), 200


def broadcast_job_progress(job_id: int, job=None):
    """
    Broadcast job progress to all SSE listeners.

    Call this from background job processor to update clients.

    Args:
        job_id: Job ID
        job: Optional Job instance (fetched if not provided)
    """
    if job is None:
        job = Job.query.get(job_id)

    if job:
        announce_job_progress(job_id=job_id, job=job)


__all__ = ['stream_job_progress', 'get_job_status', 'broadcast_job_progress']
