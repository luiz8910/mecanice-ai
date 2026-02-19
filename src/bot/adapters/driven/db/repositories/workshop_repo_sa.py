"""SQLAlchemy repository for workshops."""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.bot.application.ports.driven.workshop_repo import WorkshopRepoPort
from src.bot.domain.errors import ConflictError, ValidationError, WorkshopNotFound
from src.bot.domain.model.workshop import Workshop


WORKSHOP_RETURNING = """\
id,
name,
whatsapp_phone_e164,
city,
state_uf,
status,
address,
email,
notes,
created_at,
updated_at,
soft_delete
"""


class WorkshopRepoSqlAlchemy(WorkshopRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, workshop: Workshop) -> None:
		payload = {
			"name": workshop.name,
			"whatsapp_phone_e164": workshop.whatsapp_phone_e164,
			"city": workshop.city,
			"state_uf": workshop.state_uf,
			"status": workshop.status or "active",
			"address": workshop.address,
			"email": workshop.email,
			"notes": workshop.notes,
		}
		row = self.create(payload)
		workshop.id = row["id"]

	def get(self, id: str) -> Optional[Workshop]:
		row = self.get_row(int(id))
		if row is None:
			return None
		return Workshop(
			id=row["id"],
			name=row["name"],
			whatsapp_phone_e164=row["whatsapp_phone_e164"],
			city=row["city"],
			state_uf=row["state_uf"],
			status=row["status"],
			address=row.get("address"),
			email=row.get("email"),
			notes=row.get("notes"),
		)

	def list(self) -> List[Workshop]:
		rows = self.list_rows(limit=1000, offset=0)
		return [
			Workshop(
				id=r["id"],
				name=r["name"],
				whatsapp_phone_e164=r["whatsapp_phone_e164"],
				city=r["city"],
				state_uf=r["state_uf"],
				status=r["status"],
				address=r.get("address"),
				email=r.get("email"),
				notes=r.get("notes"),
			)
			for r in rows
		]

	def remove(self, id: str) -> None:
		self.delete(int(id))

	def create(self, payload: dict[str, Any]) -> dict[str, Any]:
		stmt = text(
			f"""
			INSERT INTO workshops (
				name,
				whatsapp_phone_e164,
				city,
				state_uf,
				status,
				address,
				email,
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
				:notes
			)
			RETURNING {WORKSHOP_RETURNING}
			"""
		)
		try:
			res = self._session.execute(stmt, payload)
			row = res.mappings().one()
			self._session.commit()
			return dict(row)
		except IntegrityError as exc:
			self._session.rollback()
			raise ConflictError("workshop already exists") from exc

	def get_row(self, workshop_id: int) -> Optional[dict[str, Any]]:
		stmt = text(
			f"""
			SELECT {WORKSHOP_RETURNING}
			FROM workshops
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": workshop_id})
		row = res.mappings().one_or_none()
		return dict(row) if row else None

	def exists_active(self, workshop_id: int) -> bool:
		stmt = text(
			"""
			SELECT 1
			FROM workshops
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": workshop_id}).first()
		return res is not None

	def list_rows(
		self,
		*,
		limit: int = 50,
		offset: int = 0,
		status: str | None = None,
	) -> list[dict[str, Any]]:
		where_parts: list[str] = ["soft_delete = false"]
		params: dict[str, Any] = {
			"limit": int(limit),
			"offset": int(offset),
		}
		if status is not None:
			where_parts.append("status = :status")
			params["status"] = status

		where_sql = "\n\t\t\tAND ".join(where_parts)
		stmt = text(
			f"""
			SELECT {WORKSHOP_RETURNING}
			FROM workshops
			WHERE {where_sql}
			ORDER BY id
			LIMIT :limit
			OFFSET :offset
			"""
		)
		res = self._session.execute(stmt, params)
		return [dict(r) for r in res.mappings().all()]

	def update(self, workshop_id: int, payload: dict[str, Any]) -> dict[str, Any]:
		allowed = {
			"name",
			"whatsapp_phone_e164",
			"city",
			"state_uf",
			"status",
			"address",
			"email",
			"notes",
		}
		updates = {k: v for k, v in payload.items() if k in allowed}
		if not updates:
			raise ValidationError("no fields to update")

		set_parts = [f"{k} = :{k}" for k in updates.keys()]
		set_sql = ",\n\t\t\t".join(set_parts)

		stmt = text(
			f"""
			UPDATE workshops
			SET
				{set_sql},
				updated_at = now()
			WHERE id = :id
			  AND soft_delete = false
			RETURNING {WORKSHOP_RETURNING}
			"""
		)
		params = {"id": workshop_id, **updates}
		try:
			res = self._session.execute(stmt, params)
			row = res.mappings().one_or_none()
			if row is None:
				self._session.rollback()
				raise WorkshopNotFound("workshop not found")
			self._session.commit()
			return dict(row)
		except IntegrityError as exc:
			self._session.rollback()
			raise ConflictError("workshop update conflicts with existing data") from exc

	def delete(self, workshop_id: int) -> None:
		linked_stmt = text(
			"""
			SELECT COUNT(*)
			FROM mechanics
			WHERE workshop_id = :workshop_id
			  AND soft_delete = false
			"""
		)
		linked_count = int(
			self._session.execute(linked_stmt, {"workshop_id": workshop_id}).scalar_one()
		)
		if linked_count > 0:
			raise ConflictError("cannot delete workshop with active mechanics")

		stmt = text(
			"""
			UPDATE workshops
			SET
				soft_delete = true,
				updated_at = now()
			WHERE id = :id
			  AND soft_delete = false
			"""
		)
		res = self._session.execute(stmt, {"id": workshop_id})
		if res.rowcount == 0:
			self._session.rollback()
			raise WorkshopNotFound("workshop not found")
		self._session.commit()

