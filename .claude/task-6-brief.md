# Task 6 Brief: Integration Tests and Full Regression

## Where This Fits

This is Task 6 (final) of T006. All code is implemented. This task adds boundary/integration tests and runs the full regression suite.

## Requirements

### Step 1: Append boundary tests to `backend/tests/test_sla.py`

Add `test_closed_ticket_sla_exists`:
- Create ticket, transition to in_progress, then resolved, then closed
- Assert SLA record exists and resolved_at is not None

### Step 2: Append boundary tests to `backend/tests/test_sla_tasks.py`

Add `test_resolved_ticket_no_resolution_breach`:
- Create ticket with assignee, mark SLA resolved_at and set resolution_due in the past
- Run `_async_scan()`
- Assert `resolution_breached` remains False

### Step 3: Run full backend test suite

Run:
```bash
pytest -p no:anyio tests/ -v
```

**Target:**
- All new T006 tests must pass (≥14 new tests across test_sla.py, test_notifications.py, test_sla_tasks.py)
- All existing tests must still pass (baseline was 131 passed at start of T006)
- Zero failures in T006-related tests

If any test fails:
- Determine if it's a T006 regression or pre-existing
- Fix T006 regressions immediately
- Document pre-existing failures in the report

### Step 4: Commit

```bash
git add backend/tests/test_sla.py backend/tests/test_sla_tasks.py backend/tests/test_notifications.py
git commit -m "test(t006): integration and boundary tests for SLA management"
```

## Global Constraints

- All tests use `-p no:anyio`.
- Do NOT modify production code in this task unless fixing a T006 regression discovered by tests.
- Only append tests to existing test files; do not rewrite them.

## Report

Write your report to `.claude/task-6-report.md` with:
1. Status
2. Test counts (new / total / failed / pre-existing failures)
3. Any fixes applied
4. Final commit hash
