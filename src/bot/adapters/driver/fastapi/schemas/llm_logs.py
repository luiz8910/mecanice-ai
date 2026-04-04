"""Schemas for LLM call observability endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LlmLogMessageSchema(BaseModel):
    id: UUID
    log_id: UUID
    position: int
    role: str
    content: str
    created_at: datetime


class LlmLogSummarySchema(BaseModel):
    id: UUID
    requester_id: str | None = None
    thread_id: str | None = None
    request_id: str | None = None
    provider: str
    endpoint: str
    model: str
    status: str
    http_status: int | None = None
    duration_ms: int | None = None
    response_candidate_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class LlmLogDetailSchema(LlmLogSummarySchema):
    vehicle_json: dict[str, Any] = Field(default_factory=dict)
    context_json: dict[str, Any] = Field(default_factory=dict)
    request_payload_json: dict[str, Any] = Field(default_factory=dict)
    parsed_response_json: dict[str, Any] | None = None
    raw_response_text: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    messages: list[LlmLogMessageSchema] = Field(default_factory=list)
