from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

from .db import get_pool
from .autoparts_schemas import AutoPartCreate, AutoPartUpdate, AutoPartStatus
from .exceptions import NotFoundError, DuplicatePhoneError


def create_autopart(payload: AutoPartCreate) -> Dict[str, Any]:
    pool = get_pool()
    data = payload.model_dump()

    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        if not row:
            return row
        for k in ("created_at", "updated_at"):
            v = row.get(k)
            if v is not None:
                try:
                    row[k] = v.isoformat()
                except Exception:
                    row[k] = str(v)
        return row

    with pool.connection() as conn:
        conn.row_factory = dict_row
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO autoparts
                        (name, whatsapp_phone_e164, address, city, state_uf, status,
                         opening_hours, delivery_types, radius_km, categories, responsible_name, notes, created_at, updated_at)
                    VALUES
                        (%(name)s, %(whatsapp_phone_e164)s, %(address)s, %(city)s, %(state_uf)s, %(status)s,
                         %(opening_hours)s, %(delivery_types)s, %(radius_km)s, %(categories)s, %(responsible_name)s, %(notes)s,
                         now(), now())
                    RETURNING *;
                    """,
                    data,
                )
                row = cur.fetchone()
                conn.commit()
                return _serialize_row(row)
        except psycopg.errors.UniqueViolation as e:
            conn.rollback()
            raise DuplicatePhoneError("whatsapp_phone_e164 already exists") from e


def get_autopart(autopart_id: int) -> Dict[str, Any]:
    pool = get_pool()

    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        if not row:
            return row
        for k in ("created_at", "updated_at"):
            v = row.get(k)
            if v is not None:
                try:
                    row[k] = v.isoformat()
                except Exception:
                    row[k] = str(v)
        return row

    with pool.connection() as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM autoparts WHERE id = %s;", (autopart_id,))
            row = cur.fetchone()
            if not row:
                raise NotFoundError("autopart not found")
            return _serialize_row(row)


def list_autoparts(limit: int = 50, offset: int = 0, status: Optional[AutoPartStatus] = None) -> List[Dict[str, Any]]:
    pool = get_pool()

    def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
        if not row:
            return row
        for k in ("created_at", "updated_at"):
            v = row.get(k)
            if v is not None:
                try:
                    row[k] = v.isoformat()
                except Exception:
                    row[k] = str(v)
        return row

    with pool.connection() as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    "SELECT * FROM autoparts WHERE status = %s ORDER BY id DESC LIMIT %s OFFSET %s;",
                    (status, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT * FROM autoparts ORDER BY id DESC LIMIT %s OFFSET %s;",
                    (limit, offset),
                )
            rows = list(cur.fetchall())
            return [_serialize_row(r) for r in rows]


def update_autopart(autopart_id: int, payload: AutoPartUpdate) -> Dict[str, Any]:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_autopart(autopart_id)

    allowed = {
        "name", "whatsapp_phone_e164", "address", "city", "state_uf", "status",
        "opening_hours", "delivery_types", "radius_km", "categories", "responsible_name", "notes"
    }

    set_parts = []
    params: Dict[str, Any] = {"id": autopart_id}
    for k, v in updates.items():
        if k in allowed:
            set_parts.append(f"{k} = %({k})s")
            params[k] = v

    if not set_parts:
        return get_autopart(autopart_id)

    set_sql = ", ".join(set_parts) + ", updated_at = now()"

    pool = get_pool()
    with pool.connection() as conn:
        conn.row_factory = dict_row
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE autoparts
                    SET {set_sql}
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    raise NotFoundError("autopart not found")
                conn.commit()
                for k in ("created_at", "updated_at"):
                    v = row.get(k)
                    if v is not None:
                        try:
                            row[k] = v.isoformat()
                        except Exception:
                            row[k] = str(v)
                return row
        except psycopg.errors.UniqueViolation as e:
            conn.rollback()
            raise DuplicatePhoneError("whatsapp_phone_e164 already exists") from e


def set_autopart_status(autopart_id: int, status: AutoPartStatus) -> Dict[str, Any]:
    pool = get_pool()
    with pool.connection() as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE autoparts
                SET status = %s, updated_at = now()
                WHERE id = %s
                RETURNING *;
                """,
                (status, autopart_id),
            )
            row = cur.fetchone()
            if not row:
                raise NotFoundError("autopart not found")
            conn.commit()
            for k in ("created_at", "updated_at"):
                v = row.get(k)
                if v is not None:
                    try:
                        row[k] = v.isoformat()
                    except Exception:
                        row[k] = str(v)
            return row
