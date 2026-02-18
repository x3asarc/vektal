"""Pydantic schemas for Jobs API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

class JobQuery(BaseModel):
    """Query parameters for job list."""
    status: Optional[str] = Field(default=None, description="Filter by status")
    job_type: Optional[str] = Field(default=None, description="Filter by job type")
    limit: int = Field(default=50, ge=1, le=100)

class JobResultResponse(BaseModel):
    """Single job result."""
    id: int
    item_sku: Optional[str] = None
    item_barcode: Optional[str] = None
    item_identifier: Optional[str] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    result_data: Optional[dict] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    """Single job response."""
    id: int
    job_type: Optional[str] = None
    job_name: Optional[str] = None
    status: str
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    stream_url: Optional[str] = None  # SSE endpoint
    percent_complete: float = 0.0
    current_step: str = "queued"
    current_step_label: str = "Queued"
    step_index: int = 1
    step_total: int = 6
    eta_seconds: Optional[int] = None
    can_retry: bool = False
    retry_url: Optional[str] = None
    results_url: Optional[str] = None

    class Config:
        from_attributes = True

class JobDetailResponse(BaseModel):
    """Job with results."""
    job: JobResponse
    results: List[JobResultResponse]

class JobListResponse(BaseModel):
    """Job list response."""
    jobs: List[JobResponse]
    total: int

class JobCreateRequest(BaseModel):
    """Request to create a background ingest job."""
    store_id: Optional[int] = Field(default=None, description="Optional store id override")
    job_name: Optional[str] = Field(default=None, max_length=255)
    chunk_size: int = Field(default=100, ge=10, le=1000)

class JobCancelResponse(BaseModel):
    """Response after cancelling a job."""
    message: str
    job_id: int
    new_status: str


class JobRetryResponse(BaseModel):
    """Response after creating a retry job."""
    message: str
    job_id: int
    retry_of_job_id: int
    status: str
    task_id: Optional[str] = None
    stream_url: Optional[str] = None
