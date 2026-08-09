# Task 5 Fix Instructions

## Important Issue: Ineffective formula-injection test

The test `test_export_task_sanitizes_formula_injection` exports an overview report and asserts `=cmd` is absent. But overview data never contains formula-trigger characters, so the test passes even if sanitization is removed.

### Required fix in `backend/tests/test_export.py`:

Rewrite the test to actually verify the `_sanitize_for_export` logic:

1. Create a ticket with a title or description that starts with a formula trigger character (e.g., `=HYPERLINK("http://evil.com","click")` or `+1+1`)
2. Export a report that includes this ticket data (e.g., `category_distribution` or a custom overview)
3. Read the generated export file
4. Assert the formula trigger has been sanitized (prefixed with `'`)

Alternatively, if testing the Celery task directly is difficult in the test setup, test the `_sanitize_for_export` helper directly by importing it and asserting:
```python
from app.tasks.export_tasks import _sanitize_for_export
assert _sanitize_for_export("=HYPERLINK(...)") == "'=HYPERLINK(...)"
assert _sanitize_for_export("+1+1") == "'+1+1"
assert _sanitize_for_export("-1-1") == "'-1-1"
assert _sanitize_for_export("@SUM(...)") == "'@SUM(...)"
assert _sanitize_for_export("normal text") == "normal text"
```

This is simpler and directly tests the sanitization logic.

Run tests after fixing:
```bash
cd backend && pytest tests/test_export.py -v
```

Report results.
