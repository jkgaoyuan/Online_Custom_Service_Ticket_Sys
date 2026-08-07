# 在线客服工单系统 — 架构设计文档

---

## 一、系统架构说明

### 1.1 设计原则
- **单一职责**：每个模块只负责一个明确的业务领域。
- **接口隔离**：模块间通过 Service 层和 RESTful API 交互，避免直接操作他人数据。
- **异步解耦**：非实时要求的功能（通知、报表、SLA 扫描）通过 Celery 异步处理。
- **数据驱动**：状态流转由数据库事务保证一致性，避免内存状态机。

### 1.2 核心模块职责

| 模块 | 职责 | 对外接口 |
|------|------|----------|
| Auth | 用户注册/登录/鉴权、角色权限校验 | JWT Middleware, `/api/v1/auth/*` |
| Ticket | 工单 CRUD、状态流转、附件管理 | `/api/v1/tickets/*` |
| Assignment | 自动分派算法、手动转派、负载查询 | `/api/v1/assignments/*` |
| SLA | SLA 规则匹配、超时计算、提醒触发 | Celery Task + `/api/v1/sla/*` |
| Notification | 站内通知、邮件通知发送 | Celery Task + `/api/v1/notifications/*` |
| Webhook | 接收邮件服务商推送，解析生成工单 | `/api/v1/webhooks/email` |
| Stats | 聚合查询、报表生成、数据导出 | `/api/v1/stats/*` |
| Admin | 用户/分类/技能/SLA 规则配置 | `/api/v1/admin/*` |

---

## 二、数据模型

### 2.1 ER 图核心实体

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    User     │       │   Ticket    │       │   Category  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──┐    │ id (PK)     │──┐    │ id (PK)     │
│ username    │  │    │ title       │  │    │ name        │
│ email       │  │    │ description │  │    │ code        │
│ password_hash│  │    │ status      │  └───┤ default_priority│
│ role        │  │    │ priority    │       │ sla_config  │
│ is_active   │  │    │ category_id │       └─────────────┘
│ created_at  │  │    │ requester_id│◄──────┐
└─────────────┘  │    │ assignee_id │◄───┐  │
                 │    │ source      │    │  │
                 │    │ created_at  │    │  │
                 │    │ updated_at  │    │  │
                 │    │ resolved_at │    │  │
                 │    │ closed_at   │    │  │
                 │    │ satisfaction│    │  │
                 │    └─────────────┘    │  │
                 │            │          │  │
                 │            ▼          │  │
                 │    ┌─────────────┐    │  │
                 │    │ TicketReply │    │  │
                 │    ├─────────────┤    │  │
                 │    │ id (PK)     │    │  │
                 │    │ ticket_id   │    │  │
                 │    │ author_id   │◄───┘  │
                 │    │ content     │       │
                 │    │ is_internal │       │
                 │    │ created_at  │       │
                 │    └─────────────┘       │
                 │                          │
                 │    ┌─────────────┐       │
                 │    │  SLARecord  │       │
                 │    ├─────────────┤       │
                 │    │ id (PK)     │       │
                 │    │ ticket_id   │       │
                 │    │ priority    │       │
                 │    │ first_resp_due      │
                 │    │ resolution_due      │
                 │    │ first_resp_at       │
                 │    │ resolved_at         │
                 │    │ is_breached         │
                 │    └─────────────┘       │
                 │                          │
                 └────►┌─────────────┐      │
                       │  UserSkill  │◄─────┘
                       ├─────────────┤
                       │ id (PK)     │
                       │ user_id     │
                       │ category_id │
                       │ proficiency │
                       └─────────────┘
```

### 2.2 核心表结构定义

#### `users` — 用户表
```sql
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    email           VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('customer','agent','supervisor','admin')),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `categories` — 工单分类表
```sql
CREATE TABLE categories (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(50) NOT NULL,
    code                VARCHAR(30) NOT NULL UNIQUE,
    description         VARCHAR(255),
    default_priority    VARCHAR(10) NOT NULL CHECK (default_priority IN ('P0','P1','P2','P3')),
    sla_config          JSONB NOT NULL,  -- {first_resp_hours: 1, resolution_hours: 24}
    is_active           BOOLEAN DEFAULT TRUE
);
```

#### `tickets` — 工单表
```sql
CREATE TABLE tickets (
    id              SERIAL PRIMARY KEY,
    ticket_no       VARCHAR(20) NOT NULL UNIQUE,  -- TK-20260807-0001
    title           VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','in_progress','waiting','resolved','closed')),
    priority        VARCHAR(10) NOT NULL DEFAULT 'P2'
                        CHECK (priority IN ('P0','P1','P2','P3')),
    category_id     INTEGER NOT NULL REFERENCES categories(id),
    requester_id    INTEGER NOT NULL REFERENCES users(id),
    assignee_id     INTEGER REFERENCES users(id),
    source          VARCHAR(20) NOT NULL CHECK (source IN ('web','email','api')),
    email_message_id VARCHAR(100),  -- 邮件来源时记录原始 Message-ID
    satisfaction    VARCHAR(20) CHECK (satisfaction IN ('satisfied','neutral','dissatisfied')),
    satisfaction_note TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP,
    closed_at       TIMESTAMP
);
CREATE INDEX idx_tickets_assignee ON tickets(assignee_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
```

#### `ticket_replies` — 工单回复表
```sql
CREATE TABLE ticket_replies (
    id              SERIAL PRIMARY KEY,
    ticket_id       INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author_id       INTEGER NOT NULL REFERENCES users(id),
    content         TEXT NOT NULL,
    is_internal     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_replies_ticket ON ticket_replies(ticket_id);
```

#### `user_skills` — 客服技能表（用于分派）
```sql
CREATE TABLE user_skills (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    proficiency     INTEGER NOT NULL DEFAULT 1 CHECK (proficiency BETWEEN 1 AND 5),
    max_tickets     INTEGER NOT NULL DEFAULT 10,  -- 该分类最大并发处理数
    UNIQUE(user_id, category_id)
);
```

#### `sla_records` — SLA 执行记录表
```sql
CREATE TABLE sla_records (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
    priority            VARCHAR(10) NOT NULL,
    first_resp_hours    INTEGER NOT NULL,
    resolution_hours    INTEGER NOT NULL,
    first_resp_due      TIMESTAMP NOT NULL,
    resolution_due      TIMESTAMP NOT NULL,
    first_resp_at       TIMESTAMP,
    resolved_at         TIMESTAMP,
    first_resp_breached BOOLEAN DEFAULT FALSE,
    resolution_breached BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_sla_due ON sla_records(resolution_due) WHERE resolution_breached = FALSE;
```

---

## 三、接口契约

### 3.1 认证相关

#### POST `/api/v1/auth/login`
**Request:**
```json
{
  "username": "agent001",
  "password": "SecurePass123!"
}
```
**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 28800,
  "user": {
    "id": 1,
    "username": "agent001",
    "role": "agent"
  }
}
```

#### GET `/api/v1/auth/me`
**Response (200):**
```json
{
  "id": 1,
  "username": "agent001",
  "email": "agent@company.com",
  "role": "agent",
  "permissions": ["ticket:read", "ticket:reply", "ticket:transfer"]
}
```

### 3.2 工单相关

#### POST `/api/v1/tickets` — 创建工单
**Request:**
```json
{
  "title": "无法登录账户",
  "description": "点击登录按钮后页面无响应...",
  "category_id": 2,
  "priority": "P1",
  "source": "web"
}
```
**Response (201):**
```json
{
  "id": 15,
  "ticket_no": "TK-20260807-0015",
  "title": "无法登录账户",
  "status": "open",
  "priority": "P1",
  "category_id": 2,
  "requester_id": 5,
  "assignee_id": null,
  "created_at": "2026-08-07T10:30:00Z"
}
```

#### GET `/api/v1/tickets` — 工单列表
**Query Params:** `status`, `priority`, `category_id`, `assignee_id`, `page`, `page_size`

**Response (200):**
```json
{
  "total": 156,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 15,
      "ticket_no": "TK-20260807-0015",
      "title": "无法登录账户",
      "status": "open",
      "priority": "P1",
      "category": {"id": 2, "name": "故障报告"},
      "requester": {"id": 5, "username": "customer01"},
      "assignee": null,
      "created_at": "2026-08-07T10:30:00Z",
      "sla": {
        "first_resp_due": "2026-08-07T11:30:00Z",
        "resolution_due": "2026-08-08T10:30:00Z",
        "first_resp_breached": false
      }
    }
  ]
}
```

#### GET `/api/v1/tickets/{id}` — 工单详情
**Response (200):** 包含工单完整信息 + replies 列表 + 协作历史

#### POST `/api/v1/tickets/{id}/replies` — 回复工单
**Request:**
```json
{
  "content": "请尝试清除浏览器缓存后重新登录...",
  "is_internal": false
}
```

#### POST `/api/v1/tickets/{id}/assign` — 分派/转派
**Request:**
```json
{
  "assignee_id": 3,
  "note": "转交给技术支持组处理"
}
```

#### POST `/api/v1/tickets/{id}/close` — 关闭工单
**Request:**
```json
{
  "resolution_note": "问题已解决，客户确认可登录"
}
```

#### POST `/api/v1/tickets/{id}/satisfaction` — 提交评价
**Request:**
```json
{
  "satisfaction": "satisfied",
  "note": "问题解决很快，谢谢！"
}
```

### 3.3 统计相关

#### GET `/api/v1/stats/overview`
**Response (200):**
```json
{
  "today_new": 45,
  "today_resolved": 38,
  "open_count": 12,
  "overdue_count": 2,
  "avg_first_resp_minutes": 18.5,
  "avg_resolution_hours": 4.2,
  "satisfaction_rate": 0.92
}
```

#### GET `/api/v1/stats/agents`
**Query Params:** `start_date`, `end_date`

**Response (200):**
```json
{
  "items": [
    {
      "agent_id": 3,
      "agent_name": "客服小王",
      "ticket_count": 56,
      "resolved_count": 52,
      "avg_first_resp_minutes": 15.2,
      "avg_resolution_hours": 3.8,
      "satisfaction_rate": 0.95
    }
  ]
}
```

#### GET `/api/v1/stats/export`
**Query Params:** `type` (tickets|agents|categories), `format` (csv|xlsx), `start_date`, `end_date`

**Response:** `Content-Type: application/octet-stream`（文件下载）

### 3.4 Webhook 相关

#### POST `/api/v1/webhooks/email`
**Request Headers:** `X-Webhook-Signature: <hmac-sha256>`

**Request Body (由邮件服务商推送):**
```json
{
  "from": "customer@example.com",
  "to": "support@company.com",
  "subject": "无法登录账户",
  "text_body": "点击登录按钮后页面无响应...",
  "message_id": "<abc123@example.com>",
  "attachments": []
}
```
**Response (200):** `{"ticket_id": 16, "ticket_no": "TK-20260807-0016"}`

---

## 四、状态机设计

工单状态流转规则：

```
                    ┌─────────────┐
         ┌─────────►│    open     │◄────────┐
         │          │   (新建)     │         │
         │          └──────┬──────┘         │
    客户回复               │                 │
         │          ┌──────▼──────┐         │
         └──────────┤ in_progress │         │
                    │   (处理中)   │         │
                    └──────┬──────┘         │
                           │                │
              需客户补充    │    直接解决     │
                           │                │
              ┌────────────┼────────────┐   │
              ▼            ▼            ▼   │
        ┌─────────┐  ┌─────────┐  ┌────────┐│
        │ waiting │  │resolved │  │ closed ││
        │等待回复  │  │ 已解决   │  │ 已关闭  │┘
        └────┬────┘  └────┬────┘  └────────┘
             │            │
             └────────────┘
                  客户确认/超时自动关闭
```

**规则说明：**
- `open` → `in_progress`: 客服首次回复或主管分派时自动流转
- `in_progress` → `waiting`: 客服回复中要求客户提供更多信息
- `waiting` → `in_progress`: 客户追加回复后自动回到处理中
- `in_progress` → `resolved`: 客服标记已解决
- `resolved` → `closed`: 客户评价后，或 72 小时无反馈自动关闭
- `resolved` / `waiting` → `open`: 客户追加不满意反馈时可重新打开（配置项）
