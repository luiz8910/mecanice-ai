"""Seller authentication routes (login + credential management)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import require_admin
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_seller_credential_repo,
)
from src.bot.adapters.driver.fastapi.schemas.seller_auth import (
    SellerCredentialCreateSchema,
    SellerCredentialResponseSchema,
    SellerLoginResponseSchema,
    SellerLoginSchema,
)
from src.bot.adapters.driven.db.repositories.seller_credential_repo_sa import (
    SellerCredentialRepoSqlAlchemy,
)
from src.bot.infrastructure.config.settings import settings

router = APIRouter(prefix="/seller", tags=["seller-auth"])


@router.post(
    "/login",
    response_model=SellerLoginResponseSchema,
    summary="Login do vendedor no Seller Portal",
)
async def seller_login(
    body: SellerLoginSchema,
    repo: SellerCredentialRepoSqlAlchemy = Depends(get_seller_credential_repo),
):
    result = repo.authenticate(body.email, body.password)

    payload = {
        "vendor_id": result["seller_id"],
        "store_id": result["autopart_id"],
        "email": result["email"],
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    token = jwt.encode(payload, settings.SELLER_JWT_SECRET, algorithm="HS256")

    return SellerLoginResponseSchema(
        token=token,
        vendor_id=result["seller_id"],
        store_id=result["autopart_id"],
        seller_name=result["seller_name"],
    )


@router.post(
    "/credentials",
    response_model=SellerCredentialResponseSchema,
    summary="Criar credencial de login para vendedor (admin)",
    dependencies=[Depends(require_admin)],
)
async def create_credential(
    body: SellerCredentialCreateSchema,
    repo: SellerCredentialRepoSqlAlchemy = Depends(get_seller_credential_repo),
):
    return repo.create_credential(body.model_dump())
