from __future__ import annotations

import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


MechanicStatus = Literal["active", "blocked"]
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

BR_UF = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
}


class MechanicBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    whatsapp_phone_e164: str = Field(description="WhatsApp phone in E.164, e.g. +5511999999999")
    city: str = Field(min_length=2, max_length=80)
    state_uf: str = Field(min_length=2, max_length=2, description="UF, e.g. SP")
    status: MechanicStatus = "active"

    address: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=120)
    responsible_name: Optional[str] = Field(default=None, max_length=120)
    categories: List[str] = Field(default_factory=list)
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

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, v: List[str]) -> List[str]:
        out = []
        for item in (v or []):
            s = str(item).strip()
            if s:
                out.append(s.lower())
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq


class MechanicCreate(MechanicBase):
    pass


class MechanicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    whatsapp_phone_e164: Optional[str] = None
    city: Optional[str] = Field(default=None, min_length=2, max_length=80)
    state_uf: Optional[str] = Field(default=None, min_length=2, max_length=2)
    status: Optional[MechanicStatus] = None

    address: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=120)
    responsible_name: Optional[str] = Field(default=None, max_length=120)
    categories: Optional[List[str]] = None
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

    @field_validator("categories")
    @classmethod
    def normalize_categories(cls, v: List[str] | None) -> List[str] | None:
        if v is None:
            return None
        out = []
        for item in v:
            s = str(item).strip()
            if s:
                out.append(s.lower())
        seen = set()
        uniq = []
        for s in out:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq


class MechanicRead(MechanicBase):
    id: int
    created_at: str
    updated_at: str
