#!/usr/bin/env bash
# =============================================================================
# Cloud Agent / 本地开发：一次性环境安装脚本（可重复执行，幂等）
#
# 作用：
#   1. 安装系统依赖：PostgreSQL、Redis、Python 构建工具
#   2. 创建仓库根目录 .venv 并安装 backend/requirements.txt
#   3. 安装 pytest 等测试依赖（与 pyproject.toml [dev] 对齐）
#   4. 执行 frontend npm install
#   5. 若不存在则生成 backend/.env（本地开发默认值，不含真实密钥）
#
# 用法：在仓库根目录执行  bash .cursor/install.sh
# 说明：不启动服务；启动数据库与迁移请运行 bash .cursor/start.sh
# =============================================================================
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
# 测试套件使用 sqlite+aiosqlite 内存库
./.venv/bin/pip install "pytest>=7.4.0" "pytest-asyncio>=0.21.0" "aiosqlite>=0.19.0"

echo "==> Installing frontend dependencies"
( cd frontend && npm install )

echo "==> Ensuring local backend/.env exists"
if [ ! -f backend/.env ]; then
  # 仅用于本地开发；生产环境务必替换 SECRET_KEY 并填入真实 OAuth 凭证
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
