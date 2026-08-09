# T005 邮件 Webhook 接入设计文档

> **版本**: v1.0  
> **日期**: 2026-08-09  
> **状态**: 已评审  
> **对应任务**: T005（邮件 Webhook 接入）

---

## 一、设计目标

实现工单系统的邮件渠道接入，覆盖：
- 接收外部邮件服务商（SendGrid / Mailgun / AWS SES 等）的 inbound webhook，将邮件转化为工单或工单回复
- 未知发件人进入 moderation queue，管理员审核后再创建用户和工单
- 搭建 Outbound 邮件发送的最小化封装，供后续通知模块复用

---

## 二、范围与边界

**包含（T005 范围）：**

| 模块 | 说明 |
|------|------|
| Webhook 接收端点 | `POST /webhooks/email`，Bearer Token 鉴权 |
| Celery 异步处理 | 解析邮件、用户查找、工单匹配、创建/回复 |
| Moderation Queue | `EmailIngestion` 模型 + Admin 审核 API |
| 工单匹配逻辑 | 双轨匹配：In-Reply-To → `email_message_id`，降级主题行 `ticket_no` 解析 |
| Outbound 封装 | `mailer.py` 最小化抽象（仅 SMTP backend） |
| 测试 | 后端 ≥12 条测试 |

**不包含（后续任务）：**
- 具体邮件服务商的原生签名适配（如 Mailgun HMAC、SendGrid RSA）
- HTTP API 发信 backend 的具体实现（SendGrid/Mailgun 接口填码）
- 通知触发逻辑（工单创建确认、回复通知等 Notify Mod 内容）
- 前端 Moderation Queue 管理页面

---

## 三、架构与数据流

```
邮件服务商 (SendGrid/Mailgun/SES)
         │
         ▼
POST /webhooks/email  ──►  FastAPI Router
    (Bearer 验签 + 入队)     (同步，立即返回 200)
         │
         ▼
    Celery Task (异步)
         │
         ├── 解析邮件 (from, to, subject, body, headers)
         ├── 查找用户
         │      ├── 已知用户 ──► 双轨匹配工单
         │      │              ├── 命中 ──► 创建 TicketReply
         │      │              └── 未命中 ──► 创建新 Ticket
         │      └── 未知用户 ──► 写入 EmailIngestion (pending)
         │
         └── 返回 200（吞掉所有异常）
```

**分层职责：**

| 文件 | 职责 |
|------|------|
| `routers/webhooks.py` | 接收 HTTP POST，验证 Bearer Token，将原始 payload 丢进 Celery |
| `tasks/email_tasks.py` | Celery 异步任务：解析、匹配、创建/回复/入队 |
| `services/email_service.py` | Inbound 业务逻辑：用户查找、工单双轨匹配、内容提取、moderation 入队 |
| `services/mailer.py` | Outbound 最小化封装：SMTP 异步发送 |
| `schemas/email_webhook.py` | Webhook payload Pydantic 模型 |

---

## 四、数据模型变更

### 4.1 `ticket_replies` — 增加 `email_message_id`

```python
email_message_id: Mapped[str | None] = mapped_column(
    String(100), nullable=True, unique=True, index=True
)
```

**用途：**
- 支撑邮件 threading（回复关联原始邮件）
- 幂等去重（同一封邮件被重复 webhook 回调时拦截）

### 4.2 `email_ingestions` — 新增 moderation queue 表

```python
class EmailIngestion(Base):
    __tablename__ = "email_ingestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_email: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    in_reply_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    ticket_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tickets.id"), nullable=True
    )
```

### 4.3 `categories` — 启动时自动创建默认分类

配置 `EMAIL_DEFAULT_CATEGORY_CODE: str = "email"`。系统在 lifespan 启动时检查是否存在 `code="email"` 的分类，若不存在则自动创建：

```python
Category(name="邮件工单", code="email", description="通过邮件渠道创建的工单", default_priority="P2")
```

确保邮件创建的工单 `category_id` 永远有合法值。

---

## 五、配置项扩展

```python
# app/config.py

# Inbound
WEBHOOK_SECRET: str = "webhook-secret-change-me"
EMAIL_DEFAULT_CATEGORY_CODE: str = "email"
EMAIL_ALLOWED_DOMAINS: list[str] = []  # 空列表表示不限制

# Outbound — SMTP
SMTP_HOST: str | None = None
SMTP_PORT: int = 587
SMTP_USER: str | None = None
SMTP_PASSWORD: str | None = None
SMTP_TLS: bool = True
EMAIL_FROM: str | None = None  # 系统发件地址，如 support@example.com

# Outbound — HTTP API（预留，MVP 不实现）
EMAIL_API_PROVIDER: str | None = None
EMAIL_API_KEY: str | None = None
EMAIL_API_URL: str | None = None
```

---

## 六、API 设计

### 6.1 Webhook 接收端点

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| `POST` | `/webhooks/email` | 接收邮件 webhook | `Authorization: Bearer {WEBHOOK_SECRET}` |

**行为约束：**
- 校验失败 → 返回 401
- 校验通过但处理中任何异常 → **始终返回 200**，内部错误记日志
- 防止服务商重试风暴

### 6.2 Webhook Payload Schema（通用抽象）

```python
class InboundEmail(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=100)
    from_address: EmailStr
    from_name: str | None = Field(None, max_length=100)
    to_address: EmailStr
    subject: str = Field(..., max_length=200)
    text_body: str | None = Field(None, max_length=50000)
    html_body: str | None = Field(None, max_length=200000)
    in_reply_to: str | None = Field(None, max_length=100)
    references: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
```

> 路由层负责将各服务商格式归一化为 `InboundEmail`。

### 6.3 Admin Moderation API

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| `GET` | `/admin/email-ingestion` | 列表（支持 `status` 筛选，默认 `pending`） | admin/supervisor |
| `POST` | `/admin/email-ingestion/{id}/approve` | 审核通过：创建 customer 用户 + 创建工单 + 回填 `EmailIngestion` | admin/supervisor |
| `POST` | `/admin/email-ingestion/{id}/reject` | 拒绝：更新 `status=rejected` | admin/supervisor |

**Approve 时的用户创建规则：**
- `username`：取 email 的 local-part（如 `john.doe@example.com` → `john.doe`）
- 冲突处理：若 `username` 已存在，追加 4 位随机小写字母（如 `john.doe_a3b2`），循环直到唯一
- `password`：`secrets.token_urlsafe(24)`，随机强密码
- `email`：直接使用 `sender_email`
- `role`：`customer`
- `is_active`：`True`

> 创建后不回显密码，管理员可通过现有用户管理接口后续重置。

---

## 七、工单匹配逻辑（双轨）

```python
async def match_ticket_by_email(db, inbound: InboundEmail) -> Ticket | None:
    # 轨道 1: In-Reply-To → Ticket.email_message_id
    if inbound.in_reply_to:
        ticket = await db.scalar(
            select(Ticket).where(Ticket.email_message_id == inbound.in_reply_to)
        )
        if ticket:
            return ticket

    # 轨道 2: 主题行正则提取 ticket_no
    ticket_no = extract_ticket_no_from_subject(inbound.subject)
    if ticket_no:
        ticket = await db.scalar(
            select(Ticket).where(Ticket.ticket_no == ticket_no)
        )
        if ticket:
            return ticket

    return None
```

**主题行正则规则：**
- 匹配模式：`TK-YYYYmmdd-XXXX`（anywhere in subject）
- 预处理：strip `Re:`、`Fwd:`、`[...]` 等常见前缀，collapse whitespace

---

## 八、内容安全

MVP **只存储纯文本**，不保留原始 HTML：
- 优先取 `text_body`
- 若 `text_body` 为空，用 `html2text`（或正则 strip tags）从 `html_body` 提取纯文本
- 入库前对文本做长度截断（`TicketReply.content` / `Ticket.description` 上限）

彻底规避 XSS 风险。

---

## 九、Outbound 发信封装（最小化）

`app/services/mailer.py` 提供统一接口：

```python
class Mailer:
    async def send_text_email(self, to: str, subject: str, body: str) -> None: ...
```

**Backend 选择逻辑：**
- `SMTP_HOST` 有值 → 使用 `aiosmtplib` 异步 SMTP 发送
- `EMAIL_API_PROVIDER` 有值 → 预留 HTTP API 调用结构（MVP 不填具体实现）
- 两者皆空 → 发信为 no-op，记 warning log

> T005 不实现通知触发逻辑，只提供发信基础设施。

---

## 十、错误处理与边界情况

| 场景 | 处理 |
|------|------|
| 重复 webhook（相同 `message_id`） | `EmailIngestion.message_id` / `TicketReply.email_message_id` 唯一约束拦截，Celery task 捕获 `IntegrityError`，返回 200 |
| 超大 payload | 路由层限制 `max_size=10MB`，超限返回 200 并丢弃 |
| 解析失败（必填字段缺失） | Pydantic ValidationError，路由层捕获，返回 200，记 error log |
| 任意处理异常 | Webhook handler 全局 try/except，吞掉异常，始终返回 200 |
| 已知用户但匹配不到工单 | 视为新工单创建 |
| 已知用户回复已关闭工单 | 正常创建 `TicketReply`，**不自动重开工单** |
| `EMAIL_ALLOWED_DOMAINS` 非空且发件人域名不在白名单 | 丢弃邮件，返回 200，记 info log |

---

## 十一、测试策略

目标：**后端 ≥12 条测试通过**。

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 Webhook 接收 | 3 | 有效 payload 创建工单、有效 payload 创建回复、未知发件人入 moderation queue |
| P0 安全 | 2 | 错误 Bearer token 返回 401、重复 message_id 幂等返回 200 |
| P0 解析 | 2 | 主题行提取 ticket_no、In-Reply-To 匹配 email_message_id |
| P1 边界 | 3 | 超大 payload 丢弃、HTML 转纯文本、缺失必填字段返回 200 |
| P1 Moderation | 2 | Admin approve 创建用户+工单、admin reject |

---

## 十二、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 接入方式 | 通用 Webhook + Bearer Token 鉴权 | 与具体服务商解耦，任何提供商或转发代理均可接入；原生签名适配留待后续 |
| 未知发件人 | Moderation Queue（`EmailIngestion`） | 避免无控制账户创建和工单垃圾；管理员审核后入库 |
| 异步处理 | Celery Task | 用户决策保留；为后续附件解析、外部分类等预留扩展空间 |
| 内容存储 | 仅纯文本 | 彻底规避 XSS，无需前端 sanitize |
| 工单匹配 | 双轨（In-Reply-To + 主题行） | In-Reply-To 最准确，主题行做容错兜底 |
| Outbound | 最小化 SMTP 封装 | 搭好基础设施，通知触发逻辑留到 Notify Mod |

---

## 十三、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| Webhook 路由 | `app/routers/` 无 webhooks.py | 新建 `app/routers/webhooks.py`，在 `main.py` include |
| Celery Worker | `celery_worker.py` | 新增 `app.tasks.email_tasks` 到 `include` |
| 主路由注册 | `app/main.py` | `app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])` |
| 默认分类 | `app/models/category.py` | lifespan 启动时自动创建 `code="email"` |
| 用户查找 | `app/models/user.py` | 复用 `email` 字段索引 |
| Ticket 创建 | `app/services/ticket_service.py` | 复用 `create_ticket`，传入 `source="email"` |
| 发信封装 | 无 | 新建 `app/services/mailer.py` |
