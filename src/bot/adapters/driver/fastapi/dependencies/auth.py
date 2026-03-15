"""Auth dependencies for FastAPI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from fastapi import Header, HTTPException, status

from src.bot.infrastructure.config.settings import settings


@dataclass(frozen=True)
class BrowserIdentity:
    user_id: int
    role: str
    shop_id: int | None = None
    vendor_id: int | None = None
    mechanic_id: int | None = None
    name: str | None = None
    email: str | None = None


def _http_401() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão expirada. Faça login novamente.",
    )


def _decode_browser_token(token: str) -> BrowserIdentity:
    try:
        payload = jwt.decode(
            token,
            settings.SELLER_JWT_SECRET,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError as exc:
        raise _http_401() from exc
    except jwt.InvalidTokenError as exc:
        raise _http_401() from exc

    role = payload.get("role")
    if role is None and payload.get("vendor_id") is not None:
        role = "seller"

    user_id = payload.get("user_id")
    vendor_id = payload.get("vendor_id")
    mechanic_id = payload.get("mechanic_id")
    shop_id = payload.get("shop_id", payload.get("store_id"))

    if role == "seller" and user_id is None:
        user_id = vendor_id
    if role == "mechanic" and user_id is None:
        user_id = mechanic_id
    if role == "admin" and user_id is None:
        user_id = 0

    if role not in {"admin", "seller", "mechanic"} or user_id is None:
        raise _http_401()

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise _http_401()

    return BrowserIdentity(
        user_id=int(user_id),
        role=str(role),
        shop_id=int(shop_id) if shop_id is not None else None,
        vendor_id=int(vendor_id) if vendor_id is not None else None,
        mechanic_id=int(mechanic_id) if mechanic_id is not None else None,
        name=payload.get("name"),
        email=payload.get("email"),
    )


def require_authenticated(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> BrowserIdentity:
    if not authorization or not authorization.startswith("Bearer "):
        raise _http_401()
    token = authorization.removeprefix("Bearer ").strip()
    return _decode_browser_token(token)


def require_admin(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> BrowserIdentity:
    if authorization and authorization.startswith("Bearer "):
        identity = _decode_browser_token(authorization.removeprefix("Bearer ").strip())
        if identity.role == "admin":
            return identity
    if x_admin_token and x_admin_token == settings.ADMIN_TOKEN:
        return BrowserIdentity(user_id=0, role="admin", name="Administrator")
    raise _http_401()


def require_seller(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> BrowserIdentity:
    identity = require_authenticated(authorization)
    if identity.role != "seller" or identity.vendor_id is None or identity.shop_id is None:
        raise _http_401()
    return identity


def require_mechanic(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> BrowserIdentity:
    identity = require_authenticated(authorization)
    if identity.role != "mechanic" or identity.mechanic_id is None:
        raise _http_401()
    return identity
