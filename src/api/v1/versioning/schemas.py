"""
Pydantic schemas for version-management endpoints.

Provides request/response models for:
- API version status queries
- v2 migration requests
- v1 rollback requests
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ApiVersionStatusResponse(BaseModel):
    """
    Response model for GET /api/v1/user/version.

    Shows user's current API version, available versions, and rollback status.
    """
    current_version: str = Field(
        ...,
        description="User's current API version",
        examples=["v1", "v2"]
    )
    available_versions: List[str] = Field(
        ...,
        description="List of available API versions user can migrate to",
        examples=[["v1", "v2"]]
    )
    lock_until: Optional[datetime] = Field(
        None,
        description="ISO 8601 timestamp when rollback window expires (null if no lock)"
    )
    rollback_available: bool = Field(
        ...,
        description="Whether user can rollback to previous version"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_version": "v2",
                "available_versions": ["v1", "v2"],
                "lock_until": "2026-02-10T20:30:00Z",
                "rollback_available": True
            }
        }


class MigrateToV2Response(BaseModel):
    """
    Response model for POST /api/v1/user/migrate-to-v2.

    Shows migration results and rollback window information.
    """
    previous_version: str = Field(
        ...,
        description="API version before migration",
        examples=["v1"]
    )
    new_version: str = Field(
        ...,
        description="API version after migration",
        examples=["v2"]
    )
    migration_steps: List[str] = Field(
        ...,
        description="List of migration steps executed"
    )
    rollback_available_until: Optional[datetime] = Field(
        None,
        description="ISO 8601 timestamp when rollback window expires"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "previous_version": "v1",
                "new_version": "v2",
                "migration_steps": [
                    "Validated user eligibility",
                    "Prepared for v2 migration",
                    "Migration ready (no data transformations required in Phase 5)",
                    "User can safely use v2 API endpoints"
                ],
                "rollback_available_until": "2026-02-10T20:30:00Z"
            }
        }


class RollbackToV1Response(BaseModel):
    """
    Response model for POST /api/v1/user/rollback-to-v1.

    Shows rollback results.
    """
    previous_version: str = Field(
        ...,
        description="API version before rollback",
        examples=["v2"]
    )
    new_version: str = Field(
        ...,
        description="API version after rollback",
        examples=["v1"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "previous_version": "v2",
                "new_version": "v1"
            }
        }


__all__ = [
    'ApiVersionStatusResponse',
    'MigrateToV2Response',
    'RollbackToV1Response'
]
