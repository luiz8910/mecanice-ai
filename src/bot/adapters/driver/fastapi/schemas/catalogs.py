"""Pydantic schemas for catalog documents and RAG queries."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CatalogDocumentResponse(BaseModel):
    id: int
    manufacturer_id: int | None
    original_filename: str
    file_size_bytes: int | None
    description: str | None
    brand: str | None
    status: str
    page_count: int | None
    chunk_count: int | None
    error_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    manufacturer_id: int | None = None
    catalog_id: int | None = None
    brand: str | None = None
    top_k: int = Field(default=6, ge=1, le=20)


class RagQuerySource(BaseModel):
    catalog_id: int | None
    filename: str | None
    page: int | None
    chunk_text: str
    similarity: float


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagQuerySource]
