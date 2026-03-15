from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


BrowserRole = Literal["mechanic", "seller", "admin"]


class AuthLoginSchema(BaseModel):
    email: str
    password: str = Field(..., min_length=6, max_length=128)


class AuthCredentialCreateSchema(BaseModel):
    role: BrowserRole
    actor_id: int | None = Field(default=None, gt=0)
    email: str
    password: str = Field(..., min_length=6, max_length=128)


class BrowserUserSchema(BaseModel):
    user_id: int
    role: BrowserRole
    shop_id: int | None = None
    vendor_id: int | None = None
    mechanic_id: int | None = None
    name: str
    email: str


class AuthLoginResponseSchema(BaseModel):
    token: str
    user: BrowserUserSchema


class BrowserCredentialResponseSchema(BaseModel):
    id: int
    role: BrowserRole
    actor_id: int | None = None
    email: str
    active: bool
    created_at: datetime
    updated_at: datetime
    name: str
    shop_id: int | None = None
