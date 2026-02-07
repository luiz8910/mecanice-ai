.PHONY: install db-up migrate migrate-docker test run ci

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
	${DC} exec -T db bash -lc "for f in $(ls /docker-entrypoint-initdb.d/*.sql | sort); do echo \"running $f\"; psql -U postgres -d mecanice -f \"$f\" || true; done"

test:
	PYTHONPATH=. pytest -q

run:
	uvicorn app.main:app --reload

ci: install db-up migrate-docker test
