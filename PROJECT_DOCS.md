# 在线客服工单系统 — 项目总览

---

## 一、技术选型

### 1.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10 | 运行时 |
| FastAPI | 0.110+ | Web 框架，自动 OpenAPI 文档 |
| SQLAlchemy | 2.0+ | ORM，数据库抽象 |
| Alembic | 1.13+ | 数据库迁移 |
| Pydantic | 2.0+ | 数据校验与序列化 |
| Celery | 5.3+ | 异步任务队列 |
| Redis | 7.x | Celery Broker + 缓存 |
| PostgreSQL | 15+ | 主数据库 |
| uvicorn | 0.27+ | ASGI 服务器 |
| pytest | 8.0+ | 测试框架 |
| httpx | 0.27+ | 异步 HTTP 客户端（测试/Webhook） |

### 1.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue3 | 3.4+ | 框架 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI 组件库 |
| Vue Router | 4.2+ | 路由 |
| Pinia | 2.1+ | 状态管理 |
| Axios | 1.6+ | HTTP 客户端 |
| ECharts | 5.4+ | 图表库 |

### 1.3 基础设施

| 技术 | 用途 |
|------|------|
| Docker | 容器化 |
| Docker Compose | 本地/测试环境编排 |
| Nginx | 反向代理、静态文件服务（生产） |

---

## 二、架构图描述

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web App    │  │  Email/Webhook│  │  3rd Party   │      │
│  │   (Vue3)     │  │   Provider   │  │    API       │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway (Nginx)                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│                    FastAPI (Python 3.10)                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Auth Module│ │ Ticket Mod │ │ Assign Mod │ │ SLA Mod  │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │ Stats Mod  │ │ Notify Mod │ │ Webhook Mod│ │ Admin Mod│ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐      ┌─────────────────────────────┐
│     Data Layer          │      │      Async Worker           │
│  ┌─────────────────┐    │      │  ┌─────────────────────┐    │
│  │   PostgreSQL    │    │      │  │    Celery Worker    │    │
│  │   (Primary DB)  │◄───┘      │  │  - SLA monitor      │    │
│  └─────────────────┘           │  │  - Email webhook    │    │
│  ┌─────────────────┐           │  │  - Report export    │    │
│  │      Redis      │◄──────────┘  │  - Notify sender    │    │
│  │ (Broker/Cache)  │              │  └─────────────────────┘    │
│  └─────────────────┘              └─────────────────────────────┘
└─────────────────────────┘
```

### 架构说明
- **无状态 API 服务**：FastAPI 应用层不保存会话状态，便于水平扩展。
- **异步任务解耦**：SLA 超时检查、邮件 Webhook 处理、报表导出等耗时操作交由 Celery Worker 处理。
- **数据一致性**：核心事务数据存储于 PostgreSQL；Redis 仅用于 Celery Broker 和短期缓存。

---

## 三、目录结构

```
ticket-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 配置管理（Pydantic Settings）
│   │   ├── database.py          # SQLAlchemy 引擎与 Session
│   │   ├── models/              # 数据库模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── ticket.py
│   │   │   ├── ticket_reply.py
│   │   │   ├── category.py
│   │   │   ├── agent_skill.py
│   │   │   ├── sla_record.py
│   │   │   ├── collaboration.py
│   │   │   ├── notification.py
│   │   │   ├── dispatch_log.py
│   │   │   └── email_ingestion.py
│   │   ├── schemas/             # Pydantic 校验模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── ticket.py
│   │   │   ├── ticket_reply.py
│   │   │   ├── category.py
│   │   │   ├── agent_skill.py
│   │   │   ├── sla.py
│   │   │   ├── collaboration.py
│   │   │   ├── notification.py
│   │   │   ├── dispatch.py
│   │   │   ├── report.py
│   │   │   └── ...
│   │   ├── routers/             # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── tickets.py
│   │   │   ├── categories.py
│   │   │   ├── collaborations.py
│   │   │   ├── dispatch.py
│   │   │   ├── sla.py
│   │   │   ├── notifications.py
│   │   │   ├── reports.py
│   │   │   ├── agent_skills.py
│   │   │   ├── sse.py
│   │   │   ├── webhooks.py
│   │   │   └── admin.py
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── ticket_service.py
│   │   │   ├── reply_service.py
│   │   │   ├── category_service.py
│   │   │   ├── agent_skill_service.py
│   │   │   ├── collaboration_service.py
│   │   │   ├── dispatch_service.py
│   │   │   ├── sla_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── report_service.py
│   │   │   ├── email_service.py
│   │   │   ├── mailer.py
│   │   │   └── user_service.py
│   │   ├── tasks/               # Celery 异步任务
│   │   │   ├── __init__.py
│   │   │   ├── sla_tasks.py
│   │   │   ├── notify_tasks.py
│   │   │   ├── export_tasks.py
│   │   │   └── email_tasks.py
│   │   ├── dependencies.py      # FastAPI Dependencies（鉴权等）
│   │   ├── exceptions.py        # 自定义异常
│   │   └── core/                # 核心工具
│   │       └── sse.py           # SSE 客户端管理
│   ├── alembic/                 # 数据库迁移
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_tickets.py
│   │   └── ...
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── celery_worker.py         # Celery Worker 启动入口
│
├── frontend/
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/              # Pinia
│   │   │   ├── index.js
│   │   │   ├── auth.js
│   │   │   ├── tickets.js
│   │   │   ├── dispatch.js
│   │   │   ├── notifications.js
│   │   │   ├── categories.js
│   │   │   ├── agentSkills.js
│   │   │   ├── sla.js
│   │   │   ├── reports.js
│   │   │   └── users.js
│   │   ├── views/               # 页面
│   │   │   ├── LoginView.vue
│   │   │   ├── customer/
│   │   │   │   ├── DashboardView.vue
│   │   │   │   ├── MyTicketsView.vue
│   │   │   │   ├── CreateTicketView.vue
│   │   │   │   └── TicketDetailView.vue
│   │   │   ├── agent/
│   │   │   │   ├── WorkbenchView.vue
│   │   │   │   ├── AgentTicketsView.vue
│   │   │   │   └── AgentTicketDetailView.vue
│   │   │   └── admin/
│   │   │       ├── UsersView.vue
│   │   │       ├── ReportsView.vue
│   │   │       ├── CategoriesView.vue
│   │   │       ├── AgentSkillsView.vue
│   │   │       ├── SLARulesView.vue
│   │   │       ├── AdminTicketsView.vue
│   │   │       └── AdminTicketDetailView.vue
│   │   ├── components/          # 公共组件
│   │   │   ├── StatusBadge.vue
│   │   │   ├── PriorityTag.vue
│   │   │   ├── ReplyBox.vue
│   │   │   ├── AssignSuggestionList.vue
│   │   │   └── NotificationBell.vue
│   │   ├── api/                 # Axios 封装
│   │   │   ├── index.js
│   │   │   ├── auth.js
│   │   │   ├── tickets.js
│   │   │   ├── categories.js
│   │   │   ├── sla.js
│   │   │   ├── agentSkills.js
│   │   │   ├── dispatch.js
│   │   │   ├── reports.js
│   │   │   ├── admin.js
│   │   │   └── notifications.js
│   │   └── utils/
│   ├── public/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.production
├── deploy.sh
├── nginx.conf
├── docs/
│   └── deployment.md
└── README.md
```

---

## 四、环境配置

### 4.1 开发环境

```bash
# 1. 克隆项目
cd ticket-system

# 2. 启动基础设施（PostgreSQL + Redis）
docker compose up -d postgres redis

# 3. 后端环境
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. 数据库迁移
alembic upgrade head

# 5. 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 6. 启动 Celery Worker（另开终端）
celery -A celery_worker worker --loglevel=info

# 6.5 启动 Celery Beat 调度器（另开终端，用于定时 SLA 扫描）
celery -A celery_worker beat --loglevel=info

# 7. 前端环境（另开终端）
cd ../frontend
npm install
npm run dev

# 8. 运行测试（可选）
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && npm run test
```

### 4.2 Docker Compose 配置（关键服务）

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| api | `ticket-system/backend` | 8000 | FastAPI 应用 |
| worker | `ticket-system/backend` | — | Celery Worker |
| beat | `ticket-system/backend` | — | Celery Beat 定时任务调度器 |
| web | `ticket-system/frontend` | 80 | Nginx + 静态文件 |
| postgres | `postgres:15-alpine` | 5432 | 主数据库 |
| redis | `redis:7-alpine` | 6379 | Broker/Cache |

### 4.3 环境变量（.env 示例）

```bash
# App
APP_NAME=Ticket System API
DEBUG=True

# Database
DATABASE_URL=postgresql+asyncpg://ticket_user:ticket_pass@postgres:5432/ticket_db

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=480
ALGORITHM=HS256

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Webhook
WEBHOOK_SECRET=webhook-signing-secret

# Reports
EXPORT_DIR=./exports

# Inbound Email
EMAIL_DEFAULT_CATEGORY_CODE=email
EMAIL_ALLOWED_DOMAINS=

# Outbound — SMTP (启用时配置)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TLS=True
EMAIL_FROM=
```

---

## 五、开发与交付规范

| 项 | 规范 |
|----|------|
| 代码风格 | Black + isort + flake8 |
| 类型注解 | 全部公共函数必须添加类型注解 |
| 测试覆盖 | 核心业务逻辑覆盖率 ≥ 80% |
| API 文档 | 自动生成 Swagger UI (`/docs`) |
| 提交规范 | Conventional Commits |
| 分支策略 | `main` 为生产分支，`feat/*` 为功能分支 |
