# Ticket System 生产部署指南

## 前置要求

- Docker Engine >= 24.0
- Docker Compose >= 2.20
- Linux / macOS / WSL2（Windows 推荐）

## 快速部署

```bash
# 1. 复制环境变量模板并配置
.env.production

# 2. 修改 SECRET_KEY 等敏感配置（必须！）
vim .env.production

# 3. 一键部署
chmod +x deploy.sh
./deploy.sh
```

部署完成后访问 http://localhost

## 手动部署（无脚本）

```bash
# 构建并启动
.env.production

# 首次启动（包含构建）
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 仅启动（已有镜像）
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 停止
docker compose -f docker-compose.prod.yml down

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker compose -f docker-compose.prod.yml logs -f api
```

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| SECRET_KEY | ✅ | — | JWT 签名密钥，至少 32 位随机字符串 |
| DEBUG | — | False | 生产环境必须为 False |
| FRONTEND_URL | — | http://localhost:80 | CORS 允许来源 |
| WEBHOOK_SECRET | — | — | 邮件 Webhook 验证密钥 |
| POSTGRES_USER | — | ticket_user | 数据库用户名 |
| POSTGRES_PASSWORD | ✅ | — | 数据库密码（必须修改） |
| POSTGRES_DB | — | ticket_db | 数据库名 |

## 服务架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   nginx     │────▶│  frontend   │     │   postgres  │
│  (80:80)    │     │  (静态文件)  │     │  (数据持久化) │
└─────────────┘     └─────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    api      │     │   worker    │     │    redis    │
│  (FastAPI)  │     │  (Celery)   │     │  (缓存/队列) │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 数据持久化

- **postgres_data**: PostgreSQL 数据卷
- **redis_data**: Redis 数据卷

清理数据（⚠️ 危险）：
```bash
docker compose -f docker-compose.prod.yml down -v
```

## 数据库迁移

后端容器启动时会自动运行 `alembic upgrade head`。如需手动迁移：

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## 日志管理

每个服务配置日志轮转：
- 单文件最大 10MB
- 保留 3 个文件

查看日志：
```bash
docker compose -f docker-compose.prod.yml logs -f [service_name]
```

## 安全加固

- 后端使用非 root 用户运行
- nginx 配置了安全响应头（X-Frame-Options, X-Content-Type-Options 等）
- 生产环境关闭 API 文档（DEBUG=False 时 /docs 和 /redoc 不可用）
- CORS 仅允许配置的 FRONTEND_URL

## 故障排查

| 现象 | 排查方法 |
|------|----------|
| 服务无法启动 | `docker compose -f docker-compose.prod.yml logs` |
| 数据库连接失败 | 检查 postgres 健康状态，确认环境变量正确 |
| 前端 404 | 确认 nginx 配置正确，检查前端构建输出 |
| 导出任务失败 | 检查 worker 日志和 redis 连接 |
| 性能问题 | 检查 postgres 和 redis 资源使用情况 |

## 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker compose -f docker-compose.prod.yml up -d --build
```

## 启用 HTTPS

1. 准备 SSL 证书（cert.pem 和 key.pem）
2. 修改 `docker-compose.prod.yml`，取消 443 端口注释
3. 修改 nginx 配置，添加 443 server 块和 SSL 配置
