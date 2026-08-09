# Task 4 Report: Celery SLA Scan Tasks

## Status
Completed

## Commit
`9a8508b` feat(t006): Celery scan task for SLA warnings and breaches

## Files Touched
- `backend/app/tasks/sla_tasks.py` (new) — complete scan task with `_async_scan`, `_scan_first_resp`, `_scan_resolution`, `notify_sla_warning`, `notify_sla_breach`
- `backend/celery_worker.py` (modified) — added `beat_schedule` for `tasks.scan_sla_deadlines` every 300s
- `backend/tests/test_sla_tasks.py` (new) — 5 unit tests covering 3h warning, 1h supervisor warning, breach, short SLA exclusion, and duplicate prevention

## Test Command & Output
```bash
$ pytest -p no:anyio tests/test_sla_tasks.py -v
============================= test session starts =============================
platform win32 -- Python 3.10.10, pytest-8.0.0, pluggy-1.6.0
collected 5 items

tests/test_sla_tasks.py::test_scan_first_resp_agent_3h_warning PASSED    [ 20%]
tests/test_sla_tasks.py::test_scan_first_resp_supervisor_1h_warning PASSED [ 40%]
tests/test_sla_tasks.py::test_scan_first_resp_breach PASSED              [ 60%]
tests/test_sla_tasks.py::test_short_sla_no_3h_warning PASSED             [ 80%]
tests/test_sla_tasks.py::test_scan_no_duplicate_notification PASSED      [100%]

============================== warnings summary ===============================
-- Docs: https://docs.pytest.org/en/stable/how-to-capture-warnings.html
======================= 5 passed, 2 warnings in 14.68s ========================
```

## Full Regression
Ran full backend suite: **147 passed**, 1 failed, 3 errors.
- Failures/errors are isolated to `tests/test_webhooks.py` (pre-existing `RuntimeError: Task got Future attached to a different loop` in email task threading) and are unrelated to SLA changes.
- All SLA tests (`test_sla.py` + `test_sla_tasks.py`) pass cleanly.

## Concerns
- None related to this task. The webhook/email test instability is a pre-existing event-loop threading issue in `app/tasks/email_tasks.py`.
