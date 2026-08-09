# Task 5 Report: SLA Query API and Embedding

## Status

COMPLETED — all 12 tests pass (8 existing + 4 new).

## Commit

`11b69f60099f864bd228e64b5b58743f012a8488` feat(t006): SLA query API and ticket detail embedding

## Files Touched

| Action | File | Description |
|--------|------|-------------|
| Created | `backend/app/schemas/sla.py` | `SLAResponse` and `SLASummary` Pydantic schemas |
| Created | `backend/app/routers/sla.py` | `GET /tickets/{id}/sla` and `GET /admin/sla/overdue` endpoints |
| Modified | `backend/app/schemas/ticket.py` | Added `sla: Optional[SLASummary] = None` to `TicketResponse` |
| Modified | `backend/app/routers/tickets.py` | `get_ticket` now embeds SLA summary via `get_sla_record_by_ticket_id` |
| Modified | `backend/app/main.py` | Registered `sla.router` under `/api/v1` |
| Modified | `backend/tests/test_sla.py` | Appended 4 API-level tests for Task 5 |

## Test Command + Output

```bash
pytest -p no:anyio tests/test_sla.py -v
```

```
tests/test_sla.py::test_sla_record_model PASSED
tests/test_sla.py::test_create_ticket_auto_creates_sla PASSED
tests/test_sla.py::test_create_ticket_uses_default_sla_when_category_empty PASSED
tests/test_sla.py::test_create_ticket_compat_flat_sla_config PASSED
tests/test_sla.py::test_agent_reply_sets_first_resp_at PASSED
tests/test_sla.py::test_internal_reply_does_not_set_first_resp_at PASSED
tests/test_sla.py::test_transition_to_resolved_sets_resolved_at PASSED
tests/test_sla.py::test_reopen_clears_resolved_at PASSED
tests/test_sla.py::test_api_get_ticket_sla PASSED
tests/test_sla.py::test_api_get_ticket_sla_forbidden PASSED
tests/test_sla.py::test_api_admin_overdue_list PASSED
tests/test_sla.py::test_ticket_detail_includes_sla_summary PASSED

======================= 12 passed, 2 warnings in 29.56s =======================
```

## New Tests Added

- **API-SLA-301** `test_api_get_ticket_sla` — GET `/api/v1/tickets/{id}/sla` returns 200 with correct SLA fields.
- **API-SLA-302** `test_api_get_ticket_sla_forbidden` — customer receives 403 when accessing another customer's ticket SLA.
- **API-SLA-303** `test_api_admin_overdue_list` — admin `GET /api/v1/admin/sla/overdue` returns breached SLAs; supports `breach_type` filter (`first_resp`, `resolution`).
- **API-SLA-304** `test_ticket_detail_includes_sla_summary` — `GET /api/v1/tickets/{id}` now includes embedded `sla` object with `first_resp_due`, `resolution_due`, `first_resp_breached`, `resolution_breached`.

## Concerns

None. `list_tickets` intentionally does NOT embed SLA to avoid N+1 queries, as required.
