# Task 5 Brief: SLA Query API and Embedding

## Where This Fits

This is Task 5 of 6 for T006. Tasks 1-4 created models, engine, notifications, and Celery scan. This task adds the REST endpoints for querying SLA data and embeds a summary into ticket responses.

## Interfaces from Earlier Tasks

- `SLARecord` model at `app.models.sla_record`
- `get_sla_record_by_ticket_id()` at `app.services.sla_service`
- `TicketResponse` schema at `app.schemas.ticket`
- `check_ticket_access()` helper at `app.routers.tickets`

## Requirements

### Step 1: Create `backend/app/schemas/sla.py`

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

### Step 2: Create `backend/app/routers/sla.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.exceptions import NotFoundException
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

### Step 3: Modify `backend/app/schemas/ticket.py`

Add import:
```python
from app.schemas.sla import SLASummary
```

Add field to `TicketResponse`:
```python
    sla: Optional[SLASummary] = None
```

### Step 4: Modify `backend/app/routers/tickets.py`

Add imports:
```python
from app.schemas.sla import SLASummary
from app.services.sla_service import get_sla_record_by_ticket_id
```

Modify `get_ticket` endpoint to embed SLA:
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

Note: `list_tickets` does NOT embed SLA to avoid N+1. Only detail view embeds.

### Step 5: Modify `backend/app/main.py`

Register the sla router:
```python
from app.routers import auth, categories, dispatch, notifications, sla, tickets, webhooks
```

```python
app.include_router(sla.router, prefix="/api/v1", tags=["SLA"])
```

### Step 6-7: Write tests in `backend/tests/test_sla.py`

Append these tests:
- `test_api_get_ticket_sla` — GET /api/v1/tickets/{id}/sla returns 200 with correct fields
- `test_api_get_ticket_sla_forbidden` — customer cannot access another customer's ticket SLA (403)
- `test_api_admin_overdue_list` — admin GET /api/v1/admin/sla/overdue returns breached SLAs
- `test_ticket_detail_includes_sla_summary` — GET /api/v1/tickets/{id} includes `sla` field

Run: `pytest -p no:anyio tests/test_sla.py -v`
Expected: all tests PASS (including Task 1 and Task 2 tests)

### Step 8: Commit

```bash
git add backend/app/routers/sla.py backend/app/schemas/sla.py backend/app/routers/tickets.py backend/app/schemas/ticket.py backend/app/main.py backend/tests/test_sla.py
git commit -m "feat(t006): SLA query API and ticket detail embedding"
```

## Global Constraints

- `check_ticket_access()` already handles customer/agent permissions; reuse it.
- `require_role("admin", "supervisor")` for admin endpoints.
- `TicketResponse` must remain backward compatible for list view (no SLA there).
- All tests use `-p no:anyio`.
- Do NOT modify any files not listed above.

## Report

Write your report to `.claude/task-5-report.md` with status, files touched, test command + output, concerns.
