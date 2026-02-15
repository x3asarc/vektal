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
