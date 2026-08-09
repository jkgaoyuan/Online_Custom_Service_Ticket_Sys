# T006 SLA 管理与超时监控实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现工单系统的 SLA（服务等级协议）监控与提醒机制，包括 SLA 记录自动生成、分阶段预警通知、超时标记和可复用的站内通知基础设施。

**Architecture:** 在工单创建时由 `ticket_service` 内部调用 `sla_service` 生成 SLA 记录；Celery Beat 每 5 分钟扫描即将超时和已超时的 SLA 记录，通过 `notification_service` 写入站内通知；通知 API 支持用户查询和标记已读。

**Tech Stack:** FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic + Celery + Redis + pytest-asyncio

## Global Constraints

- Python 3.10.10，pytest 使用 `-p no:anyio` 运行（禁用 anyio 插件避免事件循环冲突）
- 数据库字段名和模型名使用 snake_case；API 路径使用 kebab-case
- SLA 时间使用自然时间（24/7 日历小时），`datetime.utcnow()` 基准
- `Category.sla_config` 新数据使用 nested 格式 `{"P0": {"first_resp_hours": 1, "resolution_hours": 4}}`，旧 flat 格式需兼容
- `celery_worker.py` 已包含 `"app.tasks.sla_tasks"`，只需补充 `beat_schedule`
- 通知表使用 `JSONB`（`from sqlalchemy.dialects.postgresql import JSONB`）
- `create_ticket()` 自行 `db.commit()`；`create_sla_record()` 在其内部 commit 前调用，不自行 flush/commit
- `create_reply()` 当前签名为 `(db, ticket, data, author_id)`；Task 2 扩展为 `(db, ticket, data, author_id, is_agent_reply=False)`
- `transition_ticket_status()` 当前在 `ticket_service.py`；Task 2 扩展 resolved/reopen 逻辑
- 扫描任务使用 `SELECT ... FOR UPDATE` + `selectinload(SLARecord.ticket)` 防止竞态和 N+1
- 预警 flag 仅在 `notify_sla_warning()` 返回 `True`（至少一条通知成功创建）后置位
- 测试目标 ≥14 条后端测试全部通过
- 每次 commit 前运行 `pytest -p no:anyio tests/`

---

## File Structure

| 文件 | 职责 |
|------|------|
| `backend/app/models/sla_record.py` | SLA 执行记录模型 |
| `backend/app/models/notification.py` | 站内通知模型 |
| `backend/app/services/sla_service.py` | SLA 规则引擎：创建记录、查询、配置解析、时间捕获辅助 |
| `backend/app/services/notification_service.py` | 通知 CRUD：创建、查询未读、标记已读 |
| `backend/app/tasks/sla_tasks.py` | Celery 扫描任务 + 预警/超时通知发送 |
| `backend/app/routers/notifications.py` | 通知 REST API |
| `backend/app/routers/sla.py` | SLA 查询 API（工单 SLA 详情、admin 超时列表） |
| `backend/app/schemas/sla.py` | SLA 相关 Pydantic schema |
| `backend/app/schemas/notification.py` | 通知相关 Pydantic schema |
| `backend/alembic/versions/xxxx_add_sla_and_notification_tables.py` | Alembic 迁移：新增两表 + category.sla_config JSON→JSONB |
| `backend/tests/test_sla.py` | SLA 引擎和 API 测试 |
| `backend/tests/test_notifications.py` | 通知服务和 API 测试 |
| `backend/tests/test_sla_tasks.py` | Celery 扫描任务测试 |

**修改的现有文件：**
- `backend/app/models/__init__.py` — 导入新模型
- `backend/app/services/ticket_service.py` — `create_ticket()` 调用 `create_sla_record()`；`transition_ticket_status()` 扩展 resolved/reopen 逻辑
- `backend/app/services/reply_service.py` — `create_reply()` 扩展 `is_agent_reply`，设置 `first_resp_at`
- `backend/app/routers/tickets.py` — 回复路由传入 `is_agent_reply`；详情/列表嵌入 SLA 摘要
- `backend/app/schemas/ticket.py` — `TicketResponse` 增加 `sla` 字段
- `backend/app/schemas/category.py` — `CategoryBase.sla_config` 改为 nested 格式
- `backend/app/main.py` — include `notifications` 和 `sla` routers
- `backend/celery_worker.py` — 增加 `beat_schedule`

---

### Task 1: 数据模型与数据库迁移

**Files:**
- Create: `backend/app/models/sla_record.py`
- Create: `backend/app/models/notification.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/xxxx_add_sla_and_notification_tables.py`
- Test: `backend/tests/test_sla.py`（迁移验证 + 模型实例化）

**Interfaces:**
- Consumes: `app.database.Base`, existing `Ticket` model
- Produces: `SLARecord` model, `Notification` model, Alembic migration runnable via `alembic upgrade head`

- [ ] **Step 1: Create `sla_record.py` model**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SLARecord(Base):
    __tablename__ = "sla_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    first_resp_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    first_resp_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    first_resp_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_resp_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    first_resp_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)

    ticket: Mapped["Ticket"] = relationship("Ticket")
```

- [ ] **Step 2: Create `notification.py` model**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 3: Update `models/__init__.py`**

```python
from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.dispatch_log import DispatchLog
from app.models.email_ingestion import EmailIngestion
from app.models.notification import Notification
from app.models.sla_record import SLARecord
from app.models.user import User
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
```

- [ ] **Step 4: Write Alembic migration**

Migration 需完成三件事：
1. 创建 `sla_records` 表（含两个索引）
2. 创建 `notifications` 表（含一个索引）
3. 将 `categories.sla_config` 从 `JSON` 改为 `JSONB`，并将现有 flat 数据升级为 nested

在 `backend/alembic/versions/` 下新建文件（手动指定 revision id）：

```python
"""add sla_records and notifications tables, migrate sla_config to jsonb

Revision ID: 7b8c9d0e1f2a
Revises: 6a1b2c3d4e5f
Create Date: 2026-08-09 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, None] = "6a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. create sla_records
    op.create_table(
        "sla_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("first_resp_hours", sa.Integer(), nullable=False),
        sa.Column("resolution_hours", sa.Integer(), nullable=False),
        sa.Column("first_resp_due", sa.DateTime(), nullable=False),
        sa.Column("resolution_due", sa.DateTime(), nullable=False),
        sa.Column("first_resp_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("first_resp_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolution_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_resp_warned_agent_3h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_resp_warned_agent_2h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_resp_warned_supervisor_1h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolution_warned_agent_3h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolution_warned_agent_2h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolution_warned_supervisor_1h", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id"),
    )
    op.create_index("idx_sla_due", "sla_records", ["resolution_due"], postgresql_where=sa.text("resolution_breached = false"))
    op.create_index("idx_first_resp_due", "sla_records", ["first_resp_due"], postgresql_where=sa.text("first_resp_breached = false"))

    # 2. create notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notifications_user_unread", "notifications", ["user_id", "is_read"], postgresql_where=sa.text("is_read = false"))

    # 3. migrate categories.sla_config from JSON to JSONB and upgrade flat data
    #    First alter column type
    op.alter_column("categories", "sla_config",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="sla_config::jsonb",
        existing_nullable=False,
        existing_server_default=sa.text("'{}'"),
    )
    #    Then data migration: if flat format detected, wrap into all priorities
    op.execute("""
        UPDATE categories
        SET sla_config = jsonb_build_object(
            'P0', jsonb_build_object('first_resp_hours', (sla_config->>'first_resp_hours')::int, 'resolution_hours', (sla_config->>'resolution_hours')::int),
            'P1', jsonb_build_object('first_resp_hours', (sla_config->>'first_resp_hours')::int, 'resolution_hours', (sla_config->>'resolution_hours')::int),
            'P2', jsonb_build_object('first_resp_hours', (sla_config->>'first_resp_hours')::int, 'resolution_hours', (sla_config->>'resolution_hours')::int),
            'P3', jsonb_build_object('first_resp_hours', (sla_config->>'first_resp_hours')::int, 'resolution_hours', (sla_config->>'resolution_hours')::int)
        )
        WHERE sla_config ? 'first_resp_hours' AND NOT sla_config ? 'P0'
    """)


def downgrade() -> None:
    op.drop_index("idx_notifications_user_unread", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_first_resp_due", table_name="sla_records")
    op.drop_index("idx_sla_due", table_name="sla_records")
    op.drop_table("sla_records")
    op.alter_column("categories", "sla_config",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.JSON(),
        postgresql_using="sla_config::json",
        existing_nullable=False,
        existing_server_default=sa.text("'{}'"),
    )
```

> **注意**：revision id `7b8c9d0e1f2a` 为示例，实际使用 `alembic revision --autogenerate` 或手动生成唯一 id。`down_revision` 必须指向当前 head（`6a1b2c3d4e5f`）。如果 autogenerate 生成的迁移缺少数据迁移 SQL，需手动补充 Step 4 中的 `op.execute` 块。

- [ ] **Step 5: Write failing test for model instantiation**

```python
# backend/tests/test_sla.py
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash


async def _create_category(db, sla_config=None):
    category = Category(name="故障", code="bug", default_priority="P2", sla_config=sla_config or {})
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _create_user(db, username, role="customer"):
    user = User(username=username, email=f"{username}@example.com", password_hash=get_password_hash("Pass1234"), role=role, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# SLA-001: SLARecord can be created directly
async def test_sla_record_model(db):
    customer = await _create_user(db, "sla_customer")
    category = await _create_category(db)
    data = TicketCreate(title="test", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    record = SLARecord(
        ticket_id=ticket.id,
        priority="P1",
        first_resp_hours=2,
        resolution_hours=8,
        first_resp_due=datetime.utcnow() + timedelta(hours=2),
        resolution_due=datetime.utcnow() + timedelta(hours=8),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    fetched = result.scalar_one()
    assert fetched.priority == "P1"
    assert fetched.first_resp_hours == 2
    assert fetched.resolution_hours == 8
    assert fetched.first_resp_breached is False
```

- [ ] **Step 6: Run test to verify it fails (model exists but not imported)**

Run: `pytest -p no:anyio tests/test_sla.py::test_sla_record_model -v`
Expected: FAIL with `SLARecord not defined` if model not yet in `__init__.py` or import error

- [ ] **Step 7: Verify models/__init__.py import is correct, re-run**

Run: `pytest -p no:anyio tests/test_sla.py::test_sla_record_model -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/sla_record.py backend/app/models/notification.py backend/app/models/__init__.py backend/alembic/versions/7b8c9d0e1f2a_add_sla_and_notification_tables.py backend/tests/test_sla.py
git commit -m "feat(t006): add SLARecord and Notification models with migration"
```

---

### Task 2: SLA 规则引擎与现有服务集成

**Files:**
- Create: `backend/app/services/sla_service.py`
- Modify: `backend/app/services/ticket_service.py`
- Modify: `backend/app/services/reply_service.py`
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/app/schemas/category.py`
- Test: `backend/tests/test_sla.py`（扩展）

**Interfaces:**
- Consumes: `Category.sla_config` (nested or flat), `Ticket` model
- Produces:
  - `create_sla_record(db, ticket) -> SLARecord`
  - `get_sla_record_by_ticket_id(db, ticket_id) -> SLARecord | None`
  - `DEFAULT_SLA: dict`
  - `create_ticket()` 内部自动创建 SLA
  - `create_reply()` 新增 `is_agent_reply` 参数
  - `transition_ticket_status()` 处理 `resolved_at` 和 reopen 清空

- [ ] **Step 1: Create `sla_service.py`**

```python
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket

DEFAULT_SLA = {
    "P0": {"first_resp_hours": 1, "resolution_hours": 4},
    "P1": {"first_resp_hours": 4, "resolution_hours": 24},
    "P2": {"first_resp_hours": 8, "resolution_hours": 48},
    "P3": {"first_resp_hours": 24, "resolution_hours": 72},
}


def _resolve_sla_config(category_sla_config: dict, priority: str) -> dict:
    """从 category.sla_config 解析出指定优先级的 SLA 配置。兼容旧版 flat 格式。"""
    sla_config = category_sla_config or {}
    # 旧版 flat 格式检测：存在顶层 first_resp_hours 且不存在 P0
    if "first_resp_hours" in sla_config and "P0" not in sla_config:
        return {
            "first_resp_hours": sla_config["first_resp_hours"],
            "resolution_hours": sla_config["resolution_hours"],
        }
    return sla_config.get(priority, DEFAULT_SLA[priority])


async def create_sla_record(db: AsyncSession, ticket: Ticket) -> SLARecord:
    """在 create_ticket 内部调用，ticket 已 flush 有 id。不自行 commit。"""
    cat_result = await db.execute(select(Category).where(Category.id == ticket.category_id))
    category = cat_result.scalar_one()

    priority_config = _resolve_sla_config(category.sla_config, ticket.priority)
    now = datetime.utcnow()

    record = SLARecord(
        ticket_id=ticket.id,
        priority=ticket.priority,
        first_resp_hours=priority_config["first_resp_hours"],
        resolution_hours=priority_config["resolution_hours"],
        first_resp_due=now + timedelta(hours=priority_config["first_resp_hours"]),
        resolution_due=now + timedelta(hours=priority_config["resolution_hours"]),
    )
    db.add(record)
    return record


async def get_sla_record_by_ticket_id(db: AsyncSession, ticket_id: int) -> SLARecord | None:
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket_id))
    return result.scalar_one_or_none()
```

- [ ] **Step 2: Modify `ticket_service.py` — `create_ticket()` 调用 `create_sla_record()`**

在 `backend/app/services/ticket_service.py` 顶部增加导入：
```python
from app.services.sla_service import create_sla_record
```

修改 `create_ticket()`：
```python
async def create_ticket(
    db: AsyncSession, data: TicketCreate, requester_id: int
) -> Ticket:
    ticket_no = await generate_ticket_no(db)
    ticket = Ticket(
        ticket_no=ticket_no,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        priority=data.priority,
        requester_id=requester_id,
        assignee_id=data.assignee_id,
        source=data.source,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    # 创建 SLA 记录（ticket 已有 id）
    await create_sla_record(db, ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

> **说明**：虽然设计文档建议在 `db.flush()` 后、`db.commit()` 前调用，但现有 `create_ticket()` 已经 `commit` 了。为了不破坏现有所有调用方的契约，我们在 `commit` 之后、第二次 `commit` 之前创建 SLA。这会产生额外一次 commit，但保持了兼容性。T006 实施期间不可修改 `create_ticket()` 的首次 commit 位置，否则所有现有测试会断。

- [ ] **Step 3: Modify `ticket_service.py` — `transition_ticket_status()` 扩展 resolved/reopen 逻辑**

在 `backend/app/services/ticket_service.py` 顶部增加导入：
```python
from app.services.sla_service import get_sla_record_by_ticket_id
```

修改 `transition_ticket_status()`：
```python
async def transition_ticket_status(db: AsyncSession, ticket: Ticket, target_status: str) -> Ticket:
    if not can_transition(ticket.status, target_status):
        raise DuplicateException(f"无法从 {ticket.status} 流转到 {target_status}")

    old_status = ticket.status
    ticket.status = target_status

    if target_status == "resolved":
        ticket.resolved_at = datetime.utcnow()
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla and sla.resolved_at is None:
            sla.resolved_at = datetime.utcnow()

    if target_status == "closed":
        ticket.closed_at = datetime.utcnow()

    # 重新打开：清空 resolved_at，让其继续受 resolution SLA 约束
    if old_status == "resolved" and target_status == "in_progress":
        ticket.resolved_at = None
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla:
            sla.resolved_at = None

    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 4: Modify `reply_service.py` — 扩展 `is_agent_reply`，设置 `first_resp_at`**

在 `backend/app/services/reply_service.py` 顶部增加导入：
```python
from datetime import datetime
from app.services.sla_service import get_sla_record_by_ticket_id
```

修改 `create_reply()`：
```python
async def create_reply(db: AsyncSession, ticket: Ticket, data: ReplyCreate, author_id: int, is_agent_reply: bool = False) -> TicketReply:
    reply = TicketReply(ticket_id=ticket.id, author_id=author_id, content=data.content, is_internal=data.is_internal)
    db.add(reply)
    await db.commit()
    await db.refresh(reply)

    if is_agent_reply:
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla and sla.first_resp_at is None:
            sla.first_resp_at = datetime.utcnow()
            await db.commit()

    return reply
```

- [ ] **Step 5: Modify `routers/tickets.py` — 回复路由传入 `is_agent_reply`**

在 `reply_ticket` 函数中，找到 `reply = await create_reply(...)` 一行，替换为：
```python
    is_agent_reply = current_user.role in ("agent", "supervisor", "admin") and not data.is_internal
    reply = await create_reply(db, ticket, data, current_user.id, is_agent_reply=is_agent_reply)
```

- [ ] **Step 6: Modify `schemas/category.py` — `sla_config` 改为 nested 格式**

```python
class CategoryBase(BaseModel):
    name: str = Field(..., max_length=50)
    code: str = Field(..., max_length=30)
    description: Optional[str] = Field(None, max_length=255)
    default_priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    sla_config: dict = Field(
        default_factory=lambda: {
            "P0": {"first_resp_hours": 1, "resolution_hours": 4},
            "P1": {"first_resp_hours": 4, "resolution_hours": 24},
            "P2": {"first_resp_hours": 8, "resolution_hours": 48},
            "P3": {"first_resp_hours": 24, "resolution_hours": 72},
        }
    )
    is_active: bool = True
```

- [ ] **Step 7: Write failing tests**

```python
# backend/tests/test_sla.py 追加

# SLA-002: create_ticket 自动生成 SLA 记录
async def test_create_ticket_auto_creates_sla(db):
    customer = await _create_user(db, "sla_customer2")
    category = await _create_category(db, sla_config={"P1": {"first_resp_hours": 2, "resolution_hours": 8}})
    data = TicketCreate(title="auto sla", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.first_resp_hours == 2
    assert record.resolution_hours == 8
    assert record.first_resp_due > datetime.utcnow()
    assert record.resolution_due > record.first_resp_due


# SLA-003: 分类无配置时使用 DEFAULT_SLA
async def test_create_ticket_uses_default_sla_when_category_empty(db):
    customer = await _create_user(db, "sla_customer3")
    category = await _create_category(db, sla_config={})
    data = TicketCreate(title="default sla", description="desc", category_id=category.id, priority="P0")
    ticket = await create_ticket(db, data, customer.id)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.first_resp_hours == 1
    assert record.resolution_hours == 4


# SLA-004: 旧版 flat sla_config 兼容
async def test_create_ticket_compat_flat_sla_config(db):
    customer = await _create_user(db, "sla_customer4")
    category = await _create_category(db, sla_config={"first_resp_hours": 5, "resolution_hours": 10})
    data = TicketCreate(title="compat", description="desc", category_id=category.id, priority="P2")
    ticket = await create_ticket(db, data, customer.id)

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.first_resp_hours == 5
    assert record.resolution_hours == 10


# SLA-005: agent 首次回复记录 first_resp_at
async def test_agent_reply_sets_first_resp_at(db):
    from app.services.reply_service import create_reply
    from app.schemas.ticket_reply import ReplyCreate

    customer = await _create_user(db, "sla_customer5")
    agent = await _create_user(db, "sla_agent", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="reply", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    reply_data = ReplyCreate(content="hello", is_internal=False)
    reply = await create_reply(db, ticket, reply_data, agent.id, is_agent_reply=True)
    assert reply is not None

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.first_resp_at is not None


# SLA-006: 内部备注不记录 first_resp_at
async def test_internal_reply_does_not_set_first_resp_at(db):
    from app.services.reply_service import create_reply
    from app.schemas.ticket_reply import ReplyCreate

    customer = await _create_user(db, "sla_customer6")
    agent = await _create_user(db, "sla_agent2", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="internal", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    reply_data = ReplyCreate(content="internal note", is_internal=True)
    reply = await create_reply(db, ticket, reply_data, agent.id, is_agent_reply=False)
    assert reply is not None

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.first_resp_at is None


# SLA-007: resolved 时记录 resolved_at
async def test_transition_to_resolved_sets_resolved_at(db):
    from app.services.ticket_service import transition_ticket_status

    customer = await _create_user(db, "sla_customer7")
    category = await _create_category(db)
    data = TicketCreate(title="resolve", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.status = "in_progress"
    await db.commit()

    await transition_ticket_status(db, ticket, "resolved")

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.resolved_at is not None


# SLA-008: resolved -> in_progress 清空 resolved_at
async def test_reopen_clears_resolved_at(db):
    from app.services.ticket_service import transition_ticket_status

    customer = await _create_user(db, "sla_customer8")
    category = await _create_category(db)
    data = TicketCreate(title="reopen", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.status = "in_progress"
    await db.commit()

    await transition_ticket_status(db, ticket, "resolved")
    await transition_ticket_status(db, ticket, "in_progress")

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    record = result.scalar_one()
    assert record.resolved_at is None
```

- [ ] **Step 8: Run tests to verify failures**

Run: `pytest -p no:anyio tests/test_sla.py -v`
Expected: 8 tests — some FAIL because `sla_service` 尚未创建或 `create_ticket` 未调用它

- [ ] **Step 9: Implement services and run tests**

完成 Step 1-6 的代码修改后：
Run: `pytest -p no:anyio tests/test_sla.py -v`
Expected: 8 tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/sla_service.py backend/app/services/ticket_service.py backend/app/services/reply_service.py backend/app/routers/tickets.py backend/app/schemas/category.py backend/tests/test_sla.py
git commit -m "feat(t006): SLA rule engine with create, first-response and resolution capture"
```

---

### Task 3: 通知服务与 REST API

**Files:**
- Create: `backend/app/services/notification_service.py`
- Create: `backend/app/routers/notifications.py`
- Create: `backend/app/schemas/notification.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: `Notification` model
- Produces:
  - `create_notification(db, user_id, type, title, message, data) -> Notification`
  - `get_unread_notifications(db, user_id, limit=50) -> list[Notification]`
  - `mark_notification_read(db, notification_id, user_id) -> bool`
  - `mark_all_notifications_read(db, user_id) -> int`
  - GET `/api/v1/notifications`
  - POST `/api/v1/notifications/{id}/read`
  - POST `/api/v1/notifications/read-all`

- [ ] **Step 1: Create `schemas/notification.py`**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    data: dict
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Create `notification_service.py`**

```python
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notif)
    # 不自行 flush，由调用方统一 commit
    return notif


async def get_unread_notifications(
    db: AsyncSession, user_id: int, limit: int = 50
) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def mark_notification_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    return result.rowcount > 0


async def mark_all_notifications_read(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount
```

- [ ] **Step 3: Create `routers/notifications.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import (
    get_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter()


@router.get("/notifications", response_model=dict)
async def list_notifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await get_unread_notifications(db, current_user.id, limit=limit)
    unread_count = sum(1 for n in items if not n.is_read)
    return {
        "items": [NotificationResponse.model_validate(n).model_dump() for n in items],
        "unread_count": unread_count,
    }


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await mark_notification_read(db, notification_id, current_user.id)
    return None


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await mark_all_notifications_read(db, current_user.id)
    return None
```

- [ ] **Step 4: Modify `main.py` 注册 router**

在 `backend/app/main.py` 顶部导入增加：
```python
from app.routers import auth, categories, dispatch, notifications, sla, tickets, webhooks
```

在 router 注册区增加：
```python
app.include_router(notifications.router, prefix="/api/v1", tags=["Notifications"])
```

> **注意**：`sla` router 在 Task 5 创建，此处先只注册 `notifications`。

- [ ] **Step 5: Write failing tests**

```python
# backend/tests/test_notifications.py
from sqlalchemy import select

from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    create_notification,
    get_unread_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.utils.security import get_password_hash


async def _create_user(db, username, role="customer"):
    user = User(username=username, email=f"{username}@example.com", password_hash=get_password_hash("Pass1234"), role=role, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# NOTIF-001: create_notification
async def test_create_notification(db):
    user = await _create_user(db, "notif_user")
    notif = await create_notification(db, user.id, "test", "Title", "Message", {"ticket_id": 1})
    await db.commit()
    await db.refresh(notif)

    result = await db.execute(select(Notification).where(Notification.user_id == user.id))
    fetched = result.scalar_one()
    assert fetched.type == "test"
    assert fetched.title == "Title"
    assert fetched.data == {"ticket_id": 1}
    assert fetched.is_read is False


# NOTIF-002: get_unread_notifications
async def test_get_unread_notifications(db):
    user = await _create_user(db, "notif_user2")
    await create_notification(db, user.id, "test", "A", "msg")
    await create_notification(db, user.id, "test", "B", "msg")
    await db.commit()

    items = await get_unread_notifications(db, user.id)
    assert len(items) == 2
    assert items[0].title == "B"


# NOTIF-003: mark_notification_read
async def test_mark_notification_read(db):
    user = await _create_user(db, "notif_user3")
    notif = await create_notification(db, user.id, "test", "T", "msg")
    await db.commit()
    await db.refresh(notif)

    ok = await mark_notification_read(db, notif.id, user.id)
    assert ok is True
    await db.commit()

    result = await db.execute(select(Notification).where(Notification.id == notif.id))
    fetched = result.scalar_one()
    assert fetched.is_read is True


# NOTIF-004: mark_all_notifications_read
async def test_mark_all_notifications_read(db):
    user = await _create_user(db, "notif_user4")
    await create_notification(db, user.id, "test", "A", "msg")
    await create_notification(db, user.id, "test", "B", "msg")
    await db.commit()

    count = await mark_all_notifications_read(db, user.id)
    assert count == 2
    await db.commit()

    items = await get_unread_notifications(db, user.id)
    assert all(n.is_read for n in items)


# NOTIF-005: API list notifications
async def test_api_list_notifications(client, customer_auth_headers, db):
    r = await client.get("/api/v1/notifications", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "unread_count" in data


# NOTIF-006: user can only mark own notification read
async def test_api_mark_read_own_only(client, customer_auth_headers, supervisor_auth_headers, db):
    from app.services.notification_service import create_notification

    # 获取 customer 用户 id
    from sqlalchemy import select
    from app.models.user import User
    result = await db.execute(select(User).where(User.username == "customer_test"))
    customer = result.scalar_one()

    notif = await create_notification(db, customer.id, "test", "T", "msg")
    await db.commit()
    await db.refresh(notif)

    # supervisor 尝试标记 customer 的通知
    r = await client.post(f"/api/v1/notifications/{notif.id}/read", headers=supervisor_auth_headers)
    # 204 因为 where 条件过滤了，实际无影响
    assert r.status_code == 204

    result = await db.execute(select(Notification).where(Notification.id == notif.id))
    fetched = result.scalar_one()
    # supervisor 的标记对 customer 的通知无影响
    assert fetched.is_read is False
```

- [ ] **Step 6: Run tests**

Run: `pytest -p no:anyio tests/test_notifications.py -v`
Expected: 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/notification_service.py backend/app/routers/notifications.py backend/app/schemas/notification.py backend/app/main.py backend/tests/test_notifications.py
git commit -m "feat(t006): notification service and REST API"
```

---

### Task 4: Celery 扫描任务

**Files:**
- Create: `backend/app/tasks/sla_tasks.py`
- Modify: `backend/celery_worker.py`
- Test: `backend/tests/test_sla_tasks.py`

**Interfaces:**
- Consumes: `SLARecord` model, `Notification` service, `selectinload`, `with_for_update`
- Produces:
  - `scan_sla_deadlines` (Celery shared_task)
  - `notify_sla_warning(db, sla, breach_type, stage, supervisor_ids) -> bool`
  - `notify_sla_breach(db, sla, breach_type, supervisor_ids) -> None`

- [ ] **Step 1: Create `sla_tasks.py`**

```python
import asyncio
import logging
from datetime import datetime, timedelta

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.sla_record import SLARecord
from app.models.user import User
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)


@shared_task(name="tasks.scan_sla_deadlines")
def scan_sla_deadlines():
    asyncio.run(_async_scan())


async def _async_scan():
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        supervisors = await db.execute(select(User.id).where(User.role == "supervisor"))
        supervisor_ids = [r[0] for r in supervisors.all()]

        try:
            await _scan_first_resp(db, now, supervisor_ids)
            await _scan_resolution(db, now, supervisor_ids)
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _scan_first_resp(db, now, supervisor_ids):
    # 客服 3 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.first_resp_hours > 3,
            SLARecord.first_resp_due > now,
            SLARecord.first_resp_due <= now + timedelta(hours=3),
            SLARecord.first_resp_at.is_(None),
            SLARecord.first_resp_warned_agent_3h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "first_resp", "agent_3h", supervisor_ids)
            if sent:
                record.first_resp_warned_agent_3h = True
        except Exception:
            logger.exception("Failed first_resp 3h warning for ticket %s", record.ticket_id)

    # 客服 2 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.first_resp_hours > 2,
            SLARecord.first_resp_due > now,
            SLARecord.first_resp_due <= now + timedelta(hours=2),
            SLARecord.first_resp_at.is_(None),
            SLARecord.first_resp_warned_agent_2h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "first_resp", "agent_2h", supervisor_ids)
            if sent:
                record.first_resp_warned_agent_2h = True
        except Exception:
            logger.exception("Failed first_resp 2h warning for ticket %s", record.ticket_id)

    # 主管 1 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.first_resp_hours > 1,
            SLARecord.first_resp_due > now,
            SLARecord.first_resp_due <= now + timedelta(hours=1),
            SLARecord.first_resp_at.is_(None),
            SLARecord.first_resp_warned_supervisor_1h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "first_resp", "supervisor_1h", supervisor_ids)
            if sent:
                record.first_resp_warned_supervisor_1h = True
        except Exception:
            logger.exception("Failed first_resp 1h warning for ticket %s", record.ticket_id)

    # 超时
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.first_resp_due <= now,
            SLARecord.first_resp_at.is_(None),
            SLARecord.first_resp_breached.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            await notify_sla_breach(db, record, "first_resp", supervisor_ids)
            record.first_resp_breached = True
        except Exception:
            logger.exception("Failed first_resp breach for ticket %s", record.ticket_id)


async def _scan_resolution(db, now, supervisor_ids):
    # 客服 3 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.resolution_hours > 3,
            SLARecord.resolution_due > now,
            SLARecord.resolution_due <= now + timedelta(hours=3),
            SLARecord.resolved_at.is_(None),
            SLARecord.resolution_warned_agent_3h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "resolution", "agent_3h", supervisor_ids)
            if sent:
                record.resolution_warned_agent_3h = True
        except Exception:
            logger.exception("Failed resolution 3h warning for ticket %s", record.ticket_id)

    # 客服 2 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.resolution_hours > 2,
            SLARecord.resolution_due > now,
            SLARecord.resolution_due <= now + timedelta(hours=2),
            SLARecord.resolved_at.is_(None),
            SLARecord.resolution_warned_agent_2h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "resolution", "agent_2h", supervisor_ids)
            if sent:
                record.resolution_warned_agent_2h = True
        except Exception:
            logger.exception("Failed resolution 2h warning for ticket %s", record.ticket_id)

    # 主管 1 小时提醒
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.resolution_hours > 1,
            SLARecord.resolution_due > now,
            SLARecord.resolution_due <= now + timedelta(hours=1),
            SLARecord.resolved_at.is_(None),
            SLARecord.resolution_warned_supervisor_1h.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            sent = await notify_sla_warning(db, record, "resolution", "supervisor_1h", supervisor_ids)
            if sent:
                record.resolution_warned_supervisor_1h = True
        except Exception:
            logger.exception("Failed resolution 1h warning for ticket %s", record.ticket_id)

    # 超时
    stmt = (
        select(SLARecord)
        .options(selectinload(SLARecord.ticket))
        .where(
            SLARecord.resolution_due <= now,
            SLARecord.resolved_at.is_(None),
            SLARecord.resolution_breached.is_(False),
        )
        .with_for_update()
    )
    for record in (await db.execute(stmt)).scalars():
        try:
            await notify_sla_breach(db, record, "resolution", supervisor_ids)
            record.resolution_breached = True
        except Exception:
            logger.exception("Failed resolution breach for ticket %s", record.ticket_id)


async def notify_sla_warning(
    db, sla: SLARecord, breach_type: str, stage: str, supervisor_ids: list[int]
) -> bool:
    ticket = sla.ticket
    target_user_ids = set()

    if stage in ("agent_3h", "agent_2h") and ticket.assignee_id:
        target_user_ids.add(ticket.assignee_id)
    elif stage == "supervisor_1h":
        target_user_ids.update(supervisor_ids)

    if not target_user_ids:
        return False

    stage_label = {"agent_3h": "3小时", "agent_2h": "2小时", "supervisor_1h": "1小时"}[stage]
    type_label = "首次响应" if breach_type == "first_resp" else "解决"

    for user_id in target_user_ids:
        await create_notification(
            db,
            user_id=user_id,
            type="sla_warning",
            title=f"[预警] 工单 #{ticket.ticket_no} 即将超时",
            message=f"{type_label}截止时间剩余不足 {stage_label}，请及时处理。",
            data={"ticket_id": ticket.id, "sla_record_id": sla.id, "stage": stage, "type": breach_type},
        )
    return True


async def notify_sla_breach(
    db, sla: SLARecord, breach_type: str, supervisor_ids: list[int]
) -> None:
    ticket = sla.ticket
    target_user_ids = set()

    if ticket.assignee_id:
        target_user_ids.add(ticket.assignee_id)
    target_user_ids.update(supervisor_ids)

    if not target_user_ids:
        return

    type_label = "首次响应" if breach_type == "first_resp" else "解决"
    hours = sla.first_resp_hours if breach_type == "first_resp" else sla.resolution_hours

    for user_id in target_user_ids:
        await create_notification(
            db,
            user_id=user_id,
            type="sla_breach",
            title=f"[超时] 工单 #{ticket.ticket_no} SLA 已超时",
            message=f"{type_label}时间已超出规定时限（{hours} 小时）。",
            data={"ticket_id": ticket.id, "sla_record_id": sla.id, "type": breach_type},
        )
```

- [ ] **Step 2: Modify `celery_worker.py` 增加 beat_schedule**

```python
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ticket_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.sla_tasks",
        "app.tasks.notify_tasks",
        "app.tasks.export_tasks",
        "app.tasks.email_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "scan-sla-deadlines": {
        "task": "tasks.scan_sla_deadlines",
        "schedule": 300.0,
    },
}
```

- [ ] **Step 3: Write failing tests**

```python
# backend/tests/test_sla_tasks.py
from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.category import Category
from app.models.notification import Notification
from app.models.sla_record import SLARecord
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket
from app.tasks.sla_tasks import _async_scan
from app.utils.security import get_password_hash


async def _create_user(db, username, role="customer"):
    user = User(username=username, email=f"{username}@example.com", password_hash=get_password_hash("Pass1234"), role=role, is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_category(db, sla_config=None):
    category = Category(name="故障", code="bug", default_priority="P2", sla_config=sla_config or {})
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# TASK-001: 3h 预警触发并创建通知
async def test_scan_first_resp_agent_3h_warning(db):
    customer = await _create_user(db, "task_customer")
    agent = await _create_user(db, "task_agent", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="warn", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.assignee_id = agent.id
    await db.commit()

    # 把 first_resp_due 调到 2.5h 后（在 3h 预警窗口内）
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_due = datetime.utcnow() + timedelta(hours=2, minutes=30)
    sla.first_resp_hours = 8
    await db.commit()

    await _async_scan()

    result = await db.execute(select(Notification).where(Notification.user_id == agent.id))
    notif = result.scalar_one_or_none()
    assert notif is not None
    assert notif.type == "sla_warning"
    assert "3小时" in notif.message

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    assert sla.first_resp_warned_agent_3h is True


# TASK-002: 1h 主管预警触发
async def test_scan_first_resp_supervisor_1h_warning(db):
    customer = await _create_user(db, "task_customer2")
    supervisor = await _create_user(db, "task_super", "supervisor")
    category = await _create_category(db)
    data = TicketCreate(title="super warn", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_due = datetime.utcnow() + timedelta(minutes=45)
    sla.first_resp_hours = 8
    await db.commit()

    await _async_scan()

    result = await db.execute(select(Notification).where(Notification.user_id == supervisor.id))
    notif = result.scalar_one_or_none()
    assert notif is not None
    assert notif.type == "sla_warning"
    assert "1小时" in notif.message

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    assert sla.first_resp_warned_supervisor_1h is True


# TASK-003: 超时标记触发
async def test_scan_first_resp_breach(db):
    customer = await _create_user(db, "task_customer3")
    agent = await _create_user(db, "task_agent2", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="breach", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.assignee_id = agent.id
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_due = datetime.utcnow() - timedelta(hours=1)
    await db.commit()

    await _async_scan()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    assert sla.first_resp_breached is True

    result = await db.execute(select(Notification).where(Notification.user_id == agent.id))
    notif = result.scalar_one_or_none()
    assert notif is not None
    assert notif.type == "sla_breach"


# TASK-004: 短 SLA（1h）不触发 3h 预警
async def test_short_sla_no_3h_warning(db):
    customer = await _create_user(db, "task_customer4")
    agent = await _create_user(db, "task_agent3", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="short", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.assignee_id = agent.id
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_hours = 1
    sla.first_resp_due = datetime.utcnow() + timedelta(minutes=30)
    await db.commit()

    await _async_scan()

    result = await db.execute(select(Notification).where(Notification.user_id == agent.id))
    notif = result.scalar_one_or_none()
    assert notif is None


# TASK-005: 重复扫描不重复通知
async def test_scan_no_duplicate_notification(db):
    customer = await _create_user(db, "task_customer5")
    agent = await _create_user(db, "task_agent4", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="dup", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.assignee_id = agent.id
    await db.commit()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_due = datetime.utcnow() + timedelta(hours=2, minutes=30)
    sla.first_resp_hours = 8
    await db.commit()

    await _async_scan()
    await _async_scan()

    result = await db.execute(select(Notification).where(Notification.user_id == agent.id))
    count = len(result.scalars().all())
    assert count == 1
```

- [ ] **Step 4: Run tests**

Run: `pytest -p no:anyio tests/test_sla_tasks.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/sla_tasks.py backend/celery_worker.py backend/tests/test_sla_tasks.py
git commit -m "feat(t006): Celery scan task for SLA warnings and breaches"
```

---

### Task 5: SLA 查询 API 与嵌入

**Files:**
- Create: `backend/app/routers/sla.py`
- Create: `backend/app/schemas/sla.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/app/schemas/ticket.py`
- Test: `backend/tests/test_sla.py`（追加）

**Interfaces:**
- Consumes: `get_sla_record_by_ticket_id`, `SLARecord` model
- Produces:
  - GET `/api/v1/tickets/{id}/sla`
  - GET `/api/v1/admin/sla/overdue?breach_type=`
  - `TicketResponse.sla` 嵌入字段

- [ ] **Step 1: Create `schemas/sla.py`**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SLAResponse(BaseModel):
    ticket_id: int
    priority: str
    first_resp_hours: int
    resolution_hours: int
    first_resp_due: datetime
    resolution_due: datetime
    first_resp_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    first_resp_breached: bool
    resolution_breached: bool

    model_config = ConfigDict(from_attributes=True)


class SLASummary(BaseModel):
    first_resp_due: datetime
    resolution_due: datetime
    first_resp_breached: bool
    resolution_breached: bool

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Create `routers/sla.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import NotFoundException, PermissionDeniedException
from app.models.user import User
from app.routers.tickets import check_ticket_access
from app.schemas.sla import SLAResponse
from app.services.sla_service import get_sla_record_by_ticket_id
from app.services.ticket_service import get_ticket_by_id

router = APIRouter()


@router.get("/tickets/{ticket_id}/sla", response_model=SLAResponse)
async def get_ticket_sla(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(ticket, current_user)

    sla = await get_sla_record_by_ticket_id(db, ticket_id)
    if not sla:
        raise NotFoundException("SLA 记录不存在")
    return sla


@router.get("/admin/sla/overdue", response_model=list[SLAResponse])
async def list_overdue_sla(
    breach_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "supervisor")),
):
    from sqlalchemy import select
    from app.models.sla_record import SLARecord

    stmt = select(SLARecord).where(
        (SLARecord.first_resp_breached.is_(True)) | (SLARecord.resolution_breached.is_(True))
    )
    if breach_type == "first_resp":
        stmt = stmt.where(SLARecord.first_resp_breached.is_(True))
    elif breach_type == "resolution":
        stmt = stmt.where(SLARecord.resolution_breached.is_(True))

    result = await db.execute(stmt.order_by(SLARecord.id.desc()))
    return result.scalars().all()
```

- [ ] **Step 3: Modify `schemas/ticket.py` 嵌入 SLA 摘要**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.sla import SLASummary


class TicketBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str = Field(...)
    category_id: int = Field(..., gt=0)
    priority: str = Field(default="P2", pattern="^(P0|P1|P2|P3)$")
    source: str = Field(default="web", pattern="^(web|email|api)$")


class TicketCreate(TicketBase):
    assignee_id: Optional[int] = None
    auto_dispatch: bool = False


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = Field(None, gt=0)
    priority: Optional[str] = Field(None, pattern="^(P0|P1|P2|P3)$")
    assignee_id: Optional[int] = None


class TicketResponse(BaseModel):
    id: int
    ticket_no: str
    title: str
    description: str
    status: str
    priority: str
    category_id: int
    requester_id: int
    assignee_id: Optional[int] = None
    source: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    sla: Optional[SLASummary] = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Modify `routers/tickets.py` 在详情/列表中嵌入 SLA**

在 `backend/app/routers/tickets.py` 顶部增加导入：
```python
from app.schemas.sla import SLASummary
from app.services.sla_service import get_sla_record_by_ticket_id
```

修改 `get_ticket` 函数，在返回前嵌入 SLA：
```python
@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise NotFoundException("工单不存在")
    await check_ticket_access(ticket, current_user)

    sla = await get_sla_record_by_ticket_id(db, ticket_id)
    response = TicketResponse.model_validate(ticket)
    if sla:
        response.sla = SLASummary.model_validate(sla)
    return response
```

修改 `list_tickets` 函数，在序列化时嵌入 SLA：
```python
@router.get("/tickets", response_model=dict)
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await get_tickets_query(
        db, current_user, status, priority, category_id, page, page_size
    )
    items = []
    for ticket in result["items"]:
        resp = TicketResponse.model_validate(ticket)
        # 列表页不单独查 SLA 以避免 N+1；如果 get_tickets_query 已 join 可优化
        # 当前保持简单：列表不嵌入完整 SLA，仅详情嵌入
        items.append(resp.model_dump())
    return {
        "total": result["total"],
        "page": result["n        "        "        
    }
```

Wait, I need to fix that corrupted output. The `list_tickets` modification should be:

```python
@router.get("/tickets", response_model=dict)
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await get_tickets_query(
        db, current_user, status, priority, category_id, page, page_size
    )
    return {
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "items": [
            TicketResponse.model_validate(ticket).model_dump()
            for ticket in result["items"]
        ],
    }
```

> **说明**：列表页不嵌入 SLA 摘要以避免 N+1（当前 `get_tickets_query` 未预加载 SLA）。如果后续需要列表也显示 SLA 状态，在 `get_tickets_query` 中增加 `selectinload(Ticket.sla_record)` 后再嵌入。Task 5 保持简单，仅详情页嵌入。

- [ ] **Step 5: Modify `main.py` 注册 `sla` router**

```python
from app.routers import auth, categories, dispatch, notifications, sla, tickets, webhooks
```

```python
app.include_router(sla.router, prefix="/api/v1", tags=["SLA"])
```

- [ ] **Step 6: Write failing tests**

```python
# backend/tests/test_sla.py 追加

# SLA-009: API 查询工单 SLA 详情
async def test_api_get_ticket_sla(client, customer_auth_headers, db):
    from app.schemas.ticket import TicketCreate
    customer = await _create_user(db, "sla_api_customer")
    category = await _create_category(db)
    data = TicketCreate(title="api sla", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    r = await client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ticket_id"] == ticket.id
    assert data["priority"] == "P1"
    assert "first_resp_due" in data


# SLA-010: API 查询 SLA 详情权限控制
async def test_api_get_ticket_sla_forbidden(client, customer_auth_headers, db):
    from app.schemas.ticket import TicketCreate
    another = await _create_user(db, "another_for_sla", "customer")
    category = await _create_category(db)
    data = TicketCreate(title="private", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, another.id)

    r = await client.get(f"/api/v1/tickets/{ticket.id}/sla", headers=customer_auth_headers)
    assert r.status_code == 403


# SLA-011: admin 查询超时列表
async def test_api_admin_overdue_list(client, admin_auth_headers, db):
    from app.schemas.ticket import TicketCreate
    customer = await _create_user(db, "overdue_customer")
    category = await _create_category(db)
    data = TicketCreate(title="overdue", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    # 手动标记超时
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.first_resp_breached = True
    await db.commit()

    r = await client.get("/api/v1/admin/sla/overdue", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert any(item["ticket_id"] == ticket.id for item in data)


# SLA-012: 工单详情嵌入 SLA 摘要
async def test_ticket_detail_includes_sla_summary(client, customer_auth_headers, db):
    from app.schemas.ticket import TicketCreate
    customer = await _create_user(db, "embed_customer")
    category = await _create_category(db)
    data = TicketCreate(title="embed", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "sla" in data
    assert data["sla"]["first_resp_due"] is not None
    assert data["sla"]["resolution_due"] is not None
```

- [ ] **Step 7: Run tests**

Run: `pytest -p no:anyio tests/test_sla.py -v`
Expected: 12 tests PASS（包含 Task 2 的 8 条 + Task 5 的 4 条）

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/sla.py backend/app/schemas/sla.py backend/app/routers/tickets.py backend/app/schemas/ticket.py backend/app/main.py backend/tests/test_sla.py
git commit -m "feat(t006): SLA query API and ticket detail embedding"
```

---

### Task 6: 集成测试与补齐

**Files:**
- Modify: `backend/tests/test_sla.py`
- Modify: `backend/tests/test_sla_tasks.py`
- Modify: `backend/tests/test_notifications.py`

**Interfaces:**
- Consumes: 全部前面 Task 的组件
- Produces: ≥14 条测试全部通过，零失败

- [ ] **Step 1: 补充边界测试到 `test_sla.py`**

```python
# backend/tests/test_sla.py 追加

# SLA-013: 已关闭工单的 SLA 记录存在但不影响扫描（扫描任务自行过滤）
async def test_closed_ticket_sla_exists(db):
    from app.schemas.ticket import TicketCreate
    from app.services.ticket_service import transition_ticket_status

    customer = await _create_user(db, "close_customer")
    category = await _create_category(db)
    data = TicketCreate(title="close", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.status = "in_progress"
    await db.commit()

    await transition_ticket_status(db, ticket, "resolved")
    await transition_ticket_status(db, ticket, "closed")

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    assert sla is not None
    assert sla.resolved_at is not None
```

- [ ] **Step 2: 补充边界测试到 `test_sla_tasks.py`**

```python
# backend/tests/test_sla_tasks.py 追加

# TASK-006: 已解决工单不触发 resolution 超时
async def test_resolved_ticket_no_resolution_breach(db):
    customer = await _create_user(db, "res_customer")
    agent = await _create_user(db, "res_agent", "agent")
    category = await _create_category(db)
    data = TicketCreate(title="resolved no breach", description="desc", category_id=category.id, priority="P1")
    ticket = await create_ticket(db, data, customer.id)
    ticket.assignee_id = agent.id
    ticket.status = "in_progress"
    await db.commit()

    # 标记 resolved
    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    sla.resolved_at = datetime.utcnow()
    sla.resolution_due = datetime.utcnow() - timedelta(hours=1)
    await db.commit()

    await _async_scan()

    result = await db.execute(select(SLARecord).where(SLARecord.ticket_id == ticket.id))
    sla = result.scalar_one()
    assert sla.resolution_breached is False
```

- [ ] **Step 3: 全量回归测试**

Run: `pytest -p no:anyio tests/ -v`
Expected: 所有现有测试 + 新增测试全部通过。当前基线 131 passed，目标 ≥145 passed。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_sla.py backend/tests/test_sla_tasks.py backend/tests/test_notifications.py
git commit -m "test(t006): integration and boundary tests for SLA management"
```

---

## Spec Coverage Check

| Spec 章节 | 对应 Task | 验证方式 |
|-----------|-----------|----------|
| 4.1 categories.sla_config 格式与迁移 | Task 1 (迁移), Task 2 (兼容层) | 测试 SLA-003, SLA-004 |
| 4.2 sla_records 模型 | Task 1 | 测试 SLA-001 |
| 4.3 notifications 模型 | Task 1 | 测试 NOTIF-001 |
| 5.1 创建 SLA 记录 | Task 2 | 测试 SLA-002 |
| 5.2 首次响应时间捕获 | Task 2 | 测试 SLA-005, SLA-006 |
| 5.3 解决时间捕获与重新打开 | Task 2 | 测试 SLA-007, SLA-008 |
| 6.1 Celery Beat 配置 | Task 4 | 代码审查 `celery_worker.py` |
| 6.2 扫描逻辑（锁 + N+1 + 异常隔离） | Task 4 | 代码审查 `sla_tasks.py` |
| 6.3 通知发送 | Task 4 | 测试 TASK-001~005 |
| 7.1 Notification Service | Task 3 | 测试 NOTIF-001~004 |
| 7.2 通知 API | Task 3 | 测试 NOTIF-005~006 |
| 8.1 工单 SLA 详情 | Task 5 | 测试 SLA-009, SLA-010 |
| 8.2 管理后台超时列表 | Task 5 | 测试 SLA-011 |
| 8.3 工单列表/详情嵌入 SLA | Task 5 | 测试 SLA-012 |
| 十、测试策略 ≥14 条 | Task 1~6 | 全量测试计数 |

## Placeholder Scan

- 无 "TBD", "TODO", "implement later", "fill in details"
- 无 "Add appropriate error handling" / "add validation" / "handle edge cases"
- 无 "Write tests for the above"（每步都有具体测试代码）
- 无 "Similar to Task N"（各任务代码独立完整）
- 无未定义的类型/函数引用

## Type Consistency Check

- `create_reply` 签名统一为 `(db, ticket, data, author_id, is_agent_reply=False)`
- `transition_ticket_status` 处理 `resolved_at` / reopen 逻辑
- `SLARecord` 字段名与模型、迁移、扫描任务完全一致
- `Notification` 模型使用 `JSONB`，与迁移一致
- `TicketResponse.sla` 使用 `SLASummary` schema
- `CategoryBase.sla_config` 默认值为 nested 格式

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-09-sla-management.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?