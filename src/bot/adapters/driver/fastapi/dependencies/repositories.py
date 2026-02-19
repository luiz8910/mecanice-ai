"""Repository dependencies for FastAPI (driver adapter)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from src.bot.adapters.driven.db.session import get_session
from src.bot.adapters.driven.db.repositories.mechanic_repo_sa import (
	MechanicRepoSqlAlchemy,
)
from src.bot.adapters.driven.db.repositories.workshop_repo_sa import WorkshopRepoSqlAlchemy


def get_mechanic_repo(
	session: Session = Depends(get_session),
) -> MechanicRepoSqlAlchemy:
	return MechanicRepoSqlAlchemy(session)


def get_workshop_repo(
	session: Session = Depends(get_session),
) -> WorkshopRepoSqlAlchemy:
	return WorkshopRepoSqlAlchemy(session)
