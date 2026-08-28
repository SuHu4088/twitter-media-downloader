# 🐦 社交媒体内容管理与下载系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个功能全面的社交媒体内容管理与下载系统，支持自动监测、下载和管理推特账号的媒体内容，并通过Telegram进行内容分发，同时提供可视化的管理界面和数据分析功能。

## 📖 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [安装配置](#安装配置)
- [使用指南](#使用指南)
- [API文档](#api文档)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [部署说明](#部署说明)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [致谢](#致谢)

## ✨ 功能特性

### 🔐 推特账号集成与授权
- 支持 OAuth 2.0 PKCE 安全授权流程
- 多账号绑定与管理
- 令牌自动刷新机制
- 加密存储敏感信息

### 📥 自动化内容检测与下载
- **点赞监测**: 自动下载用户点赞内容中的媒体文件
- **收藏监测**: 自动下载用户收藏内容中的媒体文件
- **关注账号监测**: 定时检查关注账号的内容更新
- **新关注检测**: 检测新关注账号并触发全量下载
- **断点续传**: 支持大文件断点续传下载
- **并发控制**: 智能限流，避免触发API限制

### 💾 数据存储与管理
- PostgreSQL 数据库存储元数据
- 多维度去重机制（文件哈希、推文ID、媒体URL）
- 媒体文件本地存储管理
- 完整的推文内容归档

### 📤 Telegram 内容分发
- 集成 [TDL](https://github.com/iyear/tdl) 工具
- 支持单文件和批量上传
- 自动重试失败任务
- 上传进度追踪

### 📊 数据可视化与管理界面
- 现代化 Web 管理界面
- 媒体内容网格展示
- 博主发布频率分析图表
- 多维度内容筛选与搜索
- 任务状态实时监控

### 🌐 网络访问优化
- 支持 HTTP/HTTPS/SOCKS5 代理
- 代理连接测试功能
- 请求重试与超时配置

## 🛠 技术栈

### 后端
| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 主要开发语言 |
| FastAPI | 0.104+ | 异步Web框架 |
| SQLAlchemy | 2.0+ | ORM框架 |
| PostgreSQL | 15+ | 关系型数据库 |
| Celery | 5.3+ | 异步任务队列 |
| Redis | 7+ | 缓存与消息代理 |
| Alembic | 1.12+ | 数据库迁移工具 |

### 前端
| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| TypeScript | 5.0+ | 类型安全 |
| Element Plus | 2.4+ | UI组件库 |
| Pinia | 2.1+ | 状态管理 |
| ECharts | 5.4+ | 数据可视化 |
| Vite | 5.0+ | 构建工具 |

### 基础设施
| 技术 | 说明 |
|------|------|
| Docker | 容器化部署 |
| Nginx | 反向代理与静态文件服务 |

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Twitter Developer 账号（获取 API 凭证）
- Telegram API 凭证（可选，用于上传功能）

### 一键启动

```bash
# 克隆项目
git clone https://github.com/yourusername/social-media-manager.git
cd social-media-manager

# 复制环境变量配置
cp .env.example .env

# 编辑环境变量（填入你的配置）
nano .env

# 启动所有服务
docker-compose up -d

# 初始化数据库
docker-compose exec backend python scripts/init_db.py
```

### 访问应用

- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc

## ⚙️ 安装配置

### 环境变量说明

创建 `.env` 文件并配置以下变量：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/social_media

# Redis配置
REDIS_URL=redis://redis:6379/0

# 安全配置
SECRET_KEY=your-secret-key-change-in-production

# Twitter OAuth 配置
TWITTER_CLIENT_ID=your-twitter-client-id
TWITTER_CLIENT_SECRET=your-twitter-client-secret
TWITTER_REDIRECT_URI=http://localhost:8000/api/v1/twitter/oauth/callback

# Telegram 配置（可选）
TELEGRAM_API_ID=your-api-id
TELEGRAM_API_HASH=your-api-hash

# 代理配置（可选）
PROXY_HTTP=http://127.0.0.1:7890
PROXY_HTTPS=http://127.0.0.1:7890

# 下载配置
DOWNLOAD_PATH=/app/downloads
TDL_PATH=/app/tdl
```

### 获取 Twitter API 凭证

1. 访问 [Twitter Developer Portal](https://developer.twitter.com/)
2. 创建新的项目和应用
3. 在应用设置中启用 OAuth 2.0
4. 添加回调 URL: `http://your-domain/api/v1/twitter/oauth/callback`
5. 获取 Client ID 和 Client Secret

### 获取 Telegram API 凭证

1. 访问 [Telegram API](https://my.telegram.org/apps)
2. 创建新应用获取 API ID 和 API Hash
3. 下载 [TDL](https://github.com/iyear/tdl/releases) 工具

### 开发环境配置

```bash
# 后端开发环境
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 启动 Celery Worker（新终端）
celery -A app.core.celery_app worker --loglevel=info

# 启动 Celery Beat（新终端）
celery -A app.core.celery_app beat --loglevel=info

# 前端开发环境
cd frontend
npm install
npm run dev
```

## 📚 使用指南

### 1. 用户注册与登录

首次使用需要注册账号：

```bash
# 通过 API 注册
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "your-password"}'
```

或通过 Web 界面注册登录。

### 2. 绑定 Twitter 账号

1. 进入「账号管理」页面
2. 点击「绑定 Twitter 账号」
3. 授权后自动完成绑定
4. 查看账号状态和同步信息

### 3. 配置同步任务

系统支持以下同步任务：

| 任务类型 | 说明 | 默认间隔 |
|---------|------|---------|
| 点赞同步 | 同步用户点赞的媒体内容 | 每小时 |
| 收藏同步 | 同步用户收藏的媒体内容 | 每小时 |
| 关注时间线 | 同步关注账号的最新内容 | 每30分钟 |
| 新关注检测 | 检测新关注的账号 | 每10分钟 |

可在「系统设置」页面调整任务间隔。

### 4. 配置 Telegram 上传

1. 进入「系统设置」→「Telegram 配置」
2. 填入 API ID 和 API Hash
3. 点击「登录」完成 Telegram 授权
4. 配置目标频道/群组 ID
5. 启用自动上传功能

### 5. 配置代理

1. 进入「系统设置」→「代理配置」
2. 添加代理服务器信息
3. 测试代理连接
4. 设置为默认代理

## 📖 API文档

### 认证接口

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=string&password=string
```

### Twitter 账号接口

```http
# 获取授权URL
GET /api/v1/twitter/oauth/authorize

# OAuth回调
GET /api/v1/twitter/oauth/callback?code=xxx&state=xxx

# 获取账号列表
GET /api/v1/twitter/accounts

# 解绑账号
DELETE /api/v1/twitter/accounts/{id}
```

### 媒体接口

```http
# 获取媒体列表
GET /api/v1/media?page=1&page_size=20&media_type=photo

# 获取媒体详情
GET /api/v1/media/{id}

# 删除媒体
DELETE /api/v1/media/{id}
```

### 任务接口

```http
# 获取任务列表
GET /api/v1/tasks?status=running

# 创建同步任务
POST /api/v1/tasks
Content-Type: application/json

{
  "task_type": "likes",
  "twitter_account_id": "uuid"
}

# 取消任务
POST /api/v1/tasks/{id}/cancel
```

完整 API 文档请访问：http://localhost:8000/docs

## 📁 项目结构

```
social-media-manager/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   └── v1/           # V1 版本 API
│   │   ├── core/             # 核心配置
│   │   │   ├── config.py     # 配置管理
│   │   │   ├── database.py   # 数据库连接
│   │   │   ├── security.py   # 安全工具
│   │   │   └── celery_app.py # Celery 配置
│   │   ├── models/           # 数据模型
│   │   ├── schemas/          # Pydantic 模式
│   │   ├── services/         # 业务逻辑
│   │   ├── tasks/            # Celery 任务
│   │   └── utils/            # 工具函数
│   ├── tests/                # 测试文件
│   ├── alembic/              # 数据库迁移
│   ├── main.py               # 应用入口
│   └── requirements.txt      # Python 依赖
├── frontend/                  # 前端服务
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   ├── components/       # 通用组件
│   │   ├── api/              # API 调用
│   │   ├── stores/           # 状态管理
│   │   ├── router/           # 路由配置
│   │   └── styles/           # 样式文件
│   ├── package.json          # Node 依赖
│   └── vite.config.ts        # Vite 配置
├── scripts/                   # 脚本文件
│   ├── init_db.py            # 数据库初始化
│   └── backup.sh             # 备份脚本
├── docker-compose.yml         # 开发环境编排
├── docker-compose.prod.yml    # 生产环境编排
└── README.md                  # 项目说明
```

## 💻 开发指南

### 运行测试

```bash
# 后端单元测试
cd backend
pytest tests/ -v

# 带覆盖率报告
pytest tests/ --cov=app --cov-report=html

# 前端测试
cd frontend
npm run test
```

### 代码规范

```bash
# Python 代码格式化
cd backend
black app/ tests/
isort app/ tests/

# Python 类型检查
mypy app/

# 前端代码检查
cd frontend
npm run lint
```

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 🚢 部署说明

### Docker 部署（推荐）

```bash
# 复制生产环境配置
cp .env.production.example .env.production

# 编辑配置
nano .env.production

# 启动生产环境
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 手动部署

1. **后端部署**
   ```bash
   cd backend
   pip install -r requirements.txt
   alembic upgrade head
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

2. **前端部署**
   ```bash
   cd frontend
   npm install
   npm run build
   # 将 dist/ 目录部署到 Nginx
   ```

3. **Celery 服务**
   ```bash
   celery -A app.core.celery_app worker --loglevel=info
   celery -A app.core.celery_app beat --loglevel=info
   ```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## ❓ 常见问题

### Q: Twitter OAuth 授权失败？
A: 检查以下配置：
- Twitter Developer Portal 中的回调 URL 是否正确
- Client ID 和 Client Secret 是否配置正确
- 应用是否启用了 OAuth 2.0

### Q: 下载速度很慢？
A: 尝试以下优化：
- 配置代理服务器
- 调整并发下载数量
- 检查网络连接

### Q: Telegram 上传失败？
A: 确认：
- TDL 工具已正确安装
- Telegram API 凭证正确
- 已完成 Telegram 登录授权

### Q: 数据库迁移失败？
A: 检查：
- PostgreSQL 服务是否运行
- 数据库连接配置是否正确
- 是否有足够的数据库权限

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8（Python）和 ESLint（TypeScript）规范
- 编写单元测试覆盖新功能
- 更新相关文档

### 提交信息规范

使用约定式提交：

- `feat:` 新功能
- `fix:` 修复 Bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 UI 组件库
- [TDL](https://github.com/iyear/tdl) - Telegram Downloader 工具
- [x-spider](https://github.com/MiningCattiva/x-spider) - 项目设计参考

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给一个 Star！⭐**

Made with ❤️ by [Your Name]

</div>
