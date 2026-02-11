"""SQLAlchemy repository stub for solicitations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.bot.application.ports.driven.solicitation_repo import (
	SolicitationRepoPort,
)
from src.bot.domain.model.solicitation import Solicitation


class SolicitationRepoSqlAlchemy(SolicitationRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, solicitation: Solicitation) -> None:
		raise NotImplementedError("TODO: implement Solicitation persistence")

	def get(self, id: str) -> Optional[Solicitation]:
		raise NotImplementedError("TODO: implement Solicitation retrieval")

	def list(self) -> List[Solicitation]:
		raise NotImplementedError("TODO: implement Solicitation listing")

	def remove(self, id: str) -> None:
		raise NotImplementedError("TODO: implement Solicitation removal")

