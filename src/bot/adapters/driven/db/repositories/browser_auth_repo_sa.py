"""SQLAlchemy repository for browser-first authentication."""

from __future__ import annotations

from typing import Any

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import ConflictError, UnauthorizedError, ValidationError


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class BrowserAuthRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_credential(self, payload: dict[str, Any]) -> dict[str, Any]:
        role = str(payload["role"]).strip().lower()
        email = str(payload["email"]).strip().lower()
        actor_id = payload.get("actor_id")

        if role not in {"mechanic", "seller", "admin"}:
            raise ValidationError("role must be mechanic, seller, or admin")

        if role == "admin":
            actor_id = None
        elif actor_id is None:
            raise ValidationError("actor_id is required for mechanic and seller credentials")

        principal = self._load_principal(role=role, actor_id=int(actor_id) if actor_id is not None else None)
        password_hash = _hash_password(str(payload["password"]))

        try:
            row = self._session.execute(
                text(
                    """
                    INSERT INTO browser_auth_credentials (role, actor_id, email, password_hash, active)
                    VALUES (:role, :actor_id, :email, :password_hash, true)
                    RETURNING id, role, actor_id, email, active, created_at, updated_at
                    """
                ),
                {
                    "role": role,
                    "actor_id": actor_id,
                    "email": email,
                    "password_hash": password_hash,
                },
            ).mappings().one()
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("credential already exists for this actor or email") from exc

        return {
            **dict(row),
            "name": principal["name"],
            "shop_id": principal["shop_id"],
        }

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        email_lower = email.strip().lower()
        credential = self._session.execute(
            text(
                """
                SELECT id, role, actor_id, email, password_hash, active
                FROM browser_auth_credentials
                WHERE LOWER(email) = LOWER(:email)
                  AND active = true
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {"email": email_lower},
        ).mappings().one_or_none()

        if credential is not None:
            if not _check_password(password, credential["password_hash"]):
                raise UnauthorizedError("E-mail ou senha inválidos.")

            principal = self._load_principal(
                role=str(credential["role"]),
                actor_id=int(credential["actor_id"]) if credential["actor_id"] is not None else None,
            )
            return {
                "user_id": principal["user_id"],
                "role": principal["role"],
                "shop_id": principal["shop_id"],
                "vendor_id": principal.get("vendor_id"),
                "mechanic_id": principal.get("mechanic_id"),
                "name": principal["name"],
                "email": credential["email"],
            }

        legacy_seller = self._session.execute(
            text(
                """
                SELECT
                    sc.seller_id AS vendor_id,
                    sc.autopart_id AS shop_id,
                    sc.email,
                    sc.password_hash,
                    sc.active,
                    v.name
                FROM seller_credentials sc
                JOIN vendors v ON v.id = sc.seller_id
                WHERE LOWER(sc.email) = LOWER(:email)
                  AND sc.active = true
                  AND v.soft_delete = false
                  AND v.active = true
                LIMIT 1
                """
            ),
            {"email": email_lower},
        ).mappings().one_or_none()

        if legacy_seller is None or not _check_password(password, legacy_seller["password_hash"]):
            raise UnauthorizedError("E-mail ou senha inválidos.")

        return {
            "user_id": int(legacy_seller["vendor_id"]),
            "role": "seller",
            "shop_id": int(legacy_seller["shop_id"]),
            "vendor_id": int(legacy_seller["vendor_id"]),
            "mechanic_id": None,
            "name": str(legacy_seller["name"]),
            "email": str(legacy_seller["email"]),
        }

    def _load_principal(self, *, role: str, actor_id: int | None) -> dict[str, Any]:
        if role == "admin":
            return {
                "user_id": 0,
                "role": "admin",
                "shop_id": None,
                "vendor_id": None,
                "mechanic_id": None,
                "name": "Administrator",
            }

        if role == "mechanic":
            if actor_id is None:
                raise ValidationError("mechanic credentials require actor_id")
            row = self._session.execute(
                text(
                    """
                    SELECT id, name, workshop_id
                    FROM mechanics
                    WHERE id = :id
                      AND soft_delete = false
                      AND status = 'active'
                    """
                ),
                {"id": int(actor_id)},
            ).mappings().one_or_none()
            if row is None:
                raise ValidationError("mechanic not found")
            return {
                "user_id": int(row["id"]),
                "role": "mechanic",
                "shop_id": int(row["workshop_id"]),
                "vendor_id": None,
                "mechanic_id": int(row["id"]),
                "name": str(row["name"]),
            }

        if role == "seller":
            if actor_id is None:
                raise ValidationError("seller credentials require actor_id")
            row = self._session.execute(
                text(
                    """
                    SELECT id, autopart_id, name
                    FROM vendors
                    WHERE id = :id
                      AND soft_delete = false
                      AND active = true
                    """
                ),
                {"id": int(actor_id)},
            ).mappings().one_or_none()
            if row is None:
                raise ValidationError("vendor not found")
            return {
                "user_id": int(row["id"]),
                "role": "seller",
                "shop_id": int(row["autopart_id"]),
                "vendor_id": int(row["id"]),
                "mechanic_id": None,
                "name": str(row["name"]),
            }

        raise ValidationError("unsupported role")
