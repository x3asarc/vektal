"""
Pydantic schemas for Jobs API.

These schemas define request/response formats and enable automatic
OpenAPI documentation generation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

from src.jobs.progress import build_progress_payload


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
    current_step: str = Field(default="queued")
    current_step_label: str = Field(default="Queued")
    step_index: int = Field(default=1)
    step_total: int = Field(default=6)
    eta_seconds: Optional[int] = Field(default=None)
    can_retry: bool = Field(default=False)
    retry_url: Optional[str] = Field(default=None)
    results_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)

    @classmethod
    def from_job(cls, job) -> "JobProgressEvent":
        """Create progress event from Job model."""
        payload = build_progress_payload(job)
        return cls(**payload)


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
    current_step: str = "queued"
    current_step_label: str = "Queued"
    step_index: int = 1
    step_total: int = 6
    eta_seconds: Optional[int] = None
    can_retry: bool = False
    retry_url: Optional[str] = None
    results_url: Optional[str] = None


class JobStreamInfo(BaseModel):
    """Information about SSE stream endpoint."""
    stream_url: str = Field(description="SSE endpoint URL for real-time updates")
    fallback_url: str = Field(description="Polling endpoint URL for fallback")
    retry_interval: int = Field(default=2000, description="Recommended polling interval (ms)")
