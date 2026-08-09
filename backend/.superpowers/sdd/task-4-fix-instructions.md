# Task 4 Fix Instructions

## Important Issue: Exception semantic debt

The router adds `_map_validation_error` to catch `DuplicateException` (409) and re-raise as 422. This is a workaround because `validate_date_range` in `report_service.py` wrongly raises `DuplicateException` for date validation errors.

### Required fix:

1. **In `app/exceptions.py`** — Add a new exception class (if not already existing):
   ```python
   class ValidationException(TicketSystemException):
       def __init__(self, message: str):
           super().__init__(message, status_code=422)
   ```
   If `ValidationException` already exists or there's a similar 422 exception, reuse it.

2. **In `app/services/report_service.py`** — Replace ALL `raise DuplicateException(...)` in `validate_date_range` with `raise ValidationException(...)`.

3. **In `app/routers/reports.py`** — Remove the `_map_validation_error` wrapper entirely. The routes should call the service functions directly. `ValidationException` will be handled by the global `ticket_system_exception_handler` in `main.py` (which already catches `TicketSystemException` and returns `status_code=exc.status_code`).

4. **Verify tests still pass.** The tests expect 422 for date validation errors — with `ValidationException(status_code=422)`, they will get 422 without any router workaround.

Run tests after fixing:
```bash
cd backend && pytest tests/test_reports.py -v
```

Report results.
