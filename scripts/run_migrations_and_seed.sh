#!/usr/bin/env bash
set -euo pipefail

# Simple migration + seed runner
# Requires: DATABASE_URL env var pointing to Postgres (psql available)

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL not set"
  exit 2
fi

MIG_FOLDER="$(dirname "$0")/../migrations"

echo "Applying migrations from $MIG_FOLDER"
for f in $(ls "$MIG_FOLDER"/*.sql | sort); do
  echo "-- running $f"
  psql "$DATABASE_URL" -f "$f"
done

echo "Migrations applied (including any seeds present in migrations folder)."

echo "Done."
