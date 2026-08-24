# 在线客服工单系统

> 前后端分离架构：后端 FastAPI + 前端 Vue3，容器化交付。

## 技术栈

- **后端**: Python 3.10, FastAPI, SQLAlchemy 2.0, PostgreSQL, Celery, Redis
- **前端**: Vue 3, Vite, Element Plus, Pinia, ECharts (Node.js 20+)
- **基础设施**: Docker, Docker Compose, Nginx

## 快速启动

### 开发环境（推荐）

```bash
# 1. 启动基础设施
docker compose up -d postgres redis

# 2. 后端
cd backend
cp .env.example .env
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Celery Worker（另开终端）
celery -A celery_worker worker --loglevel=info

# 3.5 Celery Beat 调度器（另开终端，用于定时 SLA 扫描等）
celery -A celery_worker beat --loglevel=info

# 4. 前端（另开终端，Node.js 20+）
cd frontend
npm install
npm run dev

# 5. 运行测试（可选）
# 后端测试
cd backend
pytest --cov=app --cov-report=term-missing
# 前端测试
cd frontend
npm run test
```

### 部署脚本

项目根目录提供 `deploy.sh`，封装了生产环境的标准部署流程：

```bash
# 一键构建并启动生产环境
./deploy.sh
```

该脚本默认执行：
1. 验证 `.env.production` 存在且非空
2. 检查关键变量是否已修改（非 `change-me`）
3. 拉取/构建最新镜像
4. 通过 `docker-compose.prod.yml` 启动服务
5. 执行数据库迁移（`alembic upgrade head`）
6. 健康检查轮询

更多部署细节请参考 `docs/deployment.md`。

### 生产环境（Docker Compose）

```bash
# 1. 准备生产环境变量
# 复制 .env.production 并修改密钥、密码等敏感项
# SECRET_KEY、POSTGRES_PASSWORD、WEBHOOK_SECRET 必须修改

# 2. 一键启动全部服务（使用生产编排文件）
docker compose -f docker-compose.prod.yml up -d --build

# 或使用部署脚本（推荐）
./deploy.sh
```

> 生产环境 `DEBUG=False`，API 文档（`/docs`）与健康检查（`/health`）**不对外暴露**。前端与 API 统一通过 Nginx 80 端口代理访问。

访问：
- 前端: http://localhost
- API 基础路径: `/api/v1`（通过 Nginx 反向代理）
- 开发环境 API 文档: http://localhost:8000/docs
- 开发环境健康检查: http://localhost:8000/health
- Nginx 健康检查: http://localhost/nginx-health

## 初始化配置与默认账户

系统首次启动时会自动创建默认管理员，并加载基础环境配置。以下为快速参考，**生产环境请务必修改所有默认值**。

### 默认管理员账户

后端服务启动时（`lifespan`）自动检查并创建：

| 字段 | 默认值 | 备注 |
|------|--------|------|
| 用户名 | `admin` | 若已存在则跳过创建 |
| 邮箱 | `admin@example.com` | — |
| 密码 | `admin123` | **生产环境必须立即修改** |
| 角色 | `admin` | 拥有全部权限 |

> 密码修改方式：生产环境首次登录后，**必须**直接更新数据库 `users` 表的 `password_hash` 字段（使用 bcrypt 哈希），或通过后端管理接口重置。前端暂无个人修改密码页面。

### 数据库连接信息

开发环境默认（`docker-compose.yml` / `backend/app/config.py`）：

```
主机: localhost (或 postgres 容器内)
端口: 5432
数据库: ticket_db
用户名: ticket_user
密码: ticket_pass
```

生产环境默认（`docker-compose.prod.yml` / `.env.production`）：

```
主机: postgres (容器网络内)
端口: 5432
数据库: ticket_db
用户名: ticket_user
密码: <见 .env.production 中 POSTGRES_PASSWORD>
```

### 完整环境变量清单

生产环境变量统一维护在 `.env.production`（**切勿提交到 Git**），完整变量如下：

| 变量 | 用途 | 默认值（`.env.production`） | 开发环境默认值（`.env.example`） | 是否必须修改 |
|------|------|---------------------------|--------------------------------|--------------|
| `SECRET_KEY` | JWT 签名密钥 | `change-me` | `change-me-in-development` | ✅ 必须 |
| `POSTGRES_PASSWORD` | 数据库密码 | `change-me` | `ticket_pass`（docker-compose） | ✅ 必须 |
| `WEBHOOK_SECRET` | Webhook 验签 | `change-me` | `webhook-secret-change-me` | ✅ 必须 |
| `APP_NAME` | 应用名称 | `Ticket System API` | `Ticket System API` | 按需调整 |
| `DEBUG` | 调试模式 | `False` | `True` | 生产环境保持 `False` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT 过期时间（分钟） | `60` | `480` | 按需调整 |
| `ALGORITHM` | JWT 签名算法 | `HS256` | `HS256` | 通常保持默认 |
| `FRONTEND_URL` | CORS 允许来源 | `http://localhost:80` | `http://localhost:5173` | 按需调整 |
| `EXPORT_DIR` | 报表导出目录 | `./exports` | `./exports` | 按需调整 |
| `CELERY_BROKER_URL` | Celery Broker (Redis) | `redis://redis:6379/1` | `redis://localhost:6379/1` | Docker 环境自动配置 |
| `CELERY_RESULT_BACKEND` | Celery 结果后端 (Redis) | `redis://redis:6379/2` | `redis://localhost:6379/2` | Docker 环境自动配置 |
| `EMAIL_DEFAULT_CATEGORY_CODE` | 邮件默认分类标识 | `email` | `email` | 按需调整 |
| `EMAIL_ALLOWED_DOMAINS` | 允许接收邮件的域名 | 空 | 空 | 按需调整 |
| `SMTP_*` | 邮件发送（`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`, `EMAIL_FROM`） | 空 | 空 | 启用 SMTP 时配置 |
| `EMAIL_API_*` | 第三方邮件 API（`EMAIL_API_PROVIDER`, `EMAIL_API_KEY`, `EMAIL_API_URL`） | 空 | 空 | 预留，未实现 |

> 确保 `.env.production` 已加入 `.gitignore`，避免密钥泄露。首次生产部署前，务必修改所有 `change-me` 占位值。

### `.env.production` 示例

以下是可直接复制使用的模板（**所有敏感值均为占位符，部署前必须替换**）：

```bash
# Ticket System — Production Environment Variables
# 首次部署前，必须将所有 change-me 替换为强随机值

# App
APP_NAME=Ticket System API
DEBUG=False

# JWT (必须修改！生产环境请使用强随机密钥)
SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# Frontend URL (用于 CORS 允许来源)
FRONTEND_URL=http://localhost:80

# Webhook
WEBHOOK_SECRET=change-me

# Database (Docker 部署时由 docker-compose.prod.yml 注入，本地非 Docker 部署时参考)
POSTGRES_PASSWORD=change-me
# DATABASE_URL=postgresql+asyncpg://ticket_user:change-me@localhost:5432/ticket_db
# REDIS_URL=redis://localhost:6379/0
# CELERY_BROKER_URL=redis://localhost:6379/1
# CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Reports
EXPORT_DIR=./exports

# Inbound Email
EMAIL_DEFAULT_CATEGORY_CODE=email
EMAIL_ALLOWED_DOMAINS=

# Outbound — SMTP (启用邮件通知时配置)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TLS=True
EMAIL_FROM=

# Outbound — HTTP API (预留，未实现)
EMAIL_API_PROVIDER=
EMAIL_API_KEY=
EMAIL_API_URL=
```

> 提示：`POSTGRES_PASSWORD` 在 Docker 部署时会被 `docker-compose.prod.yml` 读取并注入到数据库和 API 服务中。如果仅在本地运行后端（非 Docker），请取消注释 `DATABASE_URL` 等连接字符串并正确配置。

## 项目文档

- `PRD.md` — 产品需求文档
- `PROJECT_DOCS.md` — 项目总览（技术选型、架构图、目录结构）
- `TASKS.md` — 开发任务清单（按里程碑分组）
- `ARCHITECTURE.md` — 系统架构设计（数据模型、接口契约、状态机）
- `RISKS.md` — 风险清单与应对建议
- `testing-guidelines.md` — 测试设计规范（用例设计方法、优先级、命名体系）
- `docs/deployment.md` — 生产环境部署指南

## 开发规范

- 代码风格: `black` + `isort` + `flake8`
- 测试: `pytest`（目标覆盖率 ≥ 80%）
- 提交规范: Conventional Commits
- 分支策略: `main` 为生产分支，`feat/*` 为功能分支
