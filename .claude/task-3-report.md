# Task 3 Report: Notification Service and REST API

## Status

Completed successfully.

## Files Touched

- `backend/app/schemas/notification.py` — new
- `backend/app/services/notification_service.py` — new
- `backend/app/routers/notifications.py` — new
- `backend/app/main.py` — modified (added import and router registration)
- `backend/tests/test_notifications.py` — new

## Commit

`7345e07` feat(t006): notification service and REST API

## Test Command and Output

```bash
$ pytest -p no:anyio tests/test_notifications.py -v
```

```
tests/test_notifications.py::test_create_notification PASSED
tests/test_notifications.py::test_get_unread_notifications PASSED
tests/test_notifications.py::test_mark_notification_read PASSED
tests/test_notifications.py::test_mark_all_notifications_read PASSED
tests/test_notifications.py::test_api_list_notifications PASSED
tests/test_notifications.py::test_api_mark_read_own_only PASSED

6 passed, 2 warnings in 14.47s
```

## Concerns

- `Notification.is_read` default is only applied at DB flush time (SQLAlchemy 2.0 `mapped_column` behavior), so pre-commit assertions on `is_read` must be done after `commit()`/`refresh()`. This was adjusted in `test_create_notification`.
- No placeholder `sla.py` router was created per instructions.
- `create_notification` does not call `db.flush()` or `db.commit()` internally, leaving transaction control to callers as required.
