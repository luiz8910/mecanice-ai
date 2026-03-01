"""Auth dependencies for FastAPI.

These dependencies are intentionally small and framework-specific.
If an endpoint needs admin-only access, use `Depends(require_admin)`.
If an endpoint is for sellers (vendors), use `Depends(require_seller)`.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
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


@dataclass(frozen=True)
class SellerIdentity:
	"""Claims extracted from the seller JWT."""
	vendor_id: int
	store_id: int


def require_seller(
	authorization: str | None = Header(default=None, alias="Authorization"),
) -> SellerIdentity:
	"""Extract and validate the seller JWT from the Authorization header.

	Expected header format:  Authorization: Bearer <jwt>
	Required JWT claims:     vendor_id (int), store_id (int)
	"""
	if not authorization or not authorization.startswith("Bearer "):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Sessão expirada. Faça login novamente.",
		)

	token = authorization.removeprefix("Bearer ").strip()
	try:
		payload = jwt.decode(
			token,
			settings.SELLER_JWT_SECRET,
			algorithms=["HS256"],
		)
	except jwt.ExpiredSignatureError:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Sessão expirada. Faça login novamente.",
		)
	except jwt.InvalidTokenError:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Sessão expirada. Faça login novamente.",
		)

	vendor_id = payload.get("vendor_id")
	store_id = payload.get("store_id")
	if vendor_id is None or store_id is None:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Sessão expirada. Faça login novamente.",
		)

	return SellerIdentity(vendor_id=int(vendor_id), store_id=int(store_id))

