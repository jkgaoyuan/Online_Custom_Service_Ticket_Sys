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
