"""Wire (HTTP) schemas for workshops CRUD."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class WorkshopBaseSchema(BaseModel):
	name: Optional[str] = None
	whatsapp_phone_e164: Optional[str] = Field(
		None, description="WhatsApp phone in E.164 (eg +5511999999999)"
	)
	city: Optional[str] = None
	state_uf: Optional[str] = None
	status: Optional[str] = Field(None, description="active | blocked")
	address: Optional[str] = None
	email: Optional[str] = None
	notes: Optional[str] = None

	@field_validator("whatsapp_phone_e164")
	@classmethod
	def validate_e164(cls, v: str | None) -> str | None:
		if v is None:
			return v
		v = v.strip()
		digits = re.sub(r"\D", "", v)
		if not digits:
			raise ValueError("whatsapp_phone_e164 must contain digits")
		if not (10 <= len(digits) <= 15):
			raise ValueError("whatsapp_phone_e164 must be 10..15 digits")
		return "+" + digits

	@field_validator("state_uf")
	@classmethod
	def normalize_state(cls, v: str | None) -> str | None:
		if v is None:
			return v
		v = v.strip().upper()
		if len(v) != 2:
			raise ValueError("state_uf must be a 2-letter UF")
		return v

	@field_validator("status")
	@classmethod
	def validate_status(cls, v: str | None) -> str | None:
		if v is None:
			return v
		v = v.strip().lower()
		if v not in {"active", "blocked"}:
			raise ValueError("status must be 'active' or 'blocked'")
		return v


class WorkshopCreateSchema(WorkshopBaseSchema):
	name: str
	whatsapp_phone_e164: str
	city: str
	state_uf: str
	status: str


class WorkshopUpdateSchema(WorkshopBaseSchema):
	"""Partial update schema (PATCH)."""

	pass


class WorkshopResponseSchema(BaseModel):
	id: int
	name: str
	whatsapp_phone_e164: str
	city: str
	state_uf: str
	status: str
	address: Optional[str] = None
	email: Optional[str] = None
	notes: Optional[str] = None
	created_at: Optional[datetime] = None
	updated_at: Optional[datetime] = None
