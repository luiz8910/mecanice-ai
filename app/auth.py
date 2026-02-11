"""Minimal admin-token auth dependency (compat).

Tests override `require_admin` via FastAPI dependency overrides.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    expected = os.getenv("ADMIN_TOKEN", "change-me")
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin token",
        )
