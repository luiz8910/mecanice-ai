from __future__ import annotations

import re
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


AutoPartStatus = Literal["active", "paused"]
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

BR_UF = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
}


class AutoPartBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    whatsapp_phone_e164: str = Field(description="WhatsApp phone in E.164, e.g. +5511999999999")
    address: Optional[str] = Field(default=None, max_length=200)
    city: str = Field(min_length=2, max_length=80)
    state_uf: str = Field(min_length=2, max_length=2, description="UF, e.g. SP")
    status: AutoPartStatus = "active"

    opening_hours: Optional[str] = Field(default=None, max_length=200)
    delivery_types: List[str] = Field(default_factory=list)
    radius_km: Optional[float] = None
    categories: List[str] = Field(default_factory=list)
    responsible_name: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("whatsapp_phone_e164")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        v = (v or "").strip()
        if not _E164_RE.match(v):
            raise ValueError("Invalid E.164 phone number. Example: +5511999999999")
        return v

    @field_validator("state_uf")
    @classmethod
    def validate_uf(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if v not in BR_UF:
            raise ValueError("state_uf must be a valid Brazilian UF")
        return v

    @field_validator("delivery_types")
    @classmethod
    def normalize_delivery(cls, v: List[str]) -> List[str]:
        out = []
        for item in (v or []):
            s = str(item).strip().lower()
            if s:
                out.append(s)
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, v: List[str]) -> List[str]:
        out = []
        for item in (v or []):
            s = str(item).strip().lower()
            if s:
                out.append(s)
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq


class AutoPartCreate(AutoPartBase):
    pass


class AutoPartUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    whatsapp_phone_e164: Optional[str] = None
    address: Optional[str] = Field(default=None, max_length=200)
    city: Optional[str] = Field(default=None, min_length=2, max_length=80)
    state_uf: Optional[str] = Field(default=None, min_length=2, max_length=2)
    status: Optional[AutoPartStatus] = None

    opening_hours: Optional[str] = Field(default=None, max_length=200)
    delivery_types: Optional[List[str]] = None
    radius_km: Optional[float] = None
    categories: Optional[List[str]] = None
    responsible_name: Optional[str] = Field(default=None, max_length=120)
    notes: Optional[str] = Field(default=None, max_length=500)

    @field_validator("whatsapp_phone_e164")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not _E164_RE.match(v):
            raise ValueError("Invalid E.164 phone number. Example: +5511999999999")
        return v

    @field_validator("state_uf")
    @classmethod
    def validate_uf(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().upper()
        if v not in BR_UF:
            raise ValueError("state_uf must be a valid Brazilian UF")
        return v

    @field_validator("delivery_types")
    @classmethod
    def normalize_delivery(cls, v: List[str] | None) -> List[str] | None:
        if v is None:
            return None
        out = []
        for item in v:
            s = str(item).strip().lower()
            if s:
                out.append(s)
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, v: List[str] | None) -> List[str] | None:
        if v is None:
            return None
        out = []
        for item in v:
            s = str(item).strip().lower()
            if s:
                out.append(s)
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq


class AutoPartRead(AutoPartBase):
    id: int
    created_at: datetime
    updated_at: datetime
