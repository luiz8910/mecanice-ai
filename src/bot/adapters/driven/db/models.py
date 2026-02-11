"""SQLAlchemy models for the driven Postgres adapter.

Right now the project uses SQL migrations in `migrations/`.
This module provides a Declarative Base so Alembic autogenerate can be
introduced later without breaking imports.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
	pass

