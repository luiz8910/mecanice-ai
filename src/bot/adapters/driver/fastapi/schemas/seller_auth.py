"""Schemas for seller authentication (login / register)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SellerLoginSchema(BaseModel):
    email: str = Field(..., min_length=1, description="E-mail do vendedor")
    password: str = Field(..., min_length=6, description="Senha do vendedor")


class SellerLoginResponseSchema(BaseModel):
    token: str = Field(..., description="JWT Bearer token")
    vendor_id: int
    store_id: int
    seller_name: str


class SellerCredentialCreateSchema(BaseModel):
    seller_id: int = Field(..., gt=0, description="ID do vendor")
    autopart_id: int = Field(..., gt=0, description="ID da autopeça (loja)")
    email: str = Field(..., min_length=1, description="E-mail de login")
    password: str = Field(..., min_length=6, description="Senha")


class SellerCredentialResponseSchema(BaseModel):
    id: int
    seller_id: int
    autopart_id: int
    email: str
    active: bool
    created_at: datetime
    updated_at: datetime
