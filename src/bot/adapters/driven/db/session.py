"""SQLAlchemy session helpers (driven adapter).

Kept intentionally small so application wiring can import `get_session`
without pulling in FastAPI.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.bot.infrastructure.config.settings import settings


def _normalize_database_url(url: str) -> str:
	"""Ensure SQLAlchemy uses psycopg (v3) driver.

	If the URL doesn't specify a driver (eg `postgresql://`), SQLAlchemy
	may default to `psycopg2` which isn't installed in this project.
	"""
	if url.startswith("postgresql+psycopg://"):
		return url
	if url.startswith("postgresql://"):
		return "postgresql+psycopg://" + url[len("postgresql://") :]
	if url.startswith("postgres://"):
		# common alias; SQLAlchemy prefers postgresql
		rest = url[len("postgres://") :]
		return "postgresql+psycopg://" + rest
	return url


engine = create_engine(_normalize_database_url(settings.DATABASE_URL), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Iterator[Session]:
	session = SessionLocal()
	try:
		yield session
	finally:
		session.close()

