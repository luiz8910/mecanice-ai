#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "Waiting for db service to be healthy..."
count=0
until [ "$count" -ge 120 ]; do
  cid=$(docker compose ps -q db 2>/dev/null || true)
  if [ -n "$cid" ]; then
    status=$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "")
    if [ "$status" = "healthy" ]; then
      echo "DB container is healthy"
      break
    fi
  fi
  sleep 1
  count=$((count+1))
done

if [ "$count" -ge 120 ]; then
  echo "Timed out waiting for DB to become healthy" >&2
  exit 1
fi

echo "Verifying pg_isready inside container..."
until docker compose exec -T db pg_isready -U postgres -d mecanice >/dev/null 2>&1; do
  sleep 1
done

echo "Postgres is ready."
