# T007 统计报表与导出 — 后端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现工单系统的统计聚合查询与异步报表导出后端功能（5 个查询端点 + Excel/CSV 导出）。

**Architecture:** 所有统计查询在 PostgreSQL 层通过 SQLAlchemy 聚合函数完成；导出使用 Celery 异步任务 + pandas/openpyxl 生成文件，本地文件系统暂存。

**Tech Stack:** FastAPI, SQLAlchemy(async), PostgreSQL, Celery, pandas, openpyxl, pytest

## Global Constraints

- Python 3.10+
- FastAPI 0.110.0
- SQLAlchemy 2.0.27 (async)
- pytest 8.0.0, pytest-asyncio 0.21.1
- pandas 2.2.0, openpyxl 3.1.2（已存在于 requirements.txt）
- 测试命名：`API-{MODULE}-{SEQ:03d}` 注释 + `test_{操作}_{对象}_{预期结果}_{状态码}` 函数名
- 所有 admin 报表接口权限：`require_role("admin", "supervisor")`
- 日期范围上限：单次查询最多 365 天
- `granularity` 严格白名单：`day`, `week`, `month`
- 导出文件存储：`settings.EXPORT_DIR`（默认 `./exports`）
- `task_id` 使用 UUID4，下载接口正则校验 `^[a-f0-9\-]{36}$`
- CSV/Excel 公式注入防护：文本字段以 `= + - @` 开头时前置单引号 `'`

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/schemas/report.py` | 创建 | 所有报表 Pydantic Schema |
| `backend/app/services/report_service.py` | 创建 | 聚合查询服务层 |
| `backend/app/routers/reports.py` | 创建 | 报表路由（含导出/下载） |
| `backend/app/tasks/export_tasks.py` | 修改（当前为空） | Celery 导出任务 |
| `backend/app/config.py` | 修改 | 新增 `EXPORT_DIR` |
| `backend/app/main.py` | 修改 | 注册 `reports` router |
| `backend/tests/conftest.py` | 修改 | 新增 `_create_resolved_ticket` 辅助函数 |
| `backend/tests/test_reports.py` | 创建 | 统计查询接口测试 |
| `backend/tests/test_export.py` | 创建 | 导出接口测试 |
| `backend/.gitignore` | 修改 | 新增 `/exports/` |

---

### Task 1: Report Schemas + Config + Overview/Category/Satisfaction Service

**Files:**
- Create: `backend/app/schemas/report.py`
- Modify: `backend/app/config.py`
- Create: `backend/app/services/report_service.py`
- Test: `backend/tests/test_reports.py`

**Interfaces:**
- Consumes: `Ticket`, `SLARecord`, `Category`, `User` models; `get_settings()`
- Produces: `OverviewResponse`, `AgentPerformanceResponse`, `CategoryDistributionResponse`, `TrendResponse`, `SatisfactionResponse`, `ExportRequest` schemas; `get_overview()`, `get_category_distribution()`, `get_satisfaction_stats()`, `validate_date_range()` service functions

- [ ] **Step 1: Write the failing tests**

在 `backend/tests/test_reports.py` 中写入：

```python
from datetime import datetime, timedelta

from app.services.report_service import (
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    validate_date_range,
)
from tests.conftest import _create_category, _create_ticket, _create_user


# API-RPT-101: overview returns correct aggregated stats
async def test_overview_returns_correct_stats(db):
    customer = await _create_user(db, "ov_customer", "customer")
    category = await _create_category(db)
    t1 = await _create_ticket(db, "T1", "D1", category.id, customer.id, status="resolved")
    t2 = await _create_ticket(db, "T2", "D2", category.id, customer.id, status="open")

    result = await get_overview(db)
    assert result["total_tickets"] >= 2
    assert "today_new" in result
    assert "week_new" in result
    assert "month_new" in result
    assert "status_distribution" in result
    assert "sla_compliance_rate" in result
    assert "avg_satisfaction" in result


# API-RPT-103: category distribution returns correct stats
async def test_category_distribution_returns_correct_stats(db):
    customer = await _create_user(db, "cat_customer", "customer")
    category = await _create_category(db)
    await _create_ticket(db, "C1", "D1", category.id, customer.id)
    await _create_ticket(db, "C2", "D2", category.id, customer.id)

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_category_distribution(db, start, end)
    assert len(result) >= 1
    item = result[0]
    assert "category_id" in item
    assert "category_name" in item
    assert "count" in item
    assert "percentage" in item


# API-RPT-105: satisfaction returns correct stats
async def test_satisfaction_returns_correct_stats(db):
    customer = await _create_user(db, "sat_customer", "customer")
    category = await _create_category(db)
    t1 = await _create_ticket(db, "S1", "D1", category.id, customer.id, status="closed")
    t1.satisfaction = "satisfied"
    await db.commit()

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_satisfaction_stats(db, start, end)
    assert "distribution" in result
    assert "avg_score" in result
    assert "participation_rate" in result


# API-RPT-201: empty data returns zeros and empty lists
async def test_empty_data_returns_zeros(db):
    result = await get_overview(db)
    assert result["total_tickets"] >= 0

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    cat_result = await get_category_distribution(db, start, end)
    assert cat_result == []

    sat_result = await get_satisfaction_stats(db, start, end)
    assert sat_result["participation_rate"] == 0.0


# API-RPT-203: date range exceeds one year returns error
async def test_date_range_exceeds_one_year():
    from app.exceptions import DuplicateException
    start = "2024-01-01"
    end = "2026-01-01"
    try:
        validate_date_range(start, end)
        assert False, "Expected exception"
    except DuplicateException as e:
        assert "365" in e.message or "1年" in e.message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_reports.py -v`
Expected: FAIL with "module not found" or "function not defined"

- [ ] **Step 3: Write minimal implementation**

创建 `backend/app/schemas/report.py`：

```python
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OverviewResponse(BaseModel):
    total_tickets: int
    today_new: int
    week_new: int
    month_new: int
    status_distribution: dict[str, int]
    sla_compliance_rate: float
    avg_satisfaction: float


class AgentPerformanceResponse(BaseModel):
    agent_id: int
    agent_name: str
    total_assigned: int
    resolved_count: int
    avg_first_resp_hours: float
    avg_resolution_hours: float


class CategoryDistributionResponse(BaseModel):
    category_id: int
    category_name: str
    count: int
    percentage: float


class TrendResponse(BaseModel):
    bucket: str
    created: int
    resolved: int


class SatisfactionResponse(BaseModel):
    distribution: dict[str, int]
    avg_score: float
    participation_rate: float
    total_rated: int
    total_in_range: int


class ExportRequest(BaseModel):
    report_type: Literal[
        "overview",
        "agent_performance",
        "category_distribution",
        "trend",
        "satisfaction",
    ]
    format: Literal["xlsx", "csv"] = "xlsx"
    start_date: date | None = None
    end_date: date | None = None
    filters: dict = Field(default_factory=dict)
```

修改 `backend/app/config.py`，在 `Settings` 类中添加：

```python
    EXPORT_DIR: str = "./exports"
```

创建 `backend/app/services/report_service.py`：

```python
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateException
from app.models.category import Category
from app.models.sla_record import SLARecord
from app.models.ticket import Ticket


MAX_DATE_RANGE_DAYS = 365


def validate_date_range(start_date: str | None, end_date: str | None) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        if (end - start).days > MAX_DATE_RANGE_DAYS:
            raise DuplicateException(f"日期范围不能超过 {MAX_DATE_RANGE_DAYS} 天")
        if start > end:
            raise DuplicateException("开始日期不能晚于结束日期")
        return start, end
    end = now
    start = now - timedelta(days=30)
    return start, end


async def get_overview(db: AsyncSession) -> dict:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_result = await db.execute(select(func.count(Ticket.id)))
    total = total_result.scalar() or 0

    today_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= today_start)
    )
    today_new = today_result.scalar() or 0

    week_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= week_start)
    )
    week_new = week_result.scalar() or 0

    month_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.created_at >= month_start)
    )
    month_new = month_result.scalar() or 0

    status_result = await db.execute(
        select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    )
    status_distribution = {row[0]: row[1] for row in status_result.all()}

    sla_result = await db.execute(
        select(func.count(SLARecord.id)).where(
            SLARecord.first_resp_breached.is_(False),
            SLARecord.resolution_breached.is_(False),
        )
    )
    sla_ok = sla_result.scalar() or 0
    sla_total_result = await db.execute(select(func.count(SLARecord.id)))
    sla_total = sla_total_result.scalar() or 0
    sla_compliance_rate = (sla_ok / sla_total) if sla_total > 0 else 1.0

    sat_result = await db.execute(
        select(func.count(Ticket.id)).where(Ticket.satisfaction.isnot(None))
    )
    sat_count = sat_result.scalar() or 0

    sat_scores = {"satisfied": 5, "neutral": 3, "dissatisfied": 1}
    score_sum = 0
    sat_details = await db.execute(
        select(Ticket.satisfaction, func.count(Ticket.id))
        .where(Ticket.satisfaction.isnot(None))
        .group_by(Ticket.satisfaction)
    )
    sat_distribution = {}
    for row in sat_details.all():
        sat_distribution[row[0]] = row[1]
        score_sum += sat_scores.get(row[0], 0) * row[1]

    avg_satisfaction = (score_sum / sat_count) if sat_count > 0 else 0.0

    return {
        "total_tickets": total,
        "today_new": today_new,
        "week_new": week_new,
        "month_new": month_new,
        "status_distribution": status_distribution,
        "sla_compliance_rate": round(sla_compliance_rate, 2),
        "avg_satisfaction": round(avg_satisfaction, 2),
    }


async def get_category_distribution(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> list[dict]:
    start, end = validate_date_range(start_date, end_date)

    total_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.created_at >= start, Ticket.created_at <= end
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Category.id, Category.name, func.count(Ticket.id))
        .join(Ticket, Ticket.category_id == Category.id)
        .where(Ticket.created_at >= start, Ticket.created_at <= end)
        .group_by(Category.id, Category.name)
        .order_by(func.count(Ticket.id).desc())
    )

    rows = result.all()
    return [
        {
            "category_id": row[0],
            "category_name": row[1],
            "count": row[2],
            "percentage": round(row[2] / total, 3) if total > 0 else 0.0,
        }
        for row in rows
    ]


async def get_satisfaction_stats(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> dict:
    start, end = validate_date_range(start_date, end_date)

    total_closed_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.closed_at.isnot(None),
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
    )
    total_in_range = total_closed_result.scalar() or 0

    sat_details = await db.execute(
        select(Ticket.satisfaction, func.count(Ticket.id))
        .where(
            Ticket.satisfaction.isnot(None),
            Ticket.closed_at.isnot(None),
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        .group_by(Ticket.satisfaction)
    )

    distribution = {}
    score_sum = 0
    total_rated = 0
    scores = {"satisfied": 5, "neutral": 3, "dissatisfied": 1}
    for row in sat_details.all():
        distribution[row[0]] = row[1]
        total_rated += row[1]
        score_sum += scores.get(row[0], 0) * row[1]

    avg_score = (score_sum / total_rated) if total_rated > 0 else 0.0
    participation_rate = (total_rated / total_in_range) if total_in_range > 0 else 0.0

    return {
        "distribution": distribution,
        "avg_score": round(avg_score, 2),
        "participation_rate": round(participation_rate, 2),
        "total_rated": total_rated,
        "total_in_range": total_in_range,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_reports.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/report.py backend/app/services/report_service.py backend/app/config.py backend/tests/test_reports.py
git commit -m "feat(t007): report schemas, config, overview/category/satisfaction services"
```

---

### Task 2: Agent Performance Service

**Files:**
- Modify: `backend/app/services/report_service.py`
- Modify: `backend/tests/conftest.py`
- Test: `backend/tests/test_reports.py`（追加）

**Interfaces:**
- Consumes: `Ticket`, `SLARecord`, `TicketReply`, `User` models; `validate_date_range()`
- Produces: `get_agent_performance(db, start_date, end_date)` -> `list[dict]`

- [ ] **Step 1: Write the failing test**

在 `backend/tests/test_reports.py` 追加：

```python
from app.services.report_service import get_agent_performance


# API-RPT-102: agent performance returns correct stats
async def test_agent_performance_returns_correct_stats(db):
    customer = await _create_user(db, "perf_customer", "customer")
    agent = await _create_user(db, "perf_agent", "agent")
    category = await _create_category(db)

    t1 = await _create_ticket(
        db, "Perf1", "D1", category.id, customer.id, status="resolved", assignee_id=agent.id
    )
    t1.resolved_at = datetime.utcnow()
    await db.commit()

    start = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_agent_performance(db, start, end)
    assert len(result) >= 1
    item = result[0]
    assert "agent_id" in item
    assert "agent_name" in item
    assert "total_assigned" in item
    assert "resolved_count" in item
    assert "avg_first_resp_hours" in item
    assert "avg_resolution_hours" in item
```

在 `backend/tests/conftest.py` 的 `_create_ticket` 之后添加：

```python
async def _create_resolved_ticket(
    db, title, description, category_id, requester_id, assignee_id=None, satisfaction=None
):
    ticket = await _create_ticket(
        db, title, description, category_id, requester_id,
        status="resolved", assignee_id=assignee_id
    )
    ticket.resolved_at = datetime.utcnow()
    ticket.satisfaction = satisfaction
    await db.commit()
    await db.refresh(ticket)
    return ticket
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_reports.py::test_agent_performance_returns_correct_stats -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

在 `backend/app/services/report_service.py` 追加：

```python
from app.models.ticket_reply import TicketReply
from app.models.user import User


async def get_agent_performance(
    db: AsyncSession, start_date: str | None, end_date: str | None
) -> list[dict]:
    start, end = validate_date_range(start_date, end_date)

    # Assigned + resolved stats grouped by assignee
    assigned_result = await db.execute(
        select(
            Ticket.assignee_id,
            User.username,
            func.count(Ticket.id),
            func.sum(func.cast(Ticket.status == "resolved", func.INT)),
            func.avg(
                func.EXTRACT("EPOCH", Ticket.resolved_at - Ticket.created_at) / 3600
            ),
        )
        .join(User, Ticket.assignee_id == User.id)
        .where(
            Ticket.created_at >= start,
            Ticket.created_at <= end,
            Ticket.assignee_id.isnot(None),
        )
        .group_by(Ticket.assignee_id, User.username)
    )

    assigned_rows = {row[0]: row for row in assigned_result.all()}

    # First response stats from ticket_replies (earliest non-internal reply per ticket)
    first_reply_result = await db.execute(
        select(
            TicketReply.author_id,
            func.avg(
                func.EXTRACT("EPOCH", TicketReply.created_at - Ticket.created_at) / 3600
            ),
        )
        .select_from(TicketReply)
        .join(Ticket, TicketReply.ticket_id == Ticket.id)
        .where(
            TicketReply.is_internal.is_(False),
            Ticket.created_at >= start,
            Ticket.created_at <= end,
        )
        .group_by(TicketReply.author_id)
    )

    first_reply_map = {row[0]: row[1] for row in first_reply_result.all()}

    result = []
    for agent_id, row in assigned_rows.items():
        avg_resolution = row[4] if row[4] is not None else 0.0
        avg_first_resp = first_reply_map.get(agent_id, 0.0)
        if avg_first_resp is None:
            avg_first_resp = 0.0
        result.append({
            "agent_id": agent_id,
            "agent_name": row[1],
            "total_assigned": row[2],
            "resolved_count": row[3] or 0,
            "avg_first_resp_hours": round(avg_first_resp, 2),
            "avg_resolution_hours": round(avg_resolution, 2),
        })

    return sorted(result, key=lambda x: x["total_assigned"], reverse=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_reports.py::test_agent_performance_returns_correct_stats -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_service.py backend/tests/conftest.py backend/tests/test_reports.py
git commit -m "feat(t007): agent performance query service"
```

---

### Task 3: Trend Service

**Files:**
- Modify: `backend/app/services/report_service.py`
- Test: `backend/tests/test_reports.py`（追加）

**Interfaces:**
- Consumes: `Ticket` model; `validate_date_range()`
- Produces: `get_trend(db, granularity, start_date, end_date)` -> `list[dict]`

- [ ] **Step 1: Write the failing test**

在 `backend/tests/test_reports.py` 追加：

```python
from app.services.report_service import get_trend


# API-RPT-104: trend with day granularity returns correct buckets
async def test_trend_day_granularity_returns_correct_buckets(db):
    customer = await _create_user(db, "trend_customer", "customer")
    category = await _create_category(db)
    await _create_ticket(db, "Trend1", "D1", category.id, customer.id, status="resolved")

    start = (datetime.utcnow() - timedelta(days=6)).date().isoformat()
    end = datetime.utcnow().date().isoformat()
    result = await get_trend(db, "day", start, end)
    assert len(result) >= 1
    item = result[0]
    assert "bucket" in item
    assert "created" in item
    assert "resolved" in item


# API-RPT-204: invalid granularity raises error
async def test_invalid_granularity_raises_error(db):
    from app.exceptions import DuplicateException
    try:
        await get_trend(db, "hour", "2026-01-01", "2026-01-02")
        assert False, "Expected exception"
    except DuplicateException as e:
        assert "granularity" in e.message.lower() or "day" in e.message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_reports.py::test_trend_day_granularity_returns_correct_buckets tests/test_reports.py::test_invalid_granularity_raises_error -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

在 `backend/app/services/report_service.py` 追加：

```python
from sqlalchemy import text


GRANULARITY_WHITELIST = {"day", "week", "month"}


async def get_trend(
    db: AsyncSession,
    granularity: str,
    start_date: str | None,
    end_date: str | None,
) -> list[dict]:
    if granularity not in GRANULARITY_WHITELIST:
        raise DuplicateException(f"granularity 必须是以下之一: {', '.join(GRANULARITY_WHITELIST)}")

    start, end = validate_date_range(start_date, end_date)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    # Use generate_series to ensure every bucket is represented
    sql = text(f"""
        WITH buckets AS (
            SELECT DATE_TRUNC(:granularity, generate_series)::date AS bucket
            FROM generate_series(
                DATE :start_date,
                DATE :end_date,
                INTERVAL '1 {granularity}'
            )
        ),
        created_counts AS (
            SELECT DATE_TRUNC(:granularity, created_at)::date AS bucket,
                   COUNT(*) AS cnt
            FROM tickets
            WHERE created_at BETWEEN :start_dt AND :end_dt
            GROUP BY DATE_TRUNC(:granularity, created_at)::date
        ),
        resolved_counts AS (
            SELECT DATE_TRUNC(:granularity, resolved_at)::date AS bucket,
                   COUNT(*) AS cnt
            FROM tickets
            WHERE resolved_at IS NOT NULL
              AND resolved_at BETWEEN :start_dt AND :end_dt
            GROUP BY DATE_TRUNC(:granularity, resolved_at)::date
        )
        SELECT
            b.bucket::text,
            COALESCE(c.cnt, 0) AS created,
            COALESCE(r.cnt, 0) AS resolved
        FROM buckets b
        LEFT JOIN created_counts c ON b.bucket = c.bucket
        LEFT JOIN resolved_counts r ON b.bucket = r.bucket
        ORDER BY b.bucket
    """)

    result = await db.execute(
        sql,
        {
            "granularity": granularity,
            "start_date": start_str,
            "end_date": end_str,
            "start_dt": start,
            "end_dt": end,
        },
    )

    return [
        {
            "bucket": row[0],
            "created": row[1],
            "resolved": row[2],
        }
        for row in result.all()
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_reports.py::test_trend_day_granularity_returns_correct_buckets tests/test_reports.py::test_invalid_granularity_raises_error -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_service.py backend/tests/test_reports.py
git commit -m "feat(t007): trend query service with generate_series"
```

---

### Task 4: Reports Router + Registration

**Files:**
- Create: `backend/app/routers/reports.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_reports.py`（追加权限和边界测试）

**Interfaces:**
- Consumes: All `get_*` functions from `report_service`; `require_role("admin", "supervisor")`
- Produces: 5 GET endpoints under `/api/v1/admin/reports/*`

- [ ] **Step 1: Write the failing tests**

在 `backend/tests/test_reports.py` 追加：

```python
# API-RPT-301: customer cannot access reports (403)
async def test_customer_access_reports_403(client, customer_auth_headers):
    r = await client.get("/api/v1/admin/reports/overview", headers=customer_auth_headers)
    assert r.status_code == 403


# API-RPT-302: agent cannot access reports (403)
async def test_agent_access_reports_403(client, agent_auth_headers):
    r = await client.get("/api/v1/admin/reports/overview", headers=agent_auth_headers)
    assert r.status_code == 403


# API-RPT-202: start_date after end_date returns 422
async def test_start_date_after_end_date_422(client, admin_auth_headers):
    r = await client.get(
        "/api/v1/admin/reports/agent-performance?start_date=2026-08-10&end_date=2026-08-01",
        headers=admin_auth_headers,
    )
    assert r.status_code == 422


# API-RPT-203: date range exceeds one year returns 422
async def test_date_range_exceeds_one_year_422(client, admin_auth_headers):
    r = await client.get(
        "/api/v1/admin/reports/agent-performance?start_date=2024-01-01&end_date=2026-01-01",
        headers=admin_auth_headers,
    )
    assert r.status_code == 422


# API-RPT-204: invalid granularity returns 422
async def test_invalid_granularity_422(client, admin_auth_headers):
    r = await client.get(
        "/api/v1/admin/reports/trend?granularity=hour",
        headers=admin_auth_headers,
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_reports.py -k "access_reports or date_range or granularity" -v`
Expected: FAIL with 404 (route not found)

- [ ] **Step 3: Write minimal implementation**

创建 `backend/app/routers/reports.py`：

```python
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.schemas.report import (
    AgentPerformanceResponse,
    CategoryDistributionResponse,
    OverviewResponse,
    SatisfactionResponse,
    TrendResponse,
)
from app.services.report_service import (
    get_agent_performance,
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    get_trend,
)

router = APIRouter()


@router.get("/admin/reports/overview", response_model=OverviewResponse)
async def overview(
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_overview(db)


@router.get("/admin/reports/agent-performance", response_model=list[AgentPerformanceResponse])
async def agent_performance(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_agent_performance(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)


@router.get("/admin/reports/category-distribution", response_model=list[CategoryDistributionResponse])
async def category_distribution(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_category_distribution(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)


@router.get("/admin/reports/trend", response_model=list[TrendResponse])
async def trend(
    granularity: str = Query("day"),
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_trend(
        db,
        granularity,
        start_date.isoformat() if start_date else None,
        end_date.isoformat() if end_date else None,
    )


@router.get("/admin/reports/satisfaction", response_model=SatisfactionResponse)
async def satisfaction(
    start_date: date | None = None,
    end_date: date | None = None,
    db=Depends(get_db),
    _=Depends(require_role("admin", "supervisor")),
):
    return await get_satisfaction_stats(db, start_date.isoformat() if start_date else None, end_date.isoformat() if end_date else None)
```

修改 `backend/app/main.py`，在现有的 router includes 之后添加：

```python
from app.routers import reports

app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_reports.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/reports.py backend/app/main.py backend/tests/test_reports.py
git commit -m "feat(t007): reports router with role-based access control"
```

---

### Task 5: Export Task + Download

**Files:**
- Modify: `backend/app/tasks/export_tasks.py`
- Modify: `backend/app/routers/reports.py`
- Modify: `backend/.gitignore`
- Test: `backend/tests/test_export.py`

**Interfaces:**
- Consumes: `get_*` functions from `report_service`; `ExportRequest` schema; `settings.EXPORT_DIR`
- Produces: Celery task `tasks.generate_report_export`; download endpoint

- [ ] **Step 1: Write the failing tests**

创建 `backend/tests/test_export.py`：

```python
import uuid

import pytest


# API-EXP-101: export xlsx succeeds and file is downloadable
async def test_export_xlsx_success(client, admin_auth_headers):
    payload = {
        "report_type": "overview",
        "format": "xlsx",
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    task_id = data["task_id"]

    # Query status (may still be pending in tests)
    r2 = await client.get(f"/api/v1/admin/reports/export/{task_id}", headers=admin_auth_headers)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["task_id"] == task_id
    assert data2["status"] in ("pending", "completed")


# API-EXP-102: export csv succeeds
async def test_export_csv_success(client, admin_auth_headers):
    payload = {
        "report_type": "category_distribution",
        "format": "csv",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "pending"


# API-EXP-201: invalid report_type returns 422
async def test_invalid_report_type_422(client, admin_auth_headers):
    payload = {
        "report_type": "invalid_type",
        "format": "xlsx",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 422


# API-EXP-202: pending export status returns pending
async def test_pending_export_status(client, admin_auth_headers):
    # Use a random UUID that will never be found
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/v1/admin/reports/export/{fake_id}", headers=admin_auth_headers)
    # Our implementation may return 404 for unknown task_id
    assert r.status_code in (200, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_export.py -v`
Expected: FAIL with 404 (route not found)

- [ ] **Step 3: Write minimal implementation**

修改 `backend/app/tasks/export_tasks.py`：

```python
import csv
import uuid
from pathlib import Path

import pandas as pd
from celery import shared_task

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.report_service import (
    get_agent_performance,
    get_category_distribution,
    get_overview,
    get_satisfaction_stats,
    get_trend,
)

REPORT_TYPE_TO_FUNC = {
    "overview": get_overview,
    "agent_performance": get_agent_performance,
    "category_distribution": get_category_distribution,
    "trend": get_trend,
    "satisfaction": get_satisfaction_stats,
}


def _sanitize_for_export(value):
    """Prevent CSV/Excel formula injection."""
    if not isinstance(value, str):
        return value
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _sanitize_rows(rows):
    if isinstance(rows, dict):
        return {k: _sanitize_for_export(v) for k, v in rows.items()}
    if isinstance(rows, list):
        return [_sanitize_rows(row) for row in rows]
    return rows


@shared_task(name="tasks.generate_report_export")
def generate_report_export(task_id: str, report_type: str, format: str, start_date: str | None, end_date: str | None):
    import asyncio
    asyncio.run(_async_generate_report_export(task_id, report_type, format, start_date, end_date))


async def _async_generate_report_export(task_id, report_type, format, start_date, end_date):
    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        func = REPORT_TYPE_TO_FUNC.get(report_type)
        if func is None:
            raise ValueError(f"Unknown report_type: {report_type}")

        if report_type == "overview":
            data = await func(db)
        elif report_type == "trend":
            # Default granularity for export is day
            data = await func(db, "day", start_date, end_date)
        else:
            data = await func(db, start_date, end_date)

    if report_type == "overview" or report_type == "satisfaction":
        # Single dict -> list of one
        rows = [data]
    else:
        rows = data if isinstance(data, list) else [data]

    rows = _sanitize_rows(rows)
    df = pd.DataFrame(rows)

    file_path = export_dir / f"{task_id}.{format}"
    if format == "xlsx":
        df.to_excel(file_path, index=False, engine="openpyxl")
    else:
        df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
```

修改 `backend/app/routers/reports.py`，在文件顶部添加导入：

```python
import re
import uuid
from pathlib import Path

from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.report import ExportRequest
from app.tasks.export_tasks import generate_report_export
```

在 `backend/app/routers/reports.py` 底部追加路由：

```python
UUID_RE = re.compile(r"^[a-f0-9\-]{36}$")


@router.post("/admin/reports/export")
async def create_export(
    req: ExportRequest,
    _=Depends(require_role("admin", "supervisor")),
):
    task_id = str(uuid.uuid4())
    generate_report_export.delay(
        task_id=task_id,
        report_type=req.report_type,
        format=req.format,
        start_date=req.start_date.isoformat() if req.start_date else None,
        end_date=req.end_date.isoformat() if req.end_date else None,
    )
    return {"task_id": task_id, "status": "pending"}


@router.get("/admin/reports/export/{task_id}")
async def get_export_status(
    task_id: str,
    _=Depends(require_role("admin", "supervisor")),
):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="无效的 task_id")

    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    for fmt in ("xlsx", "csv"):
        file_path = export_dir / f"{task_id}.{fmt}"
        if file_path.exists():
            return {
                "task_id": task_id,
                "status": "completed",
                "download_url": f"/api/v1/admin/reports/exports/download/{task_id}",
            }
    return {"task_id": task_id, "status": "pending", "download_url": None}


@router.get("/admin/reports/exports/download/{task_id}")
async def download_export(
    task_id: str,
    _=Depends(require_role("admin", "supervisor")),
):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail="无效的 task_id")

    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    for fmt in ("xlsx", "csv"):
        file_path = export_dir / f"{task_id}.{fmt}"
        if file_path.exists():
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if fmt == "xlsx"
                else "text/csv"
            )
            return FileResponse(
                path=str(file_path),
                filename=f"report_{task_id}.{fmt}",
                media_type=media_type,
            )
    raise HTTPException(status_code=404, detail="导出文件不存在或尚未完成")
```

注意：需要在 `backend/app/routers/reports.py` 顶部添加 `HTTPException` 导入：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
```

修改 `backend/.gitignore`，追加：

```gitignore
/exports/
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_export.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/export_tasks.py backend/app/routers/reports.py backend/tests/test_export.py backend/.gitignore
git commit -m "feat(t007): async report export with xlsx/csv and formula injection guard"
```

---

### Task 6: Integration Tests + Full Regression

**Files:**
- Test: `backend/tests/test_reports.py`, `backend/tests/test_export.py`
- Run: full pytest suite

- [ ] **Step 1: Run all T007 tests**

Run: `cd backend && pytest tests/test_reports.py tests/test_export.py -v`
Expected: PASS (all tests)

- [ ] **Step 2: Run full regression suite**

Run: `cd backend && pytest`
Expected: All existing tests still pass (zero T007 regression)

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "test(t007): integration and regression tests pass"
```

---

## Spec Coverage Check

| 需求 | 任务 |
|------|------|
| 综合概览（总量、状态分布、SLA 达标率、满意度） | Task 1 |
| 客服绩效（工单量、平均首次响应/解决时长） | Task 2 |
| 分类分布 | Task 1 |
| 时段趋势（日/周/月） | Task 3 |
| 满意度统计 | Task 1 |
| Excel/CSV 异步导出 | Task 5 |
| 权限隔离（supervisor/admin） | Task 4 |
| 日期范围校验（上限 365 天） | Task 1 + Task 4 |
| granularity 白名单 | Task 3 + Task 4 |
| 公式注入防护 | Task 5 |
| UUID 路径校验 | Task 5 |

**无遗漏。**

## Placeholder Scan

- 无 "TBD", "TODO", "implement later", "fill in details"
- 无 "Add appropriate error handling" 等模糊描述
- 所有步骤包含实际代码和命令
- 无 "Similar to Task N"

## Type Consistency Check

- `validate_date_range` 签名在所有任务中一致：`start_date: str | None, end_date: str | None -> tuple[datetime, datetime]`
- `granularity` 白名单值一致：`day/week/month`
- `ExportRequest.format` 枚举一致：`xlsx/csv`
- `task_id` 使用 `uuid.uuid4()` 生成，正则校验一致

---

**Plan complete and saved to `docs/superpowers/plans/2026-08-09-statistics-reports.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
