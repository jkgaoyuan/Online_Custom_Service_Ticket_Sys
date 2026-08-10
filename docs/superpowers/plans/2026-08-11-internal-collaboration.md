# 内部协作（转交/协助）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现工单内部协作：客服可转交工单（记录原因），可请求其他客服协助，协作历史嵌入工单详情。

**Architecture:** 新增 `ticket_collaborations` 表存储 `transfer`（变更负责人）和 `assist`（不改变负责人）记录。转交时更新 `tickets.assignee_id` 并通知新负责人；协助仅创建协作记录并通知协助人。协作历史嵌入工单详情响应。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, pytest

## Global Constraints
- 所有数据库变更必须通过 Alembic 迁移
- `create_notification` 不自行 flush/commit，由调用方统一 commit
- 测试使用 `client`（AsyncClient）+ `db`（AsyncSession）+ `agent_auth_headers` 等 fixtures
- 转交目标必须是 `agent` 角色且 `is_active=True`
- 同一工单同一协助人不可重复协助
- 转交原因/协助说明最大 500 字
- 协作历史按 `created_at` 倒序展示

---

## File Map

| 文件 | 职责 | 操作 |
|------|------|------|
| `backend/alembic/versions/20260811_add_ticket_collaborations.py` | 新增 `ticket_collaborations` 表 | 创建 |
| `backend/app/models/collaboration.py` | `TicketCollaboration` 模型 | 创建 |
| `backend/app/models/__init__.py` | 注册新模型 | 修改 |
| `backend/app/schemas/collaboration.py` | `CollaborationResponse`, `TransferRequest`, `AssistRequest` | 创建 |
| `backend/app/routers/tickets.py` | 新增 `POST /transfer` 和 `POST /assist` 端点 | 修改 |
| `backend/app/services/collaboration_service.py` | `transfer_ticket`, `request_assistance`, `get_collaborations` | 创建 |
| `backend/app/routers/tickets.py` | 工单详情嵌入 `collaborations` | 修改 |
| `backend/tests/test_collaboration.py` | 转交/协助/异常测试 | 创建 |

---

### Task 1: Alembic 迁移 — 新增 `ticket_collaborations` 表

**Files:**
- Create: `backend/alembic/versions/20260811_add_ticket_collaborations.py`
- Create: `backend/app/models/collaboration.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Consumes: 现有 `tickets` 表和 `users` 表
- Produces: `TicketCollaboration` 模型，可 SQLAlchemy 查询

- [ ] **Step 1: 创建 Alembic 迁移**

```python
"""add ticket_collaborations table

Revision ID: 20260811_add_ticket_collaborations
Revises: 20260811_add_satisfaction_at
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260811_add_ticket_collaborations'
down_revision: Union[str, None] = '20260811_add_satisfaction_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ticket_collaborations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=True),
        sa.Column('to_user_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_collaborations_ticket', 'ticket_collaborations', ['ticket_id'], unique=False)
    op.create_index('ix_collaborations_to_user', 'ticket_collaborations', ['to_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_collaborations_to_user', table_name='ticket_collaborations')
    op.drop_index('ix_collaborations_ticket', table_name='ticket_collaborations')
    op.drop_table('ticket_collaborations')
```

- [ ] **Step 2: 创建模型文件**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TicketCollaboration(Base):
    __tablename__ = "ticket_collaborations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # "transfer" | "assist"
    from_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    to_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket: Mapped["Ticket"] = relationship("Ticket")
    from_user: Mapped["User | None"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])
```

- [ ] **Step 3: 注册模型**

在 `backend/app/models/__init__.py` 中增加：

```python
from app.models.collaboration import TicketCollaboration
```

- [ ] **Step 4: 运行迁移**

```bash
cd backend
alembic upgrade 20260811_add_ticket_collaborations
```

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/20260811_add_ticket_collaborations.py backend/app/models/collaboration.py backend/app/models/__init__.py
git commit -m "feat(collaboration): add ticket_collaborations table and model"
```

---

### Task 2: 协作 Service — 转交/协助/查询

**Files:**
- Create: `backend/app/services/collaboration_service.py`
- Modify: `backend/app/routers/tickets.py`（导入新 service）

**Interfaces:**
- Consumes: `Ticket`, `User`, `TicketCollaboration` 模型，`create_notification`
- Produces: `transfer_ticket()`, `request_assistance()`, `get_collaborations()` 函数

- [ ] **Step 1: 创建 collaboration_service.py**

```python
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket
from app.models.user import User
from app.models.collaboration import TicketCollaboration
from app.services.notification_service import create_notification


async def transfer_ticket(
    db: AsyncSession, ticket_id: int, from_user_id: int, to_user_id: int, reason: str | None
) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 校验目标客服
    target_result = await db.execute(
        select(User).where(User.id == to_user_id, User.role == "agent", User.is_active == True)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=400, detail="目标客服不存在或不可用")

    if ticket.assignee_id == to_user_id:
        raise HTTPException(status_code=400, detail="该客服已是当前负责人")

    # 创建协作记录
    collab = TicketCollaboration(
        ticket_id=ticket_id,
        type="transfer",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=(reason[:500] if reason else None),
    )
    db.add(collab)

    old_assignee = ticket.assignee_id
    ticket.assignee_id = to_user_id

    # 状态自动流转：open -> in_progress
    if ticket.status == "open":
        ticket.status = "in_progress"

    # 通知新负责人
    await create_notification(
        db,
        user_id=to_user_id,
        type="ticket_transferred",
        title=f"工单 #{ticket.ticket_no} 已转交给你",
        message=f"来自 {'系统' if old_assignee is None else '客服'} 的转交，原因：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )

    await db.commit()
    await db.refresh(ticket)
    return ticket


async def request_assistance(
    db: AsyncSession, ticket_id: int, from_user_id: int, to_user_id: int, reason: str | None
) -> TicketCollaboration:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    target_result = await db.execute(
        select(User).where(User.id == to_user_id, User.role == "agent", User.is_active == True)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=400, detail="目标客服不存在或不可用")

    # 检查重复协助
    dup_result = await db.execute(
        select(TicketCollaboration).where(
            and_(
                TicketCollaboration.ticket_id == ticket_id,
                TicketCollaboration.type == "assist",
                TicketCollaboration.to_user_id == to_user_id,
            )
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该客服已在协助此工单")

    collab = TicketCollaboration(
        ticket_id=ticket_id,
        type="assist",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=(reason[:500] if reason else None),
    )
    db.add(collab)

    # 通知协助人
    await create_notification(
        db,
        user_id=to_user_id,
        type="assistance_requested",
        title=f"协助请求：工单 #{ticket.ticket_no}",
        message=f"请求协助原因：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )

    await db.commit()
    await db.refresh(collab)
    return collab


async def get_collaborations(db: AsyncSession, ticket_id: int) -> list[TicketCollaboration]:
    result = await db.execute(
        select(TicketCollaboration)
        .options(
            selectinload(TicketCollaboration.from_user),
            selectinload(TicketCollaboration.to_user),
        )
        .where(TicketCollaboration.ticket_id == ticket_id)
        .order_by(TicketCollaboration.created_at.desc())
    )
    return result.scalars().all()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/collaboration_service.py
git commit -m "feat(collaboration): add transfer and assistance service"
```

---

### Task 3: API 端点 — 转交 + 协助 + 详情嵌入

**Files:**
- Create: `backend/app/schemas/collaboration.py`
- Modify: `backend/app/routers/tickets.py`

**Interfaces:**
- Consumes: `transfer_ticket`, `request_assistance`, `get_collaborations` services
- Produces: `POST /tickets/{id}/transfer`, `POST /tickets/{id}/assist`, `TicketResponse` 嵌入 `collaborations`

- [ ] **Step 1: 创建 Pydantic Schema**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransferRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)


class AssistRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    reason: Optional[str] = Field(None, max_length=500)


class UserBrief(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class CollaborationResponse(BaseModel):
    id: int
    type: str
    from_user: Optional[UserBrief] = None
    to_user: UserBrief
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: 修改 `TicketResponse` 嵌入协作历史**

在 `backend/app/schemas/ticket.py` 中导入并增加：

```python
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.sla import SLASummary
from app.schemas.collaboration import CollaborationResponse

class TicketResponse(BaseModel):
    # ... 现有字段 ...
    satisfaction: Optional[str] = None
    satisfaction_note: Optional[str] = None
    satisfaction_at: Optional[datetime] = None
    collaborations: Optional[list[CollaborationResponse]] = None
    sla: Optional[SLASummary] = None

    model_config = ConfigDict(from_attributes=True)
```

> 注意：由于 `model_validate` 自动从 SQLAlchemy 对象映射，`collaborations` 不会自动填充，需要自定义序列化。修改 `get_ticket` 端点手动处理。

- [ ] **Step 3: 修改 `get_ticket` 端点嵌入协作历史**

在 `backend/app/routers/tickets.py` 中：

```python
from app.schemas.collaboration import CollaborationResponse
from app.services.collaboration_service import get_collaborations

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
    collaborations = await get_collaborations(db, ticket_id)

    response = TicketResponse.model_validate(ticket)
    if sla:
        response.sla = SLASummary.model_validate(sla)
    if collaborations:
        response.collaborations = [CollaborationResponse.model_validate(c) for c in collaborations]
    return response
```

- [ ] **Step 4: 新增转交和协助端点**

在 `backend/app/routers/tickets.py` 中追加：

```python
from app.schemas.collaboration import TransferRequest, AssistRequest
from app.services.collaboration_service import transfer_ticket, request_assistance
from app.dependencies import require_role

@router.post("/tickets/{ticket_id}/transfer", response_model=TicketResponse)
async def transfer_ticket_endpoint(
    ticket_id: int,
    data: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    ticket = await transfer_ticket(db, ticket_id, current_user.id, data.to_user_id, data.reason)
    return TicketResponse.model_validate(ticket)


@router.post("/tickets/{ticket_id}/assist", status_code=status.HTTP_201_CREATED)
async def request_assistance_endpoint(
    ticket_id: int,
    data: AssistRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent", "supervisor", "admin")),
):
    collab = await request_assistance(db, ticket_id, current_user.id, data.to_user_id, data.reason)
    return CollaborationResponse.model_validate(collab)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/collaboration.py backend/app/routers/tickets.py
git commit -m "feat(collaboration): add transfer and assist API endpoints"
```

---

### Task 4: 后端测试

**Files:**
- Create: `backend/tests/test_collaboration.py`

**Interfaces:**
- Consumes: `client`, `db`, `agent_auth_headers`, `admin_auth_headers` fixtures
- Produces: 10 条测试全部通过

- [ ] **Step 1: 编写测试**

```python
from datetime import datetime
from sqlalchemy import select

from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.models.collaboration import TicketCollaboration
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket
from app.utils.security import get_password_hash


async def _create_category(db):
    category = Category(name="故障", code="bug", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _create_agent(db, username, email):
    agent = User(
        username=username,
        email=email,
        password_hash=get_password_hash("pass"),
        role="agent",
        is_active=True,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


# === P0 正向 ===

# COL-001: 转交工单成功
async def test_transfer_ticket_success(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent02", "a2@test.com")
    # 创建并分派给 agent1
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    body = {"to_user_id": agent2.id, "reason": "需要专家支持"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["assignee_id"] == agent2.id
    assert data["status"] == "in_progress"


# COL-002: 转交记录正确写入协作历史
async def test_transfer_creates_collaboration_record(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent03", "a3@test.com")
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json={"to_user_id": agent2.id, "reason": "转交测试"},
    )

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=agent_auth_headers)
    data = r.json()
    collabs = data["collaborations"]
    assert len(collabs) == 1
    assert collabs[0]["type"] == "transfer"
    assert collabs[0]["reason"] == "转交测试"
    assert collabs[0]["to_user"]["id"] == agent2.id


# COL-003: 请求协助成功
async def test_request_assistance_success(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent04", "a4@test.com")
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    body = {"to_user_id": agent2.id, "reason": "需要帮忙确认配置"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist",
        headers=agent_auth_headers,
        json=body,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "assist"
    assert data["to_user"]["id"] == agent2.id


# COL-004: 转交通知目标客服
async def test_transfer_notification_sent(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent05", "a5@test.com")
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json={"to_user_id": agent2.id},
    )

    # agent2 的通知列表
    from app.services.auth_service import create_access_token
    token = await create_access_token(agent2.id)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/notifications", headers=headers)
    data = r.json()
    assert any(n["type"] == "ticket_transferred" for n in data["items"])


# === P0 异常 ===

# COL-005: 转交给自己 400
async def test_transfer_to_self_400(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    body = {"to_user_id": agent1.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "已是当前负责人" in r.json()["detail"]


# COL-006: 转交给非 agent 用户 400
async def test_transfer_to_non_agent_400(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    customer = User(username="cust_transfer", email="c@t.com", password_hash=get_password_hash("p"), role="customer")
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    body = {"to_user_id": customer.id}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "目标客服" in r.json()["detail"]


# COL-007: 重复协助 400
async def test_duplicate_assistance_400(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent06", "a6@test.com")
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    ticket.assignee_id = agent1.id
    await db.commit()

    await client.post(
        f"/api/v1/tickets/{ticket.id}/assist",
        headers=agent_auth_headers,
        json={"to_user_id": agent2.id},
    )
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/assist",
        headers=agent_auth_headers,
        json={"to_user_id": agent2.id},
    )
    assert r.status_code == 400
    assert "已在协助" in r.json()["detail"]


# COL-008: 工单不存在 404
async def test_transfer_nonexistent_ticket_404(client, agent_auth_headers, db):
    r = await client.post(
        "/api/v1/tickets/99999/transfer",
        headers=agent_auth_headers,
        json={"to_user_id": 1},
    )
    assert r.status_code == 404


# COL-009: 转交 open 工单自动变为 in_progress
async def test_transfer_open_ticket_status_change(client, agent_auth_headers, db):
    category = await _create_category(db)
    agent1 = (await db.execute(select(User).where(User.role == "agent").limit(1))).scalar_one()
    agent2 = await _create_agent(db, "agent07", "a7@test.com")
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), agent1.id
    )
    assert ticket.status == "open"
    await db.commit()

    await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=agent_auth_headers,
        json={"to_user_id": agent2.id},
    )

    r = await client.get(f"/api/v1/tickets/{ticket.id}", headers=agent_auth_headers)
    data = r.json()
    assert data["status"] == "in_progress"


# COL-010: customer 角色调用转交 403
async def test_transfer_customer_forbidden_403(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), customer.id
    )

    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=customer_auth_headers,
        json={"to_user_id": 1},
    )
    assert r.status_code == 403

```

- [ ] **Step 2: 运行测试**

```bash
cd backend
pytest tests/test_collaboration.py -v
```

Expected: 10 passed, 0 failed

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_collaboration.py
git commit -m "test(collaboration): add 10 backend tests for transfer and assistance"
```

---

### Task 5: 前端转交/协助弹窗（M2-T21）

**Files:**
- Modify: `frontend/src/views/agent/AgentTicketDetailView.vue`

**Interfaces:**
- Consumes: `POST /tickets/{id}/transfer`, `POST /tickets/{id}/assist` API
- Produces: 客服详情页操作区增加转交和协助按钮及弹窗

- [ ] **Step 1: 在客服工单详情页增加操作按钮和弹窗**

```vue
<template>
  <!-- 现有详情内容 -->
  
  <!-- 操作区域 -->
  <div class="actions-section">
    <el-button type="warning" @click="showTransferDialog = true">转交工单</el-button>
    <el-button type="info" @click="showAssistDialog = true">请求协助</el-button>
  </div>

  <!-- 转交弹窗 -->
  <el-dialog v-model="showTransferDialog" title="转交工单" width="500px">
    <el-form :model="transferForm">
      <el-form-item label="目标客服" required>
        <el-select v-model="transferForm.to_user_id" placeholder="选择客服">
          <el-option
            v-for="agent in availableAgents"
            :key="agent.id"
            :label="agent.username"
            :value="agent.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="转交原因">
        <el-input
          v-model="transferForm.reason"
          type="textarea"
          :rows="3"
          placeholder="请说明转交原因..."
          maxlength="500"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showTransferDialog = false">取消</el-button>
      <el-button type="primary" @click="submitTransfer" :loading="transferLoading">确认转交</el-button>
    </template>
  </el-dialog>

  <!-- 协助弹窗 -->
  <el-dialog v-model="showAssistDialog" title="请求协助" width="500px">
    <el-form :model="assistForm">
      <el-form-item label="协助客服" required>
        <el-select v-model="assistForm.to_user_id" placeholder="选择客服">
          <el-option
            v-for="agent in availableAgents"
            :key="agent.id"
            :label="agent.username"
            :value="agent.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="协助说明">
        <el-input
          v-model="assistForm.reason"
          type="textarea"
          :rows="3"
          placeholder="请说明需要协助的内容..."
          maxlength="500"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAssistDialog = false">取消</el-button>
      <el-button type="primary" @click="submitAssist" :loading="assistLoading">请求协助</el-button>
    </template>
  </el-dialog>

  <!-- 协作历史展示 -->
  <div v-if="ticket.collaborations && ticket.collaborations.length" class="collaboration-history">
    <h3>协作历史</h3>
    <div
      v-for="c in ticket.collaborations"
      :key="c.id"
      class="collaboration-item"
      :class="c.type"
    >
      <span class="collab-icon">{{ c.type === 'transfer' ? '🔄' : '🤝' }}</span>
      <span class="collab-text">
        {{ c.type === 'transfer' ? '转交' : '协助' }}：
        {{ c.from_user?.username || '系统' }} → {{ c.to_user.username }}
      </span>
      <span v-if="c.reason" class="collab-reason">原因：{{ c.reason }}</span>
      <span class="collab-time">{{ formatDate(c.created_at) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import { ElMessage } from 'element-plus'
import api from '@/api'

const route = useRoute()
const ticketsStore = useTicketsStore()

const showTransferDialog = ref(false)
const showAssistDialog = ref(false)
const transferLoading = ref(false)
const assistLoading = ref(false)
const availableAgents = ref([])

const transferForm = reactive({ to_user_id: null, reason: '' })
const assistForm = reactive({ to_user_id: null, reason: '' })

// 加载可用客服列表（需要后端提供接口，或复用现有 agent-skills）
async function loadAvailableAgents() {
  const r = await api.get('/admin/agent-skills')
  // 去重获取 agent 列表
  const agents = []
  const seen = new Set()
  for (const skill of r.data || []) {
    if (skill.agent && !seen.has(skill.agent.id)) {
      seen.add(skill.agent.id)
      agents.push(skill.agent)
    }
  }
  availableAgents.value = agents
}

async function submitTransfer() {
  if (!transferForm.to_user_id) {
    ElMessage.warning('请选择目标客服')
    return
  }
  transferLoading.value = true
  try {
    await api.post(`/tickets/${route.params.id}/transfer`, transferForm)
    ElMessage.success('转交成功')
    showTransferDialog.value = false
    await ticketsStore.fetchTicket(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '转交失败')
  } finally {
    transferLoading.value = false
  }
}

async function submitAssist() {
  if (!assistForm.to_user_id) {
    ElMessage.warning('请选择协助客服')
    return
  }
  assistLoading.value = true
  try {
    await api.post(`/tickets/${route.params.id}/assist`, assistForm)
    ElMessage.success('协助请求已发送')
    showAssistDialog.value = false
    await ticketsStore.fetchTicket(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '请求协助失败')
  } finally {
    assistLoading.value = false
  }
}

// 打开弹窗时加载客服列表
watch(showTransferDialog, (v) => { if (v) loadAvailableAgents() })
watch(showAssistDialog, (v) => { if (v) loadAvailableAgents() })
</script>

<style scoped>
.actions-section { margin: 16px 0; display: flex; gap: 12px; }
.collaboration-history { margin-top: 24px; padding: 16px; background: #f5f7fa; border-radius: 8px; }
.collaboration-item { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid #e4e7ed; }
.collaboration-item:last-child { border-bottom: none; }
.collab-icon { font-size: 18px; }
.collab-text { flex: 1; }
.collab-reason { color: #666; font-size: 13px; }
.collab-time { color: #999; font-size: 12px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/agent/AgentTicketDetailView.vue
git commit -m "feat(collaboration): add transfer and assist UI in agent ticket detail"
```

---

## Self-Review Checklist

| Spec 要求 | 对应 Task | 状态 |
|-----------|-----------|------|
| 工单可转交（记录原因） | Task 2 | ✅ `transfer_ticket` 变更 `assignee_id` + 创建 `transfer` 记录 |
| 转交后通知新负责人 | Task 2 | ✅ `create_notification` 通知 `to_user_id` |
| 请求协助（不改变负责人） | Task 2 | ✅ `request_assistance` 创建 `assist` 记录 |
| 同一协助人不可重复 | Task 2 | ✅ 重复检查 |
| 协作历史嵌入详情 | Task 3 | ✅ `get_ticket` 返回 `collaborations` 数组 |
| 转交 open 工单自动 in_progress | Task 2 | ✅ 状态自动流转 |
| 前端转交/协助弹窗 | Task 5 | ✅ 客服详情页操作区 |

**Placeholder scan:** 无 TBD/TODO
**Type consistency:** `CollaborationResponse` 与 `TicketCollaboration` 模型字段一致

