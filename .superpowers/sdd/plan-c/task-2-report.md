# Task C2 Report: User Management Service

## What was implemented

Created `backend/app/services/user_service.py` with four service functions consumed by Task C3 (Admin Router):

- `list_users(db, role, is_active, page, page_size)` — paginated user listing with optional `role` and `is_active` filters. Returns total count, current page info, and user items enriched with per-user `ticket_count` aggregated from `Ticket.assignee_id`.
- `get_user_by_id(db, user_id)` — fetch a single `User` by primary key, returns `None` if not found.
- `update_user(db, user_id, update_data)` — update username, email, role, or `is_active`. Validates uniqueness for username/email against other users and restricts role to the allowed set (`customer`, `agent`, `supervisor`, `admin`). Raises `HTTPException(404)` if the user does not exist.
- `reset_user_password(db, user_id)` — generates a 12-character alphanumeric temporary password, hashes it with `get_password_hash`, persists the change, creates a `password_reset` notification via `create_notification`, and commits. Returns the plaintext temporary password for the admin to communicate out-of-band.

## Testing and results

- **Syntax/import check**: `cd backend && python -c "from app.services.user_service import *"` completed with no errors.
- No new unit tests were added in this task; Task C5 will cover backend tests per Plan C.

## Files changed

| Operation | Path | Description |
|-----------|------|-------------|
| Create | `backend/app/services/user_service.py` | New service layer for user management admin operations |

## Commit

- `0ddce6f` — `feat(user-mgmt): add user list, update, and reset password service`

## Self-review findings

- All four exported functions from the task brief are implemented exactly as specified.
- Edge cases handled: missing user (404), duplicate username/email (400), invalid role value (400).
- `create_notification` does not commit itself, so the function calls `create_notification` before the final `db.commit()`, ensuring the notification is persisted together with the password change.
- Implementation follows the existing service pattern in the codebase (async functions, `AsyncSession`, `HTTPException`, explicit commit/refresh).
- No overbuilding or speculative features beyond the brief.

## Issues or concerns

None.

## Review fixes

### Issue 1: Non-atomic uniqueness check (race condition)
**File:line**: `backend/app/services/user_service.py:102-116`

**What was fixed**: Added pessimistic row locking (`with_for_update()`) to the target user SELECT and both duplicate-check SELECTs, and wrapped `await db.commit()` in a `try/except IntegrityError` fallback. This prevents concurrent updates to the same user from racing past the friendly duplicate check and guarantees that any residual race is caught by the database-level unique constraints on `User.username` and `User.email`.

**Code changes**:
- Imported `IntegrityError` from `sqlalchemy.exc`.
- `select(User).where(User.id == user_id).with_for_update()` locks the row being updated.
- Both duplicate checks now append `.with_for_update()`.
- Commit is guarded:
  ```python
  try:
      await db.commit()
  except IntegrityError as exc:
      await db.rollback()
      raise HTTPException(status_code=400, detail="用户名或邮箱已存在") from exc
  ```

### Issue 2: `bool()` coercion of `is_active` is incorrect for string inputs
**File:line**: `backend/app/services/user_service.py:124`

**What was fixed**: Removed the unsafe `bool(update_data["is_active"])` coercion. The value is now assigned directly: `user.is_active = update_data["is_active"]`. Task C3's Pydantic `UserUpdate` schema already validates `is_active` as `Optional[bool]`, so by the time the service receives the dict the value is guaranteed to be a proper `bool` or absent.

### Verification
- **Syntax/import check**: `cd backend && python -c "from app.services.user_service import *"` completed with no errors.
