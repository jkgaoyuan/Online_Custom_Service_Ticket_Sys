# T007 Final Fix Instructions

Based on the final whole-branch review, fix the following issues in a single commit:

## Important Issue 2.1: SQL f-string in trend query

In `app/services/report_report.py`, the trend query uses:
```python
INTERVAL '1 {granularity}'
```

Fix: Map granularity to a safe interval string in Python:
```python
INTERVALS = {"day": "1 day", "week": "1 week", "month": "1 month"}
```
Then use `INTERVALS[granularity]` in the SQL (still inside `text()`, but now the SQL only contains a static literal, not an f-string interpolation).

## Important Issue 2.2: Async export silently swallows invalid date ranges

In `app/routers/reports.py`, the `create_export` endpoint fires a Celery task without validating the date range.

Fix: Before calling `generate_report_export.delay(...)`, synchronously call:
```python
from app.services.report_service import validate_date_range
if req.start_date and req.end_date:
    validate_date_range(req.start_date.isoformat(), req.end_date.isoformat())
```
This will raise `ValidationException` (422) immediately if the range is invalid.

## Minor Issue 3.1: Unused import TicketSystemException

In `app/routers/reports.py`, remove the unused `TicketSystemException` import.

## Minor Issue 3.2: sat_scores duplicated

In `app/services/report_service.py`, extract the satisfaction score mapping to a module constant:
```python
SATISFACTION_SCORES = {"satisfied": 5, "neutral": 3, "dissatisfied": 1}
```
Replace the two inline occurrences in `get_overview` and `get_satisfaction_stats`.

## Minor Issue 3.3: Unused import uuid

In `app/tasks/export_tasks.py`, remove the unused `import uuid`.

## Running tests

After all fixes, run:
```bash
cd backend && pytest tests/test_reports.py tests/test_export.py -v
```
Then run:
```bash
cd backend && pytest -v
```
Report results.
