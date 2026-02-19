"""SQLAlchemy repository for mechanics.

This adapter talks to the `mechanics` table created by
`migrations/002_create_mechanics.sql`.
"""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.application.ports.driven.mechanic_repo import MechanicRepoPort
from src.bot.domain.errors import (
	ConflictError,
	MechanicNotFound,
	ValidationError,
	WorkshopNotFound,
)
from src.bot.domain.model.mechanic import Mechanic


MECHANIC_RETURNING = """\
id,
name,
whatsapp_phone_e164,
city,
state_uf,
status,
address,
email,
workshop_id,
categories,
notes,
created_at,
updated_at,
soft_delete
"""


class MechanicRepoSqlAlchemy(MechanicRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, mechanic: Mechanic) -> None:
		payload = {
			"name": mechanic.name,
			"whatsapp_phone_e164": mechanic.whatsapp_phone_e164,
			"city": mechanic.city,
			"state_uf": mechanic.state_uf,
			"status": mechanic.status or "active",
			"address": mechanic.address,
			"email": mechanic.email,
			"workshop_id": mechanic.workshop_id,
			"categories": mechanic.categories or [],
			"notes": mechanic.notes,
		}
		row = self.create(payload)
		mechanic.id = row["id"]

	def get(self, id: str) -> Optional[Mechanic]:
		row = self.get_row(int(id))
		if row is None:
			return None
		return Mechanic(
			id=row["id"],
			name=row["name"],
			whatsapp_phone_e164=row["whatsapp_phone_e164"],
			city=row["city"],
			state_uf=row["state_uf"],
			status=row["status"],
			address=row.get("address"),
			email=row.get("email"),
			categories=row.get("categories") or [],
			notes=row.get("notes"),
			workshop_id=row.get("workshop_id"),
		)

	def list_by_workshop(self, workshop_id: str) -> List[Mechanic]:
		rows = self.list(limit=1000, offset=0, workshop_id=int(workshop_id))
		return [
			Mechanic(
				id=r["id"],
				name=r["name"],
				whatsapp_phone_e164=r["whatsapp_phone_e164"],
				city=r["city"],
				state_uf=r["state_uf"],
				status=r["status"],
				address=r.get("address"),
				email=r.get("email"),
				categories=r.get("categories") or [],
				notes=r.get("notes"),
				workshop_id=r.get("workshop_id"),
			)
			for r in rows
		]

	def remove(self, id: str) -> None:
		self.delete(int(id))

	# ── CRUD helpers used by FastAPI router ───────────────────────────
	def create(self, payload: dict[str, Any]) -> dict[str, Any]:
		workshop_id = payload.get("workshop_id")
		if workshop_id is None:
			raise ValidationError("workshop_id is required")
		if not self._workshop_exists(int(workshop_id)):
			raise WorkshopNotFound("workshop not found")

		stmt = text(
			f"""
			INSERT INTO mechanics (
				name,
				whatsapp_phone_e164,
				city,
				state_uf,
				status,
				address,
				email,
				workshop_id,
				categories,
				notes
			)
			VALUES (
				:name,
				:whatsapp_phone_e164,
				:city,
				:state_uf,
				:status,
				:address,
				:email,
				:workshop_id,
				:categories,
				:notes
			)
			RETURNING {MECHANIC_RETURNING}
			"""
		)
		try:
			res = self._session.execute(stmt, payload)
			row = res.mappings().one()
			self._session.commit()
			return dict(row)
		except IntegrityError as exc:
			self._session.rollback()
			raise ConflictError("mechanic already exists") from exc

	def get_row(self, mechanic_id: int) -> Optional[dict[str, Any]]:
		stmt = text(
			f"""
			SELECT {MECHANIC_RETURNING}
			FROM mechanics
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": mechanic_id})
		row = res.mappings().one_or_none()
		return dict(row) if row else None

	def list(
		self,
		*,
		limit: int = 50,
		offset: int = 0,
		status: str | None = None,
		workshop_id: int | None = None,
	) -> list[dict[str, Any]]:
		# Avoid passing NULL-typed bind parameters in expressions like
		# ':status IS NULL OR status = :status' which can trigger
		# psycopg.errors.AmbiguousParameter.
		where_parts: list[str] = ["soft_delete = false"]
		params: dict[str, Any] = {
			"limit": int(limit),
			"offset": int(offset),
		}
		if status is not None:
			where_parts.append("status = :status")
			params["status"] = status
		if workshop_id is not None:
			where_parts.append("workshop_id = :workshop_id")
			params["workshop_id"] = int(workshop_id)

		where_sql = "\n\t\t\tAND ".join(where_parts)
		stmt = text(
			f"""
			SELECT {MECHANIC_RETURNING}
			FROM mechanics
			WHERE {where_sql}
			ORDER BY id
			LIMIT :limit
			OFFSET :offset
			"""
		)
		res = self._session.execute(stmt, params)
		return [dict(r) for r in res.mappings().all()]

	def update(self, mechanic_id: int, payload: dict[str, Any]) -> dict[str, Any]:
		allowed = {
			"name",
			"whatsapp_phone_e164",
			"city",
			"state_uf",
			"status",
			"address",
			"email",
			"workshop_id",
			"categories",
			"notes",
		}
		updates = {k: v for k, v in payload.items() if k in allowed}
		if not updates:
			raise ValidationError("no fields to update")
		if "workshop_id" in updates:
			if updates["workshop_id"] is None:
				raise ValidationError("workshop_id cannot be null")
			if not self._workshop_exists(int(updates["workshop_id"])):
				raise WorkshopNotFound("workshop not found")

		set_parts = [f"{k} = :{k}" for k in updates.keys()]
		set_sql = ",\n\t\t\t".join(set_parts)

		stmt = text(
			f"""
			UPDATE mechanics
			SET
				{set_sql},
				updated_at = now()
			WHERE id = :id
			  AND soft_delete = false
			RETURNING {MECHANIC_RETURNING}
			"""
		)
		params = {"id": mechanic_id, **updates}
		try:
			res = self._session.execute(stmt, params)
			row = res.mappings().one_or_none()
			if row is None:
				self._session.rollback()
				raise MechanicNotFound("mechanic not found")
			self._session.commit()
			return dict(row)
		except IntegrityError as exc:
			self._session.rollback()
			raise ConflictError("mechanic update conflicts with existing data") from exc

	def delete(self, mechanic_id: int) -> None:
		stmt = text(
			"""
			UPDATE mechanics
			SET
				soft_delete = true,
				updated_at = now()
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": mechanic_id})
		if res.rowcount == 0:
			self._session.rollback()
			raise MechanicNotFound("mechanic not found")
		self._session.commit()

	def _workshop_exists(self, workshop_id: int) -> bool:
		stmt = text(
			"""
			SELECT 1
			FROM workshops
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": int(workshop_id)}).first()
		return res is not None

