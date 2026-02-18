"""Pydantic schemas for chat API contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


BlockType = Literal["text", "table", "diff", "action", "progress", "alert"]


class ChatBlock(BaseModel):
    """Deterministic block contract for frontend chat rendering."""

    type: BlockType
    text: Optional[str] = None
    title: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    store_id: Optional[int] = None


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    store_id: Optional[int] = None
    title: Optional[str] = None
    state: Literal["at_door", "in_house"]
    status: Literal["active", "closed"]
    summary: Optional[str] = None
    last_message_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]
    total: int


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    correlation_id: Optional[str] = Field(default=None, max_length=96)
    action_hints: Optional[dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    blocks: list[ChatBlock] = Field(default_factory=list)
    source_metadata: Optional[dict[str, Any]] = None
    intent_type: Optional[str] = None
    classification_method: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatMessageListResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int


class ChatActionResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    store_id: Optional[int] = None
    message_id: Optional[int] = None
    action_type: str
    status: str
    idempotency_key: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    approved_at: Optional[str] = None
    applied_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChatMessageCreateResponse(BaseModel):
    session: ChatSessionResponse
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    action: Optional[ChatActionResponse] = None


class ChatStreamEnvelope(BaseModel):
    session_id: int
    event: str
    emitted_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatRouteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    store_id: Optional[int] = None
    session_id: Optional[int] = None
    correlation_id: Optional[str] = Field(default=None, max_length=96)
    provider_failure_stage: Optional[str] = Field(default=None, max_length=64)
    provider_budget_percent: Optional[float] = Field(default=None, ge=0, le=100)
    rbac_role: str = Field(default="member", max_length=64)
    active_integrations: Optional[dict[str, bool]] = None


class EffectiveTool(BaseModel):
    tool_id: str
    risk_class: str
    mutates_data: bool
    requires_integration: Optional[str] = None
    required_role: Optional[str] = None


class ChatRouteResponse(BaseModel):
    route_decision: Literal["tier_1", "tier_2", "tier_3", "blocked"]
    correlation_id: Optional[str] = None
    confidence: float
    intent_type: str
    classifier_method: str
    approval_mode: str
    fallback_stage: Optional[str] = None
    suggested_escalation: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    effective_toolset: list[EffectiveTool] = Field(default_factory=list)
    explainability_payload: dict[str, Any] = Field(default_factory=dict)
    runtime_payload: dict[str, Any] = Field(default_factory=dict)
    provider_route: dict[str, Any] = Field(default_factory=dict)
    route_event_id: Optional[int] = None
    policy_snapshot_hash: Optional[str] = None
    effective_toolset_hash: Optional[str] = None


class ChatToolsResolveRequest(BaseModel):
    store_id: Optional[int] = None
    rbac_role: str = Field(default="member", max_length=64)
    active_integrations: Optional[dict[str, bool]] = None


class ChatToolsResolveResponse(BaseModel):
    effective_toolset: list[EffectiveTool] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ChatMemoryRetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    scope: Literal["team", "user"] = "team"
    store_id: Optional[int] = None


class ChatMemoryFactResponse(BaseModel):
    fact_id: int
    fact_key: str
    fact_value_text: str
    source: str
    trust_score: float
    relevance_score: float
    provenance: dict[str, Any] = Field(default_factory=dict)
    expires_at: Optional[str] = None


class ChatMemoryRetrieveResponse(BaseModel):
    items: list[ChatMemoryFactResponse] = Field(default_factory=list)
    total: int


class ChatDelegateRequest(BaseModel):
    parent_request_id: Optional[str] = Field(default=None, max_length=64)
    requested_tools: list[str] = Field(default_factory=list)
    depth: int = Field(default=1, ge=1, le=10)
    fan_out: int = Field(default=1, ge=1, le=20)
    budget: Optional[dict[str, Any]] = None


class ChatDelegateResponse(BaseModel):
    delegation_event_id: int
    status: str
    worker_tool_scope: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    task_id: Optional[str] = None
    queue: Optional[str] = None
    reason: Optional[str] = None


class ProductActionFieldOverride(BaseModel):
    change_id: int
    after_value: Any


class ProductActionApprovalRequest(BaseModel):
    selected_change_ids: list[int] = Field(default_factory=list)
    overrides: list[ProductActionFieldOverride] = Field(default_factory=list)
    comment: Optional[str] = None


class ProductActionApplyRequest(BaseModel):
    mode: Optional[Literal["immediate", "scheduled"]] = None


class ChatBulkActionRequest(BaseModel):
    content: str = Field(default="Bulk product operation", min_length=1, max_length=4000)
    skus: list[str] = Field(min_length=1)
    operation: Literal["add_product", "update_product"] = "update_product"
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    action_hints: Optional[dict[str, Any]] = None
    requested_chunk_size: Optional[int] = Field(default=None, ge=1, le=250)
    admin_concurrency_cap: Optional[int] = Field(default=None, ge=1, le=10)
    mode: Optional[Literal["immediate", "scheduled"]] = None
