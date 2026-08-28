#!/usr/bin/env bash
# Idempotent per-boot startup: brings up PostgreSQL + Redis, ensures the
# database exists, and applies migrations. Safe to run repeatedly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Starting PostgreSQL"
PG_VER="$(ls /etc/postgresql 2>/dev/null | sort -n | tail -1 || true)"
if [ -n "$PG_VER" ]; then
  sudo pg_ctlcluster "$PG_VER" main start 2>/dev/null || true
fi

echo "==> Starting Redis"
sudo redis-server /etc/redis/redis.conf --daemonize yes 2>/dev/null || true

echo "==> Waiting for PostgreSQL to accept connections"
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q 2>/dev/null; then
    break
  fi
  sleep 1
done

echo "==> Ensuring postgres role password and database"
sudo -u postgres psql -tAc "ALTER USER postgres PASSWORD 'postgres';" >/dev/null 2>&1 || true
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='social_media'" 2>/dev/null | grep -q 1; then
  sudo -u postgres psql -c "CREATE DATABASE social_media;" >/dev/null 2>&1 || true
fi

echo "==> Applying database migrations"
( cd backend && "$REPO_ROOT/.venv/bin/alembic" upgrade head )

echo "==> start.sh complete (Postgres + Redis up, migrations applied)"
