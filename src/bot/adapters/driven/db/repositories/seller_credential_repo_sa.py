"""SQLAlchemy repository for seller credentials (login)."""

from __future__ import annotations

from typing import Any

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.domain.errors import ConflictError, UnauthorizedError, ValidationError


CREDENTIAL_RETURNING = """\
id,
seller_id,
autopart_id,
email,
active,
created_at,
updated_at
"""


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


class SellerCredentialRepoSqlAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── register ─────────────────────────────────────────────────

    def create_credential(self, payload: dict[str, Any]) -> dict[str, Any]:
        seller_id = int(payload["seller_id"])
        autopart_id = int(payload["autopart_id"])

        # Validate vendor exists
        vendor = self._session.execute(
            text("SELECT id, autopart_id FROM vendors WHERE id = :id AND soft_delete = false"),
            {"id": seller_id},
        ).mappings().one_or_none()
        if vendor is None:
            raise ValidationError("seller (vendor) not found")
        if int(vendor["autopart_id"]) != autopart_id:
            raise ValidationError("autopart_id does not match vendor's store")

        password_hash = _hash_password(payload["password"])

        stmt = text(
            f"""
            INSERT INTO seller_credentials (seller_id, autopart_id, email, password_hash)
            VALUES (:seller_id, :autopart_id, :email, :password_hash)
            RETURNING {CREDENTIAL_RETURNING}
            """
        )
        try:
            row = self._session.execute(
                stmt,
                {
                    "seller_id": seller_id,
                    "autopart_id": autopart_id,
                    "email": payload["email"].strip().lower(),
                    "password_hash": password_hash,
                },
            ).mappings().one()
            self._session.commit()
            return dict(row)
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("email already registered") from exc

    # ── authenticate ─────────────────────────────────────────────

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        """Validate email+password and return credential + vendor info.

        Raises UnauthorizedError when credentials are invalid.
        """
        row = self._session.execute(
            text(
                """
                SELECT
                    sc.id,
                    sc.seller_id,
                    sc.autopart_id,
                    sc.email,
                    sc.password_hash,
                    sc.active,
                    v.name AS seller_name
                FROM seller_credentials sc
                JOIN vendors v ON v.id = sc.seller_id
                WHERE sc.email = :email
                  AND sc.active = true
                  AND v.soft_delete = false
                  AND v.active = true
                """
            ),
            {"email": email.strip().lower()},
        ).mappings().one_or_none()

        if row is None:
            raise UnauthorizedError("E-mail ou senha inválidos.")

        if not _check_password(password, row["password_hash"]):
            raise UnauthorizedError("E-mail ou senha inválidos.")

        return {
            "seller_id": row["seller_id"],
            "autopart_id": row["autopart_id"],
            "email": row["email"],
            "seller_name": row["seller_name"],
        }
