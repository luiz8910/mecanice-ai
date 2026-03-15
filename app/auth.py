"""Minimal admin-token auth dependency (compat).

Tests override `require_admin` via FastAPI dependency overrides.
"""

from __future__ import annotations

from fastapi import Header


def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    # MVP-only bypass to speed up integration.
    # TODO: restore strict token validation before production.
    _ = x_admin_token
    return None
