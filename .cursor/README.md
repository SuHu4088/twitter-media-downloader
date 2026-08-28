# Cursor Cloud Agent 环境说明
#
# environment.json 字段说明：
#   install  - 首次/更新依赖时执行（见 install.sh）
#   start    - 每次 Agent 启动时执行（见 start.sh）
#   terminals- 长期运行的开发服务（backend 8000、frontend 3000）
#   ports    - 需要暴露给 Agent 访问的端口
#
# 本地手动启动（不用 Cloud Agent）：
#   bash .cursor/install.sh && bash .cursor/start.sh
#   cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000
#   cd frontend && npm run dev
