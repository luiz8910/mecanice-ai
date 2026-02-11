"""SQLAlchemy repository stub for quotes."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.bot.application.ports.driven.quote_repo import QuoteRepoPort
from src.bot.domain.model.quote import Quote


class QuoteRepoSqlAlchemy(QuoteRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, quote: Quote) -> None:
		raise NotImplementedError("TODO: implement Quote persistence")

	def get(self, id: str) -> Optional[Quote]:
		raise NotImplementedError("TODO: implement Quote retrieval")

	def list(self) -> List[Quote]:
		raise NotImplementedError("TODO: implement Quote listing")

	def remove(self, id: str) -> None:
		raise NotImplementedError("TODO: implement Quote removal")

