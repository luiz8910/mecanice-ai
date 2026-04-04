from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends

from src.bot.adapters.driver.fastapi.dependencies.auth import (
    BrowserIdentity,
    require_admin,
    require_authenticated,
)
from src.bot.adapters.driver.fastapi.dependencies.repositories import (
    get_browser_auth_repo,
)
from src.bot.adapters.driver.fastapi.schemas.auth import (
    AuthCredentialCreateSchema,
    AuthLoginResponseSchema,
    AuthLoginSchema,
    BrowserCredentialResponseSchema,
    BrowserUserSchema,
)
from src.bot.adapters.driven.db.repositories.browser_auth_repo_sa import (
    BrowserAuthRepoSqlAlchemy,
)
from src.bot.infrastructure.config.settings import settings

router = APIRouter(tags=["auth"])


def _encode_token(principal: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": principal["user_id"],
        "role": principal["role"],
        "shop_id": principal.get("shop_id"),
        "vendor_id": principal.get("vendor_id"),
        "mechanic_id": principal.get("mechanic_id"),
        "name": principal["name"],
        "email": principal["email"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=8)).timestamp()),
    }
    return jwt.encode(payload, settings.SELLER_JWT_SECRET, algorithm="HS256")


@router.post("/auth/login", response_model=AuthLoginResponseSchema, summary="Login para usuários do app web")
async def login(
    body: AuthLoginSchema,
    repo: BrowserAuthRepoSqlAlchemy = Depends(get_browser_auth_repo),
):
    principal = repo.authenticate(body.email, body.password)
    token = _encode_token(principal)
    return AuthLoginResponseSchema(
        token=token,
        user=BrowserUserSchema(**principal),
    )


@router.get("/me", response_model=BrowserUserSchema, summary="Usuário autenticado atual")
async def me(identity: BrowserIdentity = Depends(require_authenticated)):
    return BrowserUserSchema(
        user_id=identity.user_id,
        role=identity.role,  # type: ignore[arg-type]
        shop_id=identity.shop_id,
        vendor_id=identity.vendor_id,
        mechanic_id=identity.mechanic_id,
        name=identity.name or "Authenticated User",
        email=identity.email or "unknown@mecanice.local",
    )


@router.post(
    "/auth/credentials",
    response_model=BrowserCredentialResponseSchema,
    summary="Criar credencial do app web (admin)",
    dependencies=[Depends(require_admin)],
)
async def create_credential(
    body: AuthCredentialCreateSchema,
    repo: BrowserAuthRepoSqlAlchemy = Depends(get_browser_auth_repo),
):
    return repo.create_credential(body.model_dump())
