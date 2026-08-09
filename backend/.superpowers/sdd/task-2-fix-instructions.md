# Task 2 Fix Instructions

## Critical Issue 1: Incorrect first-response metric

The current `get_agent_performance` averages ALL non-internal replies per author. It must average only the EARLIEST non-internal reply per ticket.

### Required fix in `app/services/report_service.py`:

Replace the first_reply_result query with a CTE or subquery that selects DISTINCT ON (ticket_id) the earliest non-internal reply, then averages by author_id:

```sql
WITH first_replies AS (
  SELECT DISTINCT ON (ticket_id) ticket_id, author_id, created_at
  FROM ticket_replies
  WHERE is_internal = false
  ORDER BY ticket_id, created_at ASC
)
SELECT
  fr.author_id,
  AVG(EXTRACT(EPOCH FROM (fr.created_at - t.created_at))/3600)
FROM first_replies fr
JOIN tickets t ON fr.ticket_id = t.id
WHERE t.created_at BETWEEN :start AND :end
GROUP BY fr.author_id
```

In SQLAlchemy, this can be done with a subquery using `distinct(TicketReply.ticket_id)` and `func.min(TicketReply.created_at)` or a window function. Use whatever compiles cleanly with SQLAlchemy 2.0 + asyncpg.

## Important Issue 2: Use _create_resolved_ticket helper

In the test, replace manual ticket creation/resolution with `_create_resolved_ticket`.

## Minor Issue 3: Strengthen test assertions

In `test_agent_performance_returns_correct_stats`, after creating a ticket with known resolution time and a first reply, assert the actual computed values (e.g., `total_assigned >= 1`, `resolved_count >= 1`, `avg_resolution_hours > 0`).

## Running tests

After fixing, run: `cd backend && pytest tests/test_reports.py::test_agent_performance_returns_correct_stats -v`
Then run: `cd backend && pytest tests/test_reports.py -v`
Report results.
