# 在线客服工单系统

> 前后端分离架构：后端 FastAPI + 前端 Vue3，容器化交付。

## 技术栈

- **后端**: Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL, Celery, Redis
- **前端**: Vue 3, Vite, Element Plus, Pinia, ECharts
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

# 4. 前端（另开终端）
cd frontend
npm install
npm run dev
```

### 生产环境（Docker Compose）

```bash
# 设置密钥
cp backend/.env.example backend/.env
# 编辑 backend/.env 修改 SECRET_KEY 和 WEBHOOK_SECRET

# 一键启动全部服务
docker compose up -d
```

访问：
- 前端: http://localhost
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

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

> 密码修改方式：登录后通过前端个人设置修改，或直接更新数据库 `users` 表的 `password_hash` 字段。

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

| 变量 | 用途 | 默认值示例 | 是否必须修改 |
|------|------|------------|--------------|
| `SECRET_KEY` | JWT 签名密钥 | `change-me` | ✅ 必须 |
| `POSTGRES_PASSWORD` | 数据库密码 | `change-me` | ✅ 必须 |
| `WEBHOOK_SECRET` | Webhook 验签 | `change-me` | ✅ 必须 |
| `APP_NAME` | 应用名称 | `Ticket System API` | 按需调整 |
| `DEBUG` | 调试模式 | `False` | 生产环境保持 `False` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT 过期时间（分钟） | `60` | 按需调整 |
| `ALGORITHM` | JWT 签名算法 | `HS256` | 通常保持默认 |
| `FRONTEND_URL` | CORS 允许来源 | `http://localhost:80` | 按需调整 |
| `SMTP_*` | 邮件发送（`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TLS`, `EMAIL_FROM`） | 空 | 启用邮件时配置 |

> `.env.production` 当前 Git 状态为已修改（`M`），请确认该文件已加入 `.gitignore`，避免密钥泄露。

## 项目文档

- `PRD.md` — 产品需求文档
- `PROJECT_DOCS.md` — 项目总览（技术选型、架构图、目录结构）
- `TASKS.md` — 开发任务清单（按里程碑分组）
- `ARCHITECTURE.md` — 系统架构设计（数据模型、接口契约、状态机）
- `RISKS.md` — 风险清单与应对建议

## 开发规范

- 代码风格: `black` + `isort` + `flake8`
- 测试: `pytest`（目标覆盖率 ≥ 80%）
- 提交规范: Conventional Commits
- 分支策略: `main` 为生产分支，`feat/*` 为功能分支
