"""SQLAlchemy repository stub for mechanics."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.bot.application.ports.driven.mechanic_repo import MechanicRepoPort
from src.bot.domain.model.mechanic import Mechanic


class MechanicRepoSqlAlchemy(MechanicRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, mechanic: Mechanic) -> None:
		raise NotImplementedError("TODO: implement Mechanic persistence")

	def get(self, id: str) -> Optional[Mechanic]:
		raise NotImplementedError("TODO: implement Mechanic retrieval")

	def list_by_workshop(self, workshop_id: str) -> List[Mechanic]:
		raise NotImplementedError("TODO: implement Mechanics listing")

	def remove(self, id: str) -> None:
		raise NotImplementedError("TODO: implement Mechanic removal")

