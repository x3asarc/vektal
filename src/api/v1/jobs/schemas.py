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
    """Request to create a job (via CSV upload)."""
    # Note: Actual job creation uses file upload, not JSON
    # This schema is for documentation purposes
    pass

class JobCancelResponse(BaseModel):
    """Response after cancelling a job."""
    message: str
    job_id: int
    new_status: str
