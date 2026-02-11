"""SQLAlchemy repository stub for suppliers."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from src.bot.application.ports.driven.supplier_repo import SupplierRepoPort
from src.bot.domain.model.supplier import Supplier


class SupplierRepoSqlAlchemy(SupplierRepoPort):
	def __init__(self, session: Session) -> None:
		self._session = session

	def add(self, supplier: Supplier) -> None:
		raise NotImplementedError("TODO: implement Supplier persistence")

	def get(self, id: str) -> Optional[Supplier]:
		raise NotImplementedError("TODO: implement Supplier retrieval")

	def list(self) -> List[Supplier]:
		raise NotImplementedError("TODO: implement Supplier listing")

	def remove(self, id: str) -> None:
		raise NotImplementedError("TODO: implement Supplier removal")

