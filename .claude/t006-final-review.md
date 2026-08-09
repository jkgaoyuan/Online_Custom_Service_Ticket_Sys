# T006 SLA Management — Final Code Review

**Reviewer:** Final Branch Reviewer  
**Date:** 2026-08-09  
**Branch:** worktree-feat+t003-ticket-core (T006 SLA Management)  
**Spec:** `docs/superpowers/specs/2026-08-09-sla-management-design.md`

---

## 1. Overall Verdict

**Needs fix**

The architecture, spec compliance, and test coverage are all strong. However, one **Critical** defect — the `Notification` model using a PostgreSQL-only `JSONB` type — breaks the entire backend test suite on SQLite (the project's test database). This must be resolved before merge. Once fixed, the branch is mergeable with two minor cleanups.

---

## 2. Findings

### 2.1 Critical

| # | Finding | Location |
|---|---------|----------|
| C1 | **Notification model uses `postgresql.JSONB`, breaking all SQLite tests** | `backend/app/models/notification.py` |

**Details:**  
`Notification.data` is typed as `Mapped[dict] = mapped_column(JSONB, ...)`. SQLite's compiler cannot render `JSONB`, causing `CompileError` on every test that triggers `Base.metadata.create_all()` (which is all of them via the `setup_db` autouse fixture). This regresses not only the 25 new T006 tests but also the 44 T005 webhook tests and the rest of the suite.

**Fix:** Change the model to use generic `sqlalchemy.JSON` (consistent with `Category.sla_config`). The Alembic migration already correctly uses `postgresql.JSONB()` for the actual DDL, so production PostgreSQL will still get `JSONB` columns.

```python
# backend/app/models/notification.py
-from sqlalchemy.dialects.postgresql import JSONB
+from sqlalchemy import JSON
 
-    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
+    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
```

---

### 2.2 Important

| # | Finding | Location |
|---|---------|----------|
| I1 | **`create_ticket()` now commits twice; deviates from spec's single-commit intent** | `backend/app/services/ticket_service.py` |

**Details:**  
The spec states: "在 create_ticket() service 内部、它自身的 db.commit() 之前创建 SLA 记录。不改动 create_ticket() 的 commit 契约". The implementation adds a second `await db.commit()` after `create_sla_record()`. While functionally safe for MVP, it widens the transaction window and leaves a window where a ticket exists without an SLA record. Consider creating the SLA record before the original commit (after `db.flush()`) so both ticket and SLA are committed atomically.

Similarly, `create_reply()` in `reply_service.py` commits, then checks SLA and commits again. This is less critical but follows the same double-commit pattern.

| I2 | **Ticket list endpoint does not embed SLA summary** | `backend/app/routers/tickets.py` |

**Details:**  
Spec section 8.3 requires SLA summary in both `GET /api/v1/tickets` and `GET /api/v1/tickets/{id}`. The detail endpoint was updated, but the list endpoint was not. This is a minor spec deviation.

---

### 2.3 Minor

| # | Finding | Location |
|---|---------|----------|
| M1 | **Significant duplication between `_scan_first_resp` and `_scan_resolution`** | `backend/app/tasks/sla_tasks.py` |

**Details:**  
The two functions are ~120 lines of nearly identical logic (3 warning stages + breach, differing only in column names). A generic `_scan_deadline(db, now, supervisor_ids, deadline_type, hours_attr, due_attr, at_attr, breached_attr, warned_attrs)` would reduce duplication and maintenance risk. Acceptable for MVP but recommended cleanup.

| M2 | **Local imports inside `list_overdue_sla`** | `backend/app/routers/sla.py` |

**Details:**  `select` and `SLARecord` are imported locally inside the route handler. Move to module level for consistency.

---

## 3. Architecture & Integration

**Verdict: Clean**

- **SLA creation** is correctly hooked into `create_ticket()` via `create_sla_record()`.
- **First response capture** is cleanly implemented in `create_reply()` with `is_agent_reply` passed from the router, avoiding an extra user query in the service layer.
- **Status transitions** correctly set/clear `resolved_at` on both `Ticket` and `SLARecord`, including the reopen (`resolved -> in_progress`) edge case.
- **Celery wiring** is complete: `sla_tasks.py` registered in `celery_worker.py` with a 5-minute beat schedule.
- **Notification infrastructure** is reusable and correctly scoped (no internal commits, caller owns transaction).
- **API integration** follows existing patterns: `check_ticket_access` reused for ticket-scoped SLA endpoint, `require_role` for admin endpoints.

---

## 4. Spec Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| SLA record model with warning flags | ✅ | Matches spec exactly |
| Nested per-priority `sla_config` | ✅ | `CategoryCreate` updated; `_resolve_sla_config` handles flat fallback |
| Flat→nested data migration | ✅ | Alembic migration uses `jsonb_build_object` with correct WHERE clause |
| First response / resolution capture | ✅ | Router passes `is_agent_reply`; `transition_ticket_status` handles resolved/reopen |
| Celery scan 3h/2h/1h + breach | ✅ | Stages match spec; `with_for_update()` used |
| Short SLA skips early warning | ✅ | `first_resp_hours > N` guards present |
| Notification service + API | ✅ | `create_notification`, `mark_read`, `mark_all_read` implemented |
| Ticket SLA detail API | ✅ | `GET /tickets/{id}/sla` |
| Admin overdue list API | ✅ | `GET /admin/sla/overdue` with `breach_type` filter |
| Embed SLA in ticket responses | ⚠️ | Detail only; list endpoint missing |

---

## 5. Data Safety & Migration

**Migration:** `40164b94b52f_add_sla_records_and_notifications_.py`

- **Safe for new deployments:** Creates `sla_records` and `notifications` tables with correct constraints and partial indexes.
- **Data migration correct:** `UPDATE categories SET sla_config = jsonb_build_object(...) WHERE sla_config ? 'first_resp_hours' AND NOT sla_config ? 'P0'` correctly targets only flat-format rows.
- **Rollback provided:** Downgrade reverses `JSONB -> JSON` and drops new tables.
- **Note:** Migration uses PostgreSQL-specific operators (`?`, `jsonb_build_object`, `postgresql_where`). This is acceptable because the project targets PostgreSQL in production and migrations are not run against SQLite.

---

## 6. Concurrency

- **`with_for_update()`** is correctly applied to all six scan queries (3h/2h/1h/breach × first_resp/resolution). This prevents concurrent Celery workers from double-notifying.
- **Warning flags are set only after successful notification send**, which matches the spec's "通知成功发送后才置位" decision. This prevents permanently lost warnings when no assignee exists.
- **Supervisor list is cached** once per scan cycle, avoiding N+1 queries.
- **`selectinload(SLARecord.ticket)`** is used to avoid lazy-loading N+1 inside the scan loop.

---

## 7. Testing

### Test Count & Coverage

| File | Count | Coverage |
|------|-------|----------|
| `test_sla.py` | 13 | Model, auto-creation, flat compat, first_resp capture, resolved/reopen, API detail, API permissions, admin overdue filter, SLA embedding in ticket detail, closed ticket retention |
| `test_sla_tasks.py` | 6 | 3h warning, 1h supervisor warning, breach, short SLA skip, duplicate scan dedup, resolved ticket no breach |
| `test_notifications.py` | 6 | Service create/read/mark-read/mark-all-read, API list, API permission (mark own only) |
| **Total T006** | **25** | Well above the spec's ≥14 requirement |

### Test Dimensions

- **Positive:** SLA auto-creation, category config, default fallback, flat compat, time capture, all API endpoints, scan triggers, notification creation.
- **Edge:** Short SLA (1h) skips 3h warning, reopen clears `resolved_at`, closed ticket retains SLA, duplicate scan doesn't duplicate notify, resolved ticket prevents breach.
- **Permissions:** Customer cannot access another customer's SLA (403), user can only mark own notifications read.

### Test Execution Status

**Current state:** All 25 T006 tests fail with `CompileError` due to `JSONB` on SQLite.  
**After fixing C1:** Expected to pass (no other blocking issues identified).

---

## 8. Code Quality

- **Naming:** Consistent with project conventions (`sla_record.py`, `SLAResponse`, `SLASummary`).
- **File sizes:** `sla_tasks.py` (~300 LOC) is the largest new file; acceptable for MVP but see M1 duplication note.
- **No dead code observed.**
- **Transaction boundaries:** Mostly correct (service functions don't self-commit, except `create_ticket`'s existing pattern). One issue: `reply_service.create_reply` still self-commits inside the function, which is pre-existing and outside T006 scope.

---

## 9. Merge Recommendation

**Do not merge until the following is resolved:**

1. **Fix C1:** Change `Notification.data` from `postgresql.JSONB` to `sqlalchemy.JSON` in the model.
2. **Verify:** Run the full backend test suite and confirm all tests pass (expected: 131+ T004/T005 existing + 25 T006 new).

**Recommended but non-blocking (can be done post-merge or in a follow-up cleanup):**

3. **Fix I1:** Refactor `create_ticket()` to create SLA before the single commit (after flush).
4. **Fix I2:** Add SLA summary to ticket list responses.
5. **Fix M1:** Extract generic scan logic to reduce `_scan_first_resp` / `_scan_resolution` duplication.
6. **Fix M2:** Move local imports in `sla.py` to module level.

Once C1 is fixed and the suite is green, this branch should be merged. The T006 feature is well-architected, thoroughly tested, and closely aligned with the design spec.
