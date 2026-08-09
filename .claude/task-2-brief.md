# Task 2 Brief: SLA Rule Engine Integration

## Where This Fits

This is Task 2 of 6 for T006. Task 1 created the models. This task builds the SLA rule engine (create record, resolve config, capture first-response and resolution times) and integrates it into existing services.

## Interfaces from Task 1

- `SLARecord` model at `app.models.sla_record`
- `Category.sla_config` is now `JSONB` and should be nested format, but may still be flat for old rows

## Requirements

### Step 1: Create `backend/app/services/sla_service.py`

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

### Step 2: Modify `backend/app/services/ticket_service.py`

Add import: `from app.services.sla_service import create_sla_record`

Modify `create_ticket()`:
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

Add import: `from app.services.sla_service import get_sla_record_by_ticket_id`

Modify `transition_ticket_status()`:
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

### Step 3: Modify `backend/app/services/reply_service.py`

Add imports:
```python
from datetime import datetime
from app.services.sla_service import get_sla_record_by_ticket_id
```

Modify `create_reply()` signature and body:
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

### Step 4: Modify `backend/app/routers/tickets.py`

In `reply_ticket` endpoint, change:
```python
    is_agent_reply = current_user.role in ("agent", "supervisor", "admin") and not data.is_internal
    reply = await create_reply(db, ticket, data, current_user.id, is_agent_reply=is_agent_reply)
```

### Step 5: Modify `backend/app/schemas/category.py`

Change `sla_config` default to nested format:
```python
    sla_config: dict = Field(
        default_factory=lambda: {
            "P0": {"first_resp_hours": 1, "resolution_hours": 4},
            "P1": {"first_resp_hours": 4, "resolution_hours": 24},
            "P2": {"first_resp_hours": 8, "resolution_hours": 48},
            "P3": {"first_resp_hours": 24, "resolution_hours": 72},
        }
    )
```

### Step 6-7: Write tests in `backend/tests/test_sla.py`

Write these tests (append to existing file):
- `test_create_ticket_auto_creates_sla` — 验证 create_ticket 自动生成 SLA，且使用 category 配置
- `test_create_ticket_uses_default_sla_when_category_empty` — 验证空配置时使用 DEFAULT_SLA
- `test_create_ticket_compat_flat_sla_config` — 验证旧 flat 格式兼容
- `test_agent_reply_sets_first_resp_at` — agent 非内部回复时设置 first_resp_at
- `test_internal_reply_does_not_set_first_resp_at` — 内部备注不设置
- `test_transition_to_resolved_sets_resolved_at` — resolved 时设置 resolved_at
- `test_reopen_clears_resolved_at` — resolved→in_progress 时清空 resolved_at

Run: `pytest -p no:anyio tests/test_sla.py -v`
Expected: all tests PASS

### Step 8: Commit

```bash
git add backend/app/services/sla_service.py backend/app/services/ticket_service.py backend/app/services/reply_service.py backend/app/routers/tickets.py backend/app/schemas/category.py backend/tests/test_sla.py
git commit -m "feat(t006): SLA rule engine with create, first-response and resolution capture"
```

## Global Constraints

- Do NOT change `create_ticket()`'s external contract (same params, same return type).
- `create_ticket()` already does `db.commit()` then `db.refresh()`; create the SLA record after the first commit, then do a second commit. This is acceptable.
- `transition_ticket_status()` already exists; extend it, don't rewrite it.
- `create_reply()` already exists; extend signature with `is_agent_reply=False` default to maintain backward compatibility.
- `reply_ticket` endpoint must determine `is_agent_reply` based on `current_user.role` and `data.is_internal`.
- All tests use `-p no:anyio`.
- Do NOT modify any files not listed above.

## Report

Write your report to `.claude/task-2-report.md` with status, files touched, test command + output, concerns.
