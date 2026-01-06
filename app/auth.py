from __future__ import annotations

from fastapi import Header, HTTPException, status
from .settings import settings


def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """MVP admin auth:
    - X-Admin-Token: <token>
    - Authorization: Bearer <token>
    """
    token = None
    if x_admin_token:
        token = x_admin_token.strip()

    if not token and authorization:
        auth = authorization.strip()
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()

    if not token or token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
