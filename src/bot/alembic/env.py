"""Alembic environment file for project migrations.

This file configures Alembic to run migrations. It attempts to discover
SQLAlchemy `MetaData` (target_metadata) from common locations in the
project; if none is found it will run migrations without autogenerate.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root is on sys.path so imports work when alembic runs here
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
	fileConfig(config.config_file_name)

# Try to locate project metadata from likely modules. If not found, keep None.
target_metadata = None
_attempt_modules = (
	"src.bot.adapters.driven.db.models",
	"app.models",
	"models",
	"src.bot.adapters.driven.db",
)
for _m in _attempt_modules:
	try:
		mod = __import__(_m, fromlist=["*"])
	except Exception:
		continue
	# common patterns: module provides `Base` (declarative base) or `metadata` directly
	if hasattr(mod, "Base"):
		Base = getattr(mod, "Base")
		if hasattr(Base, "metadata"):
			target_metadata = Base.metadata
			break
	if hasattr(mod, "metadata"):
		target_metadata = getattr(mod, "metadata")
		break


def _get_url() -> str | None:
	"""Return a database URL from env var or alembic config."""
	return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
	"""Run migrations in 'offline' mode.

	This configures the context with just a URL and not an Engine, though
	an Engine is acceptable as well.  By skipping the Engine creation we
	avoid needing DB driver dependencies for offline generation.
	"""
	url = _get_url()
	if not url:
		raise RuntimeError("No database URL configured for offline migrations")
	context.configure(
		url=url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
	)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online() -> None:
	"""Run migrations in 'online' mode.

	Create an Engine and associate a connection with the context.
	"""
	# ensure config has a url value (engine_from_config will read this)
	url = _get_url()
	if url:
		config.set_main_option("sqlalchemy.url", url)

	connectable = engine_from_config(
		config.get_section(config.config_ini_section),
		prefix="sqlalchemy.",
		poolclass=pool.NullPool,
	)

	with connectable.connect() as connection:
		context.configure(connection=connection, target_metadata=target_metadata)

		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
