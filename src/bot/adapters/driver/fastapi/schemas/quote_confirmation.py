from __future__ import annotations

from pydantic import BaseModel, Field


class ConfirmAndSendQuoteRequestSchema(BaseModel):
    selected_item_ids: list[str] = Field(
        ...,
        min_length=1,
        description="IDs dos itens selecionados na cotação",
    )
    note: str | None = Field(default=None, max_length=1000)


class ConfirmAndSendQuoteResponseSchema(BaseModel):
    ok: bool = True
    queued: bool = True
