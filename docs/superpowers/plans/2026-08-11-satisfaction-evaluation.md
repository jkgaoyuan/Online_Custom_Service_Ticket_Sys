# 满意度评价系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现工单关闭后自动触发满意度评价邀请，客户可提交评价，评价数据用于报表统计。

**Architecture:** 复用 `tickets` 表已有 `satisfaction`/`satisfaction_note` 字段，新增 `satisfaction_at` 字段记录评价时间。关闭工单时通过 `transition_ticket_status` 触发站内通知邀请。报表统计从 `tickets` 表直接聚合。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, pytest

## Global Constraints
- 所有数据库变更必须通过 Alembic 迁移
- `create_notification` 不自行 flush/commit，由调用方统一 commit
- 测试使用 `client`（AsyncClient）+ `db`（AsyncSession）+ `customer_auth_headers` 等 fixtures
- 测试函数命名格式：`test_<behavior>_<expected>`，如 `test_submit_satisfaction_closed_ticket_200`
- API 响应使用 Pydantic Schema 序列化
- 评价提交后不可修改（`satisfaction_at` 非空则拒绝）
- `note` 最大 500 字，超长自动截断

---

## File Map

| 文件 | 职责 | 操作 |
|------|------|------|
| `backend/alembic/versions/20260811_add_satisfaction_at.py` | 新增 `tickets.satisfaction_at` 字段 | 创建 |
| `backend/app/models/ticket.py` | 增加 `satisfaction_at` 字段映射 | 修改 |
| `backend/app/schemas/ticket.py` | 增加 `SatisfactionInfo`, `SatisfactionSubmit` Schema | 修改 |
| `backend/app/services/ticket_service.py` | `transition_ticket_status` 中触发评价通知 | 修改 |
| `backend/app/routers/tickets.py` | 新增 `POST /tickets/{id}/satisfaction` 端点 | 修改 |
| `backend/app/services/report_service.py` | 更新满意度统计从 `tickets` 表聚合 | 修改 |
| `backend/tests/test_satisfaction.py` | 评价提交、触发、异常测试 | 创建 |

---

### Task 1: Alembic 迁移 — 新增 `satisfaction_at` 字段

**Files:**
- Create: `backend/alembic/versions/20260811_add_satisfaction_at.py`
- Modify: `backend/app/models/ticket.py`

**Interfaces:**
- Consumes: 现有 `tickets` 表已有 `satisfaction`, `satisfaction_note` 字段
- Produces: `Ticket.satisfaction_at` 字段映射

- [ ] **Step 1: 创建 Alembic 迁移文件**

```python
"""add satisfaction_at to tickets

Revision ID: 20260811_add_satisfaction_at
Revises: 40164b94b52f
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20260811_add_satisfaction_at'
down_revision: Union[str, None] = '40164b94b52f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('satisfaction_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'satisfaction_at')
```

- [ ] **Step 2: 更新 Ticket 模型**

在 `backend/app/models/ticket.py` 中，`Ticket` 类增加字段：

```python
closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
satisfaction_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 3: 运行迁移并验证**

```bash
cd backend
alembic upgrade 20260811_add_satisfaction_at
alembic history --verbose
```

Expected: 迁移成功，无报错。

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/20260811_add_satisfaction_at.py backend/app/models/ticket.py
git commit -m "feat(satisfaction): add satisfaction_at column to tickets via alembic migration"
```

---

### Task 2: 评价提交 API — Schema + Router + Service

**Files:**
- Modify: `backend/app/schemas/ticket.py`
- Modify: `backend/app/routers/tickets.py`
- Modify: `backend/app/services/ticket_service.py`

**Interfaces:**
- Consumes: `Ticket` 模型（含 `satisfaction_at`），`create_notification` service
- Produces: `POST /api/v1/tickets/{id}/satisfaction` 端点，`submit_satisfaction` service

- [ ] **Step 1: 新增 Pydantic Schema**

在 `backend/app/schemas/ticket.py` 末尾追加：

```python
class SatisfactionSubmit(BaseModel):
    rating: str = Field(..., pattern="^(satisfied|neutral|dissatisfied)$")
    note: Optional[str] = Field(None, max_length=500)


class SatisfactionInfo(BaseModel):
    rating: str
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

同时修改 `TicketResponse`：

```python
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
    satisfaction: Optional[SatisfactionInfo] = None
    sla: Optional[SLASummary] = None

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: 新增 `submit_satisfaction` service**

在 `backend/app/services/ticket_service.py` 中追加：

```python
from fastapi import HTTPException

async def submit_satisfaction(
    db: AsyncSession, ticket_id: int, user_id: int, rating: str, note: str | None
) -> Ticket:
    from sqlalchemy import select

    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    if ticket.requester_id != user_id:
        raise HTTPException(status_code=403, detail="只能评价自己的工单")

    if ticket.status != "closed":
        raise HTTPException(status_code=400, detail="工单未关闭，无法评价")

    if ticket.satisfaction_at is not None:
        raise HTTPException(status_code=400, detail="该工单已评价，不可修改")

    if rating not in ("satisfied", "neutral", "dissatisfied"):
        raise HTTPException(status_code=400, detail="无效的评价等级")

    ticket.satisfaction = rating
    ticket.satisfaction_note = (note[:500] if note else None)
    ticket.satisfaction_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 3: 新增 `POST /tickets/{id}/satisfaction` 端点**

在 `backend/app/routers/tickets.py` 中，`transition_ticket_status` 导入后，追加：

```python
from app.schemas.ticket import SatisfactionSubmit
from app.services.ticket_service import submit_satisfaction
from app.services.notification_service import create_notification

@router.post("/tickets/{ticket_id}/satisfaction", response_model=TicketResponse)
async def submit_satisfaction_endpoint(
    ticket_id: int,
    data: SatisfactionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = await submit_satisfaction(
        db, ticket_id, current_user.id, data.rating, data.note
    )
    return TicketResponse.model_validate(ticket)
```

- [ ] **Step 4: 修改 `TicketResponse` 序列化以嵌入评价**

由于 `TicketResponse.satisfaction` 是 `SatisfactionInfo` 类型，而模型中 `satisfaction` 是 `str`，需要自定义序列化。在 `TicketResponse` 中增加自定义序列化：

修改 `backend/app/routers/tickets.py` 中的 `get_ticket` 端点：

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

需要在 `TicketResponse` 的 `model_validate` 中处理 `satisfaction` 字段。由于 Pydantic v2 的 `from_attributes` 会自动处理，但 `satisfaction` 是 `str` 而 `SatisfactionInfo` 是对象，需要调整。改为在 `TicketResponse` 中保留 `satisfaction` 为 `str` 字段，增加 `satisfaction_info` 字段：

修改 `TicketResponse`：

```python
class TicketResponse(BaseModel):
    # ... 现有字段 ...
    satisfaction: Optional[str] = None
    satisfaction_note: Optional[str] = None
    satisfaction_at: Optional[datetime] = None
    sla: Optional[SLASummary] = None

    model_config = ConfigDict(from_attributes=True)
```

这样 `model_validate` 自动从模型属性映射，无需额外处理。

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/ticket.py backend/app/routers/tickets.py backend/app/services/ticket_service.py
git commit -m "feat(satisfaction): add satisfaction submit API and schema"
```

---

### Task 3: 关闭工单时触发评价邀请通知

**Files:**
- Modify: `backend/app/services/ticket_service.py`

**Interfaces:**
- Consumes: `create_notification` service, `Notification` 模型
- Produces: `transition_ticket_status` 在 `target_status == "closed"` 时自动发送通知

- [ ] **Step 1: 修改 `transition_ticket_status` 触发通知**

在 `backend/app/services/ticket_service.py` 中，修改 `transition_ticket_status` 函数：

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
        # 触发评价邀请
        from app.services.notification_service import create_notification
        await create_notification(
            db,
            user_id=ticket.requester_id,
            type="satisfaction_invite",
            title=f"工单 #{ticket.ticket_no} 已关闭，请评价我们的服务",
            message="您的工单已处理完毕，点击评价本次服务体验。",
            data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
        )

    if old_status == "resolved" and target_status == "in_progress":
        ticket.resolved_at = None
        sla = await get_sla_record_by_ticket_id(db, ticket.id)
        if sla:
            sla.resolved_at = None

    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/ticket_service.py
git commit -m "feat(satisfaction): trigger satisfaction invite notification on ticket close"
```

---

### Task 4: 更新报表满意度统计从 tickets 表聚合

**Files:**
- Modify: `backend/app/services/report_service.py`

**Interfaces:**
- Consumes: `tickets` 表 `satisfaction` 字段
- Produces: `get_satisfaction_report` 函数返回真实评价数据

- [ ] **Step 1: 修改满意度统计逻辑**

在 `backend/app/services/report_service.py` 中找到满意度统计函数，修改为从 `tickets` 表聚合：

```python
from sqlalchemy import select, func, case
from app.models.ticket import Ticket

async def get_satisfaction_report(db: AsyncSession, start: datetime, end: datetime):
    # 分布统计
    dist_stmt = (
        select(Ticket.satisfaction, func.count(Ticket.id))
        .where(Ticket.satisfaction.isnot(None))
        .where(Ticket.closed_at >= start)
        .where(Ticket.closed_at <= end)
        .group_by(Ticket.satisfaction)
    )
    dist_result = await db.execute(dist_stmt)
    distribution = {r[0]: r[1] for r in dist_result.all()}

    # 平均分（映射 3/2/1）
    avg_stmt = (
        select(
            func.avg(
                case(
                    (Ticket.satisfaction == "satisfied", 3),
                    (Ticket.satisfaction == "neutral", 2),
                    (Ticket.satisfaction == "dissatisfied", 1),
                    else_=0,
                )
            )
        )
        .where(Ticket.satisfaction.isnot(None))
        .where(Ticket.closed_at >= start)
        .where(Ticket.closed_at <= end)
    )
    avg_result = await db.execute(avg_stmt)
    avg_score = avg_result.scalar() or 0

    # 总评价数 + 总关闭数（计算参与率）
    total_evaluated = sum(distribution.values())
    total_closed_stmt = select(func.count(Ticket.id)).where(
        Ticket.status == "closed", Ticket.closed_at >= start, Ticket.closed_at <= end
    )
    total_closed_result = await db.execute(total_closed_stmt)
    total_closed = total_closed_result.scalar() or 0
    participation_rate = round(total_evaluated / total_closed * 100, 2) if total_closed else 0

    return {
        "participation_rate": participation_rate,
        "avg_score": round(avg_score, 2),
        "total_evaluated": total_evaluated,
        "distribution": {
            "satisfied": distribution.get("satisfied", 0),
            "neutral": distribution.get("neutral", 0),
            "dissatisfied": distribution.get("dissatisfied", 0),
        },
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/report_service.py
git commit -m "feat(satisfaction): update report satisfaction stats from tickets table"
```

---

### Task 5: 后端测试

**Files:**
- Create: `backend/tests/test_satisfaction.py`

**Interfaces:**
- Consumes: `client`, `db`, `customer_auth_headers`, `admin_auth_headers` fixtures
- Produces: 8 条测试全部通过

- [ ] **Step 1: 编写测试文件**

```python
from sqlalchemy import select

from app.models.category import Category
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate
from app.services.ticket_service import create_ticket, transition_ticket_status
from app.utils.security import get_password_hash


async def _create_category(db):
    category = Category(name="故障", code="bug", default_priority="P2")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def _create_closed_ticket(db, customer_id, category_id):
    ticket = Ticket(
        ticket_no="TK-20260811-0001",
        title="测试工单",
        description="描述",
        category_id=category_id,
        requester_id=customer_id,
        status="closed",
        priority="P2",
        source="web",
        closed_at=datetime.utcnow(),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


# === P0 正向 ===

# SAT-001: 客户对已关闭工单提交评价成功
async def test_submit_satisfaction_closed_ticket_200(client, customer_auth_headers, db):
    category = await _create_category(db)
    # 创建客户
    from sqlalchemy import select
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "satisfied", "note": "服务很好"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "satisfied"
    assert data["satisfaction_note"] == "服务很好"
    assert data["satisfaction_at"] is not None


# SAT-002: 评价 note 为空也可提交
async def test_submit_satisfaction_no_note_200(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "neutral"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["satisfaction"] == "neutral"
    assert data["satisfaction_note"] is None


# SAT-003: 关闭工单时触发通知
async def test_close_ticket_triggers_notification(client, admin_auth_headers, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    # 创建 open 工单
    from app.services.ticket_service import create_ticket
    from app.schemas.ticket import TicketCreate
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), customer.id
    )
    # 流转到 closed
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/status",
        headers=admin_auth_headers,
        json={"status": "closed"},
    )
    assert r.status_code == 200
    # 查询通知
    r = await client.get("/api/v1/notifications", headers=customer_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert any(n["type"] == "satisfaction_invite" for n in data["items"])


# === P0 异常 ===

# SAT-004: 未关闭工单提交评价 400
async def test_submit_satisfaction_open_ticket_400(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    from app.services.ticket_service import create_ticket
    from app.schemas.ticket import TicketCreate
    ticket = await create_ticket(
        db, TicketCreate(title="t", description="d", category_id=category.id, priority="P2"), customer.id
    )

    body = {"rating": "satisfied"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "未关闭" in r.json()["detail"]


# SAT-005: 非本人工单提交评价 403
async def test_submit_satisfaction_other_user_403(client, admin_auth_headers, db):
    category = await _create_category(db)
    # 创建另一个客户
    other = User(username="other", email="other@test.com", password_hash=get_password_hash("pass"), role="customer")
    db.add(other)
    await db.commit()
    await db.refresh(other)
    ticket = await _create_closed_ticket(db, other.id, category.id)

    body = {"rating": "satisfied"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=admin_auth_headers,  # admin 不是 requester
        json=body,
    )
    assert r.status_code == 403
    assert "只能评价自己的工单" in r.json()["detail"]


# SAT-006: 已评价工单再次提交 400
async def test_submit_satisfaction_already_rated_400(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)
    ticket.satisfaction = "satisfied"
    ticket.satisfaction_at = datetime.utcnow()
    await db.commit()

    body = {"rating": "neutral"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 400
    assert "已评价" in r.json()["detail"]


# SAT-007: 无效 rating 400
async def test_submit_satisfaction_invalid_rating_400(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "excellent"}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 422


# SAT-008: note 超长截断
async def test_submit_satisfaction_long_note_truncated(client, customer_auth_headers, db):
    category = await _create_category(db)
    customer = (await db.execute(select(User).where(User.username == "customer_test"))).scalar_one()
    ticket = await _create_closed_ticket(db, customer.id, category.id)

    body = {"rating": "satisfied", "note": "x" * 600}
    r = await client.post(
        f"/api/v1/tickets/{ticket.id}/satisfaction",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["satisfaction_note"]) == 500


```

- [ ] **Step 2: 运行测试**

```bash
cd backend
pytest tests/test_satisfaction.py -v
```

Expected: 8 passed, 0 failed

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_satisfaction.py
git commit -m "test(satisfaction): add 8 backend tests for satisfaction evaluation"
```

---

### Task 6: 前端评价弹窗（M2-T19）

**Files:**
- Modify: `frontend/src/views/customer/TicketDetailView.vue`

**Interfaces:**
- Consumes: `POST /api/v1/tickets/{id}/satisfaction` API
- Produces: 客户详情页底部评价区域（邀请/表单/结果展示）

- [ ] **Step 1: 在客户工单详情页增加评价区域**

在 `frontend/src/views/customer/TicketDetailView.vue` 中，工单详情底部增加：

```vue
<template>
  <!-- 现有工单详情内容 -->
  
  <!-- 评价区域 -->
  <div v-if="ticket.status === 'closed'" class="satisfaction-section">
    <!-- 未评价：邀请卡片 -->
    <el-card v-if="!ticket.satisfaction" class="satisfaction-card">
      <template #header>
        <span>请评价本次服务</span>
      </template>
      <div class="rating-buttons">
        <el-button
          v-for="opt in ratingOptions"
          :key="opt.value"
          :type="selectedRating === opt.value ? 'primary' : 'default'"
          size="large"
          @click="selectedRating = opt.value"
        >
          {{ opt.icon }} {{ opt.label }}
        </el-button>
      </div>
      <el-input
        v-if="selectedRating"
        v-model="satisfactionNote"
        type="textarea"
        :rows="3"
        placeholder="您的反馈对我们很重要（选填，最多500字）"
        maxlength="500"
        show-word-limit
        class="note-input"
      />
      <el-button
        v-if="selectedRating"
        type="primary"
        @click="submitSatisfaction"
        :loading="submitting"
      >
        提交评价
      </el-button>
    </el-card>

    <!-- 已评价：展示卡片 -->
    <el-card v-else class="satisfaction-card">
      <template #header>
        <span>您的评价</span>
      </template>
      <div class="rating-display">
        <span class="rating-icon">{{ getRatingIcon(ticket.satisfaction) }}</span>
        <span class="rating-label">{{ getRatingLabel(ticket.satisfaction) }}</span>
      </div>
      <p v-if="ticket.satisfaction_note" class="rating-note">{{ ticket.satisfaction_note }}</p>
      <p class="rating-time">评价时间：{{ formatDate(ticket.satisfaction_at) }}</p>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useTicketsStore } from '@/stores/tickets'
import { ElMessage } from 'element-plus'

const route = useRoute()
const ticketsStore = useTicketsStore()

const selectedRating = ref('')
const satisfactionNote = ref('')
const submitting = ref(false)

const ratingOptions = [
  { value: 'satisfied', label: '满意', icon: '😊' },
  { value: 'neutral', label: '一般', icon: '😐' },
  { value: 'dissatisfied', label: '不满意', icon: '😞' },
]

const getRatingIcon = (rating) => ratingOptions.find(o => o.value === rating)?.icon || ''
const getRatingLabel = (rating) => ratingOptions.find(o => o.value === rating)?.label || ''

const submitSatisfaction = async () => {
  submitting.value = true
  try {
    await ticketsStore.submitSatisfaction(route.params.id, {
      rating: selectedRating.value,
      note: satisfactionNote.value,
    })
    ElMessage.success('评价提交成功，感谢您的反馈！')
    await ticketsStore.fetchTicket(route.params.id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.satisfaction-section { margin-top: 24px; }
.satisfaction-card { margin-top: 16px; }
.rating-buttons { display: flex; gap: 12px; margin-bottom: 16px; }
.note-input { margin-bottom: 16px; }
.rating-display { display: flex; align-items: center; gap: 8px; font-size: 18px; }
.rating-icon { font-size: 24px; }
.rating-note { color: #666; margin-top: 8px; }
.rating-time { color: #999; font-size: 12px; margin-top: 8px; }
</style>
```

- [ ] **Step 2: 在 tickets store 增加 submitSatisfaction action**

在 `frontend/src/stores/tickets.js` 中增加：

```javascript
async submitSatisfaction(ticketId, data) {
  const response = await api.post(`/tickets/${ticketId}/satisfaction`, data)
  return response.data
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/customer/TicketDetailView.vue frontend/src/stores/tickets.js
git commit -m "feat(satisfaction): add customer satisfaction rating UI"
```

---

## Self-Review Checklist

| Spec 要求 | 对应 Task | 状态 |
|-----------|-----------|------|
| 工单关闭后触发评价邀请通知 | Task 3 | ✅ 通过 `transition_ticket_status` 触发 `create_notification` |
| 客户提交评价（满意/一般/不满意） | Task 2 | ✅ `POST /tickets/{id}/satisfaction` 端点 |
| 可选文字反馈 | Task 2 | ✅ `note` 字段，最大 500 字 |
| 已评价不可修改 | Task 2 | ✅ `satisfaction_at` 非空则拒绝 |
| 评价数据用于报表统计 | Task 4 | ✅ 从 `tickets` 表聚合 |
| 前端评价弹窗 | Task 6 | ✅ 客户详情页嵌入 |

**Placeholder scan:** 无 TBD/TODO/"implement later"
**Type consistency:** `TicketResponse` 中 `satisfaction`/`satisfaction_note`/`satisfaction_at` 与模型字段一致

