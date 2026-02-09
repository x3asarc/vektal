"""
Pydantic schemas for Jobs API.

These schemas define request/response formats and enable automatic
OpenAPI documentation generation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class JobProgressEvent(BaseModel):
    """Real-time job progress update sent via SSE."""
    job_id: int
    status: str = Field(description="Job status: pending, running, completed, failed, cancelled")
    processed_items: int = Field(default=0)
    total_items: int = Field(default=0)
    successful_items: int = Field(default=0)
    failed_items: int = Field(default=0)
    current_item: Optional[str] = Field(default=None, description="SKU currently being processed")
    message: Optional[str] = Field(default=None, description="Status message")
    percent_complete: float = Field(default=0.0)

    @classmethod
    def from_job(cls, job) -> "JobProgressEvent":
        """Create progress event from Job model."""
        percent = 0.0
        if job.total_items > 0:
            percent = (job.processed_items / job.total_items) * 100

        return cls(
            job_id=job.id,
            status=job.status.value if hasattr(job.status, 'value') else str(job.status),
            processed_items=job.processed_items or 0,
            total_items=job.total_items or 0,
            successful_items=job.successful_items or 0,
            failed_items=job.failed_items or 0,
            percent_complete=round(percent, 1)
        )


class JobStatusResponse(BaseModel):
    """Polling fallback response for job status."""
    job_id: int
    status: str
    processed_items: int
    total_items: int
    successful_items: int
    failed_items: int
    percent_complete: float
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class JobStreamInfo(BaseModel):
    """Information about SSE stream endpoint."""
    stream_url: str = Field(description="SSE endpoint URL for real-time updates")
    fallback_url: str = Field(description="Polling endpoint URL for fallback")
    retry_interval: int = Field(default=2000, description="Recommended polling interval (ms)")
