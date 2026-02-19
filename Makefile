.PHONY: install db-up migrate migrate-docker test run ci \
	migration-make migration-make-manual migration-upgrade migration-downgrade migration-reset \
	migration-make-docker migration-make-manual-docker migration-upgrade-docker migration-downgrade-docker migration-reset-docker

PY=python
PIP=${PY} -m pip
DC=docker compose

install:
	${PIP} install -r requirements.txt

db-up:
	${DC} up -d db

# Run migrations using local psql and DATABASE_URL (export before running)
migrate:
	@if [ -z "${DATABASE_URL}" ]; then \
		echo "DATABASE_URL not set. Use migrate-docker or export DATABASE_URL."; exit 2; \
	fi
	bash scripts/run_migrations_and_seed.sh

# Run migrations inside the DB container (requires docker compose running)
migrate-docker:
	# Run all SQL files mounted into /docker-entrypoint-initdb.d in sorted order
	${DC} exec -T db bash -lc "for f in \$$(ls /docker-entrypoint-initdb.d/*.sql | sort); do echo \"running \$$f\"; psql -U postgres -d mecanice -f \"\$$f\" || true; done"

# Alembic migration helpers
# Create a new revision using --autogenerate (provide MSG)
migration-make:
	@if [ -z "$(MSG)" ]; then \
		echo "MSG not set. Usage: make migration-make MSG=\"add table\""; exit 2; \
	fi
	${PY} -m alembic revision --autogenerate -m "$(MSG)"

# Create a manual revision (no autogenerate)
migration-make-manual:
	@if [ -z "$(MSG)" ]; then \
		echo "MSG not set. Usage: make migration-make-manual MSG=\"name\""; exit 2; \
	fi
	${PY} -m alembic revision -m "$(MSG)"

# Apply migrations (default to head). Override with REV=<rev>
migration-upgrade:
	${PY} -m alembic upgrade $(if $(REV),$(REV),head)

# Downgrade to a revision. Example: REV=-1 or REV=<rev_id>
migration-downgrade:
	@if [ -z "$(REV)" ]; then \
		echo "REV not set. Usage: make migration-downgrade REV=-1 (or REV=<rev_id>)"; exit 2; \
	fi
	${PY} -m alembic downgrade $(REV)

# Reset all migrations (downgrade to base)
migration-reset:
	${PY} -m alembic downgrade base

# Alembic targets running inside a temporary python container (development)
# These mount the project, install requirements, and run alembic pointing to the DB service
# Usage examples: make migration-make-docker MSG="add table" | make migration-upgrade-docker | make migration-downgrade-docker REV=-1

migration-make-docker:
	@if [ -z "$(MSG)" ]; then \
		echo "MSG not set. Usage: make migration-make-docker MSG=\"add table\""; exit 2; \
	fi
	${DC} run --rm --no-deps -e DATABASE_URL="postgres://postgres:postgres@db:5432/mecanice" -v $$(pwd):/work -w /work python:3.11 bash -lc "pip install -r requirements.txt >/dev/null 2>&1 || true; alembic revision --autogenerate -m \"$(MSG)\""

migration-make-manual-docker:
	@if [ -z "$(MSG)" ]; then \
		echo "MSG not set. Usage: make migration-make-manual-docker MSG=\"name\""; exit 2; \
	fi
	${DC} run --rm --no-deps -e DATABASE_URL="postgres://postgres:postgres@db:5432/mecanice" -v $$(pwd):/work -w /work python:3.11 bash -lc "pip install -r requirements.txt >/dev/null 2>&1 || true; alembic revision -m \"$(MSG)\""

migration-upgrade-docker:
	${DC} run --rm --no-deps -e DATABASE_URL="postgres://postgres:postgres@db:5432/mecanice" -v $$(pwd):/work -w /work python:3.11 bash -lc "pip install -r requirements.txt >/dev/null 2>&1 || true; alembic upgrade $(if $(REV),$(REV),head)"

migration-downgrade-docker:
	@if [ -z "$(REV)" ]; then \
		echo "REV not set. Usage: make migration-downgrade-docker REV=-1 (or REV=<rev_id>)"; exit 2; \
	fi
	${DC} run --rm --no-deps -e DATABASE_URL="postgres://postgres:postgres@db:5432/mecanice" -v $$(pwd):/work -w /work python:3.11 bash -lc "pip install -r requirements.txt >/dev/null 2>&1 || true; alembic downgrade $(REV)"

migration-reset-docker:
	${DC} run --rm --no-deps -e DATABASE_URL="postgres://postgres:postgres@db:5432/mecanice" -v $$(pwd):/work -w /work python:3.11 bash -lc "pip install -r requirements.txt >/dev/null 2>&1 || true; alembic downgrade base"

test:
	PYTHONPATH=. pytest -q

run:
	uvicorn main:app --reload --port 8001

ci: install db-up migrate-docker test
