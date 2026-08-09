# Fix Report — Task 1 (Category Module Review)

## Commit
`ab79250` fix(categories): address review issues - use NotFoundException, add missing assertions and tests

## Files Changed
- `backend/app/routers/categories.py`
- `backend/app/services/category_service.py`
- `backend/tests/test_categories.py`

## Fixes Applied

### Important Issues
1. **Replaced `HTTPException(404)` with `NotFoundException`** in `routers/categories.py` (lines 48 and 60).
   - Imported `NotFoundException` from `app.exceptions`.
   - Removed unused `HTTPException` import.
   - Now consistent with the global `TicketSystemException` handler in `main.py`.

2. **Added response body assertions** to 4 tests that previously only checked status codes:
   - `test_list_categories_success` — now creates a category first and asserts list contains the created item with correct `id`, `name`, `code`, and `default_priority`.
   - `test_delete_category_not_found_404` — asserts `r.json()["detail"] == "分类不存在"`.
   - `test_create_category_unauthorized_401` — asserts `r.json()["detail"] == "Not authenticated"`.
   - `test_create_category_forbidden_403` — asserts `r.json()["detail"] == "需要角色: admin, supervisor"`.

### Quick Minor Issues
3. **Added supervisor permission test** `test_create_category_as_supervisor_200` — supervisor can successfully create categories.
4. **Added invalid priority 422 test** `test_create_category_invalid_priority_422` — rejects `P4` via Pydantic schema validation.
5. **Added PUT 404 test** `test_update_category_not_found_404` — updating non-existent category returns 404 with correct detail.
6. **Added duplicate code 409 test** `test_create_category_duplicate_code_409` — and fixed service layer to catch `IntegrityError` and raise `DuplicateException("分类编码已存在")` instead of triggering a raw 500.

## Test Results

```
pytest -p no:anyio tests/test_categories.py -v
=> 10 passed

pytest -p no:anyio tests/ -v
=> 27 passed (17 auth + 10 category)
```

No regressions in auth module.

## Remaining Issues / Not Addressed
- `backend/app/routers/__init__.py` exports `auth_router` / `categories_router` not used by `main.py` — reviewer noted as observation, not a defect; left unchanged per instructions.
- `backend/app/services/__init__.py` was empty and not modified — reviewer noted discrepancy with report claim, no code fix required.
- A full auth regression suite was already passing; no new auth regressions introduced.
