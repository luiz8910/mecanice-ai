"""SQLAlchemy repository stub for workshops."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.bot.application.ports.driven.workshop_repo import WorkshopRepoPort
from src.bot.domain.model.workshop import Workshop


class WorkshopRepoSqlAlchemy(WorkshopRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, workshop: Workshop) -> None:
		raise NotImplementedError("TODO: implement Workshop persistence")

	def get(self, id: str) -> Optional[Workshop]:
		raise NotImplementedError("TODO: implement Workshop retrieval")

	def list(self) -> List[Workshop]:
		raise NotImplementedError("TODO: implement Workshop listing")

	def remove(self, id: str) -> None:
		raise NotImplementedError("TODO: implement Workshop removal")

