"""Pydantic schemas for WhatsApp Cloud API webhooks.

This is a minimal, permissive schema meant to keep the webhook endpoint
stable while the exact payload fields are iterated.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WhatsAppWebhookPayload(BaseModel):
	"""A permissive model for WhatsApp webhook payloads."""

	object: str | None = None
	entry: list[dict[str, Any]] = Field(default_factory=list)

