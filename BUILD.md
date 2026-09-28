# Plan A: 14 build sessions

These are sessions, not a promise that every feature fits in one calendar day. At the end of each session, run the acceptance check and commit the working state. Build the first vertical slice before polishing UI or adding a model.

| Session | Build | Check before proceeding |
|---|---|---|
| 1 | Initialize repo, Python environment, Vite app, Compose PostgreSQL, `.env.example` | API health endpoint and database connection work |
| 2 | Alembic schema; register/login and password hashing | Unauthorized request rejected; register/login tested |
| 3 | Projects and one-time project keys | Plain key shown once; database contains hash only; ownership enforced |
| 4 | Validated idempotent event ingestion | Send event twice; one stored record; invalid key rejected |
| 5 | Demo service request instrumentation and fault toggles | Healthy and failing requests produce traceable events |
| 6 | Paginated event API and basic React log explorer | Filter by project/service/level/time; browser cannot cross projects |
| 7 | Rolling-window detector worker and active incident lifecycle | Healthy traffic creates none; repeated failures create one active incident |
| 8 | Stable exception fingerprints and incident details | Similar exceptions group; unrelated stack traces remain separate |
| 9 | Project overview and incident dashboard | Counts match database queries; timestamps and status clear |
| 10 | Bounded evidence retrieval and deterministic investigation | Each observation cites stored event IDs; missing evidence named |
| 11 | Optional local LLM drafting with schema validation and fallback | Invalid/offline model still yields deterministic result |
| 12 | Fault scenarios, automated evaluation, targeted integration tests | Known faults replay; metrics computed from run records |
| 13 | Container builds, persistent volume, migrations at startup, clean setup | Fresh Compose startup reproduces the demo |
| 14 | Documentation, screenshots, measured results, deployment decision | Another developer can follow README without your help |

## First vertical slice

Implement this before session 6: register → create project → send one request event with key → read it back as owner. Use Swagger or curl to verify each hop. Treat failed setup as a blocker; do not compensate with mocked dashboard data.

## Fault toggles in the demo app

Support a safe local-only way to enable `db_timeout`, `unhandled_exception`, and `slow_dependency`. Gate these switches behind local/demo configuration so they cannot be triggered on a real customer service. Run healthy traffic before and after each fault; reset the demo and record incident timestamps.

## Tests that matter

- Wrong key, revoked key, duplicate event, invalid timestamp, oversized payload.
- User A cannot see User B's events or incidents.
- Detector excludes exception-only events from request counts; repeats do not produce duplicate active incidents; low-volume windows do not resolve an incident.
- Investigation citations belong to the same project and exist in storage; model failure falls back.

## Environment checklist

`.env.example` should describe `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `DETECTOR_WINDOW_SECONDS`, `DETECTOR_INTERVAL_SECONDS`, `EVENT_RETENTION_DAYS`, `INVESTIGATOR_MODE=rules|local_llm`, and optional local model URL/name. Use development-only placeholder values in examples. The frontend needs an API base URL, not any server secret.

## Build gates

At every stage run the smallest meaningful verification: API integration tests for schema and auth, a deterministic detector test with synthetic timestamps, a browser smoke check for log and incident pages, and a fresh Compose launch before publishing. Record failing cases and fix them before advertising performance or reliability.
