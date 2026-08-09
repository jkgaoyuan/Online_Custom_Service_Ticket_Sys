# Task 1 Brief: SLA and Notification Models + Alembic Migration

## Where This Fits

This is Task 1 of 6 for T006 (SLA Management and Timeout Monitoring). It creates the two new database tables (`sla_records`, `notifications`) and the Alembic migration to add them. All later tasks depend on these models existing.

## Requirements (verbatim from plan)

### Step 1: Create `backend/app/models/sla_record.py`

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

### Step 2: Create `backend/app/models/notification.py`

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

### Step 3: Update `backend/app/models/__init__.py`

Add imports for `Notification` and `SLARecord`. Keep existing imports.

### Step 4: Write Alembic migration

Create `backend/alembic/versions/xxxx_add_sla_and_notification_tables.py` with:
1. `sla_records` table with all columns, `ticket_id` UNIQUE + FK, primary key, two partial indexes
2. `notifications` table with all columns, `user_id` FK, primary key, one partial index
3. Alter `categories.sla_config` from `JSON` to `JSONB`
4. Data migration: if flat format detected (`sla_config ? 'first_resp_hours' AND NOT sla_config ? 'P0'`), wrap into nested format for all priorities P0-P3

Use `alembic revision --autogenerate -m "add sla_records and notifications tables, migrate sla_config to jsonb"` then manually adjust. Down-revision must be `6a1b2c3d4e5f` (current head). Fix the generated migration to include the data migration SQL.

### Step 5-7: Write test `backend/tests/test_sla.py`

Write `test_sla_record_model` that:
- Creates a user, category, ticket
- Creates an `SLARecord` directly via SQLAlchemy
- Asserts all fields are correct

Run test with: `pytest -p no:anyio tests/test_sla.py::test_sla_record_model -v`

### Step 8: Commit

```bash
git add backend/app/models/sla_record.py backend/app/models/notification.py backend/app/models/__init__.py backend/alembic/versions/xxxx_add_sla_and_notification_tables.py backend/tests/test_sla.py
git commit -m "feat(t006): add SLARecord and Notification models with migration"
```

## Global Constraints

- Python 3.10.10, pytest with `-p no:anyio`
- Use `from sqlalchemy.dialects.postgresql import JSONB` for Notification.data
- Do NOT change any existing models or routers beyond what's listed
- Base = `app.database.Base`
- Ticket model already exists at `app.models.ticket`
- User model already exists at `app.models.user`
- Category model already exists at `app.models.category` with `sla_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)` — migration must change this to JSONB
- Alembic is already set up in `backend/alembic/`

## Report

Write your report to `.claude/task-1-report.md` with:
1. Status (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED)
2. Files created/modified
3. Test results (command + output)
4. Any concerns
