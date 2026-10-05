# API contract v1

Prefix: `/api/v1`. JSON responses use UTC ISO 8601 timestamps; IDs are UUID strings. Pagination uses `limit` (default 50, max 100) and opaque `cursor`. Project-scoped browser endpoints require a login token and ownership check. Request validation errors return 422, missing/invalid credentials 401, inaccessible objects 404, key rate limits 429, and oversized events 413.

## Browser endpoints

| Method | Route | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account with email and password |
| POST | `/auth/login` | Return short-lived access token |
| POST | `/projects` | Create project and return one-time ingestion key |
| GET | `/projects` | List owned projects |
| POST | `/projects/{project_id}/keys/rotate` | Invalidate previous key; return new one once |
| GET | `/projects/{project_id}/events` | Filter by time, level, service, text; paginate |
| GET | `/projects/{project_id}/overview` | Counts, error rate, services, chart buckets |
| GET | `/projects/{project_id}/incidents` | List incidents by status and time |
| GET | `/projects/{project_id}/incidents/{incident_id}` | Timeline and cited events |
| POST | `/projects/{project_id}/incidents/{incident_id}/investigate` | Run or refresh bounded investigation |

Keep login and project keys out of URL query strings. Document token expiry and refresh behavior when implementing browser auth.

## Ingestion endpoint

`POST /api/v1/events` accepts `Authorization: Bearer <project_ingestion_key>`. The key selects the project; the body must not specify an authoritative project ID. One request event represents one application request.

```json
{
  "event_id": "b7474457-5542-4b7f-8ba6-6a12da71e629",
  "timestamp": "2026-10-02T14:32:51Z",
  "event_type": "request",
  "level": "ERROR",
  "service": "payment-api",
  "message": "Database connection timeout",
  "endpoint": "/payments",
  "status_code": 500,
  "latency_ms": 2431,
  "exception_type": "DatabaseTimeout",
  "stack_trace": "DatabaseTimeout at payment.py:82",
  "metadata": {"request_id": "req_39291", "environment": "demo"}
}
```

`event_id` is client generated to support retries. Enforce uniqueness on `(project_id, event_id)`; a duplicate returns the existing result without increasing counts. Require UTC or offset-aware `timestamp`; retain `received_at` from the server. Suggested limits: 64 KiB body, 2 KiB message, 8 KiB stack, 4 KiB metadata, allowed level enum, 0–599 status code, nonnegative finite latency. An exception-only event uses `event_type=exception` and does not add to request denominators.

```json
{"status":"stored","event_id":"b7474457-5542-4b7f-8ba6-6a12da71e629"}
```

Return 201 after persistence, 200 for a replay. Batch ingestion is deferred until needed by load tests.

Implemented Phase 4 validation: `event_type` is `request` or `exception`; `level` is `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`, or `FATAL`. Field types are strict, unknown fields are rejected, and service names must be nonblank (maximum 255 characters). Optional endpoint and exception type are each capped at 2 KiB UTF-8. Metadata must be a JSON object. Unsupported content types or compressed bodies return 415; malformed JSON and invalid fields return 422; body or field size violations return 413. A per-key limit of 600 attempts per rolling minute returns 429 with `Retry-After` (local single-process enforcement). Common secret patterns are redacted before storage. A replay preserves the originally stored event even if retry fields differ. No event-reading endpoint is implemented yet.

## Investigation response

```json
{
  "incident_id": "f2c5a59d-ae48-48d8-a8d0-165f6e1e39fd",
  "status": "complete",
  "summary": "Payment requests show repeated database timeouts.",
  "observations": [{"text":"12 failed requests in 5 minutes","event_ids":["b7474457-5542-4b7f-8ba6-6a12da71e629"]}],
  "hypotheses": [{"cause":"Database connection shortage","supporting_event_ids":["b7474457-5542-4b7f-8ba6-6a12da71e629"]}],
  "suggested_checks": ["Inspect database pool and connection acquisition time"],
  "limitations": ["Database pool metrics were not collected"],
  "method": "rules",
  "created_at": "2026-10-02T14:35:00Z"
}
```

Never claim a specific code change caused the incident when no change history was collected.
