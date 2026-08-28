#!/usr/bin/env bash
# =============================================================================
# Cloud Agent / 本地开发：每次启动环境时执行的脚本（可重复执行，幂等）
#
# 作用：
#   1. 启动 PostgreSQL 与 Redis（无 systemd 时用 pg_ctlcluster / redis-server）
#   2. 确保 postgres 用户密码与 social_media 数据库存在
#   3. 执行 alembic upgrade head 应用数据库迁移
#
# 用法：先运行 install.sh，再运行本脚本，最后在 terminals 中启动前后端
# =============================================================================
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
