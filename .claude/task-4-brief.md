# Task 4 Brief: Celery SLA Scan Tasks

## Where This Fits

This is Task 4 of 6 for T006. Tasks 1-3 created models, SLA engine, and notification service. This task builds the Celery periodic scan that detects warnings and breaches.

## Interfaces from Earlier Tasks

- `SLARecord` model at `app.models.sla_record`
- `Notification` service at `app.services.notification_service`
- `AsyncSessionLocal` at `app.database`
- `celery_worker.py` already includes `"app.tasks.sla_tasks"` in its `include` list

## Requirements

### Step 1: Create `backend/app/tasks/sla_tasks.py`

Implement the complete scan task. Key requirements:
- `@shared_task(name="tasks.scan_sla_deadlines")` wrapper that calls `asyncio.run(_async_scan())`
- `_async_scan()` creates an `AsyncSessionLocal`, caches supervisor IDs once, calls `_scan_first_resp` and `_scan_resolution`, then commits
- Each scan function checks 3 stages: agent 3h warning, agent 2h warning, supervisor 1h warning, breach
- ALL queries use `.options(selectinload(SLARecord.ticket))` and `.with_for_update()`
- Per-record `try/except` so one bad record doesn't abort the batch
- Warning queries exclude short SLAs (e.g., `first_resp_hours > 3` for 3h warning)
- `notify_sla_warning()` returns `bool` (True if at least one notification created); flag only set if True
- `notify_sla_breach()` always marks breach after sending

Use the exact code from the design document for `sla_tasks.py`.

### Step 2: Modify `backend/celery_worker.py`

Add `beat_schedule`:
```python
celery_app.conf.beat_schedule = {
    "scan-sla-deadlines": {
        "task": "tasks.scan_sla_deadlines",
        "schedule": 300.0,
    },
}
```

### Step 3-4: Write tests in `backend/tests/test_sla_tasks.py`

Write these tests:
- `test_scan_first_resp_agent_3h_warning` — manipulate SLA due time to 2.5h from now, scan, assert notification created and flag set
- `test_scan_first_resp_supervisor_1h_warning` — manipulate due to 45min from now, assert supervisor gets notification
- `test_scan_first_resp_breach` — manipulate due to 1h ago, assert breach marked and notification created
- `test_short_sla_no_3h_warning` — 1h SLA with due 30min from now, assert no notification
- `test_scan_no_duplicate_notification` — run scan twice, assert only 1 notification

Run: `pytest -p no:anyio tests/test_sla_tasks.py -v`
Expected: all tests PASS

### Step 5: Commit

```bash
git add backend/app/tasks/sla_tasks.py backend/celery_worker.py backend/tests/test_sla_tasks.py
git commit -m "feat(t006): Celery scan task for SLA warnings and breaches"
```

## Global Constraints

- Use `AsyncSessionLocal` from `app.database` (NOT `get_db()` which is for FastAPI dependency injection).
- Supervisor IDs are cached once per scan: `select(User.id).where(User.role == "supervisor")`.
- `notify_sla_warning` must NOT set warning flags if no target users (returns False).
- All notification creation goes through `create_notification()` service (no direct `Notification()` instantiation in tasks).
- Tests manipulate `sla.first_resp_due` / `sla.resolution_due` directly via DB to avoid time travel issues.
- All tests use `-p no:anyio`.
- Do NOT modify any files not listed above.

## Report

Write your report to `.claude/task-4-report.md` with status, files touched, test command + output, concerns.
