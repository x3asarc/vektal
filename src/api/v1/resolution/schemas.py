"""Pydantic schemas for resolution rules, locks, and dry-run endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResolutionRuleRequest(BaseModel):
    supplier_code: str = Field(default="*", max_length=64)
    field_group: str = Field(pattern="^(images|text|pricing|ids)$")
    rule_type: str = Field(pattern="^(auto_apply|exclude|variant_create|quiz_default)$")
    action: str = Field(default="require_approval", max_length=64)
    consented: bool = False
    enabled: bool = True
    expires_at: Optional[datetime] = None
    config: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class ResolutionRulePatch(BaseModel):
    action: Optional[str] = Field(default=None, max_length=64)
    consented: Optional[bool] = None
    enabled: Optional[bool] = None
    expires_at: Optional[datetime] = None
    config: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class ResolutionRuleResponse(BaseModel):
    id: int
    supplier_code: str
    field_group: str
    rule_type: str
    action: str
    consented: bool
    enabled: bool
    expires_at: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResolutionRuleListResponse(BaseModel):
    rules: list[ResolutionRuleResponse]
    total: int


class LockResponse(BaseModel):
    batch_id: int
    locked: bool
    lock_owner_user_id: Optional[int] = None
    lock_expires_at: Optional[str] = None
    lock_heartbeat_at: Optional[str] = None
    granted: Optional[bool] = None


class DryRunInputRow(BaseModel):
    sku: Optional[str] = None
    barcode: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    product_type: Optional[str] = None
    variant_options: list[str] = Field(default_factory=list)


class DryRunCreateRequest(BaseModel):
    supplier_code: str = Field(min_length=1, max_length=64)
    supplier_verified: bool = False
    apply_mode: str = Field(default="immediate", pattern="^(immediate|scheduled)$")
    scheduled_for: Optional[datetime] = None
    rows: list[DryRunInputRow] = Field(min_length=1)


class DryRunCreateResponse(BaseModel):
    batch_id: int
    status: str
    apply_mode: str
    supplier_code: str
    counts: dict[str, Any]


class DryRunFieldChangeResponse(BaseModel):
    change_id: int
    field_group: str
    field_name: str
    before_value: Any = None
    after_value: Any = None
    status: str
    reason_sentence: Optional[str] = None
    reason_factors: dict[str, Any] = Field(default_factory=dict)
    confidence_score: Optional[float] = None
    confidence_badge: Optional[str] = None
    applied_rule_id: Optional[int] = None
    blocked_by_rule_id: Optional[int] = None


class DryRunProductGroupResponse(BaseModel):
    item_id: int
    product_label: Optional[str] = None
    status: str
    structural_state: Optional[str] = None
    conflict_reason: Optional[str] = None
    source_used: Optional[str] = None
    changes: list[DryRunFieldChangeResponse] = Field(default_factory=list)


class DryRunBatchResponse(BaseModel):
    batch_id: int
    status: str
    apply_mode: str
    scheduled_for: Optional[str] = None
    read_only: bool = False
    lock_owner_user_id: Optional[int] = None
    groups: list[DryRunProductGroupResponse] = Field(default_factory=list)


class DryRunLineageResponse(BaseModel):
    batch_id: int
    entries: list[dict[str, Any]] = Field(default_factory=list)
