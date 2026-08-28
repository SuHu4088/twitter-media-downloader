#!/usr/bin/env bash
# Idempotent dev environment bootstrap for the Twitter Media Downloader project.
# Installs system services (PostgreSQL, Redis), Python backend deps, and frontend deps.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Installing system packages (PostgreSQL, Redis, build tools)"
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  postgresql postgresql-contrib redis-server \
  python3-venv python3-dev libpq-dev build-essential

echo "==> Creating Python virtualenv and installing backend dependencies"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r backend/requirements.txt
# Dev/test tooling (mirrors backend/pyproject.toml [dev])
./.venv/bin/pip install "pytest>=7.4.0" "pytest-asyncio>=0.21.0" "aiosqlite>=0.19.0"

echo "==> Installing frontend dependencies"
( cd frontend && npm install )

echo "==> Ensuring local backend/.env exists"
if [ ! -f backend/.env ]; then
  cat > backend/.env <<'EOF'
DEBUG=True

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/social_media
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=local-development-secret-key-please-change-0123456789

TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
TWITTER_REDIRECT_URI=http://localhost:8000/api/v1/auth/twitter/callback

DOWNLOAD_DIR=./downloads
TDL_PATH=./tdl
EOF
  echo "    Created backend/.env (edit to add real Twitter/Telegram credentials)"
fi

echo "==> install.sh complete"
