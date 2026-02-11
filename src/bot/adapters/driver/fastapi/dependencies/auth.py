"""Auth dependencies for FastAPI.

These dependencies are intentionally small and framework-specific.
If an endpoint needs admin-only access, use `Depends(require_admin)`.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from src.bot.infrastructure.config.settings import settings


def require_admin(
	x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
	"""Allow request only if it carries the configured admin token."""
	if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="invalid admin token",
		)

