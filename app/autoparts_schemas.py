"""Pydantic schemas for the AutoParts admin API (compat).

Kept intentionally small — just enough to satisfy current unit tests.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _dedupe_normalize(values: List[str] | None) -> List[str]:
    if not values:
        return []
    result: List[str] = []
    seen = set()
    for v in values:
        if v is None:
            continue
        norm = str(v).strip().lower()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        result.append(norm)
    return result


class AutoPartBase(BaseModel):
    name: Optional[str] = None
    whatsapp_phone_e164: Optional[str] = None
    city: Optional[str] = None
    state_uf: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    delivery_types: List[str] = Field(default_factory=list)
    radius_km: Optional[float] = None
    categories: List[str] = Field(default_factory=list)
    responsible_name: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("whatsapp_phone_e164")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        # Very small E.164 check: must start with '+' and be digits after.
        if not v.startswith("+") or not v[1:].isdigit():
            raise ValueError("whatsapp_phone_e164 must be E.164 (eg +5511999999999)")
        return v

    @field_validator("state_uf")
    @classmethod
    def normalize_state(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 2:
            raise ValueError("state_uf must be a 2-letter UF")
        return v

    @field_validator("delivery_types", mode="before")
    @classmethod
    def normalize_delivery(cls, v):
        return _dedupe_normalize(v)

    @field_validator("categories", mode="before")
    @classmethod
    def normalize_categories(cls, v):
        return _dedupe_normalize(v)


class AutoPartCreate(AutoPartBase):
    name: str
    whatsapp_phone_e164: str
    city: str
    state_uf: str


class AutoPartUpdate(AutoPartBase):
    pass
