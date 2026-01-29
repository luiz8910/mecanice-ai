from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

from .db import get_pool
from .mechanics_schemas import MechanicCreate, MechanicUpdate, MechanicStatus


class NotFoundError(RuntimeError):
    pass


class DuplicatePhoneError(RuntimeError):
    pass


def create_mechanic(payload: MechanicCreate) -> Dict[str, Any]:
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
                    INSERT INTO mechanics
                        (name, whatsapp_phone_e164, city, state_uf, status, address, email,
                         responsible_name, categories, notes, created_at, updated_at)
                    VALUES
                        (%(name)s, %(whatsapp_phone_e164)s, %(city)s, %(state_uf)s, %(status)s,
                         %(address)s, %(email)s, %(responsible_name)s, %(categories)s, %(notes)s,
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


def get_mechanic(mechanic_id: int) -> Dict[str, Any]:
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
            cur.execute("SELECT * FROM mechanics WHERE id = %s;", (mechanic_id,))
            row = cur.fetchone()
            if not row:
                raise NotFoundError("mechanic not found")
            return _serialize_row(row)


def list_mechanics(limit: int = 50, offset: int = 0, status: Optional[MechanicStatus] = None) -> List[Dict[str, Any]]:
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
                    "SELECT * FROM mechanics WHERE status = %s ORDER BY id DESC LIMIT %s OFFSET %s;",
                    (status, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT * FROM mechanics ORDER BY id DESC LIMIT %s OFFSET %s;",
                    (limit, offset),
                )
            rows = list(cur.fetchall())
            return [_serialize_row(r) for r in rows]


def update_mechanic(mechanic_id: int, payload: MechanicUpdate) -> Dict[str, Any]:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_mechanic(mechanic_id)

    allowed = {
        "name", "whatsapp_phone_e164", "city", "state_uf", "status",
        "address", "email", "responsible_name", "categories", "notes"
    }

    set_parts = []
    params: Dict[str, Any] = {"id": mechanic_id}
    for k, v in updates.items():
        if k in allowed:
            set_parts.append(f"{k} = %({k})s")
            params[k] = v

    if not set_parts:
        return get_mechanic(mechanic_id)

    set_sql = ", ".join(set_parts) + ", updated_at = now()"

    pool = get_pool()
    with pool.connection() as conn:
        conn.row_factory = dict_row
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE mechanics
                    SET {set_sql}
                    WHERE id = %(id)s
                    RETURNING *;
                    """,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    raise NotFoundError("mechanic not found")
                conn.commit()
                # serialize datetimes
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


def set_mechanic_status(mechanic_id: int, status: MechanicStatus) -> Dict[str, Any]:
    pool = get_pool()
    with pool.connection() as conn:
        conn.row_factory = dict_row
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mechanics
                SET status = %s, updated_at = now()
                WHERE id = %s
                RETURNING *;
                """,
                (status, mechanic_id),
            )
            row = cur.fetchone()
            if not row:
                raise NotFoundError("mechanic not found")
            conn.commit()
            for k in ("created_at", "updated_at"):
                v = row.get(k)
                if v is not None:
                    try:
                        row[k] = v.isoformat()
                    except Exception:
                        row[k] = str(v)
            return row
