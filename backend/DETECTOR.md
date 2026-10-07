# Phase 7 request-failure detector

The worker reads persisted Phase 4/5 request events and writes incidents. It is separate from FastAPI, so API restarts and request handling do not run detector loops. Phase 8 exception grouping and owner-only detail lookup are now implemented separately; see `EXCEPTION_GROUPING.md`. The browsable Phase 9 incident list and investigations remain future work. The incident list is still explicitly sample data.

## Run (PowerShell)

Start PostgreSQL and the existing API normally. In a separate terminal from the repository root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.detector_worker
```

The worker loads the root `.env`. Stop with Ctrl+C; restart with the same command after reboot. `--once` runs one evaluation for diagnostics and exits nonzero on database failure. Repeated one-shot invocations do not bypass the persisted cadence. No dependency or Docker Compose changes are required.

| Environment variable | Default |
|---|---|
| `DETECTOR_WINDOW_SECONDS` | 300 |
| `DETECTOR_INTERVAL_SECONDS` | 30 |
| `DETECTOR_MIN_REQUESTS` | 20 |
| `DETECTOR_MIN_FAILURES` | 5 |
| `DETECTOR_TRIGGER_RATE` | 0.10 |
| `DETECTOR_RESOLVE_RATE` | 0.05 |

There must be two consecutive qualifying evaluations to open or resolve an incident. Configuration is validated at startup. Durations/counts are positive integers; the interval cannot exceed the window, the window is at most one day, and `0 < resolve rate < trigger rate <= 1`.

## Rules

- Group by project and service. Read `received_at` in `(evaluation time - window, evaluation time]`, using the database clock. Client timestamps and future received timestamps do not influence the current window.
- Count only `event_type=request`. A failure is `status_code >= 500 OR level = ERROR`; a request satisfying both still counts once. Exception-only events never increase the numerator or denominator. Successful slow requests are not request failures.
- Open after two checks with at least 20 requests, five failures, and a failure rate of at least 10%. Type is `request_failure_rate`; severity is a fixed `warning`, not an inferred impact assessment.
- Keep one active incident per project/service/type. Subsequent checks update the same incident's latest rolling-window counts, not cumulative totals.
- Resolve after two checks with sufficient request volume and rate strictly below 5%. Exactly 5% is not recovery. A middle-band evaluation is `neutral`; a window below the volume minimum is `insufficient_data`. Both reset streaks and leave an active incident open.
- `started_at` is the first failure in the first qualifying window. `last_seen_at` advances only to an actual observed failure, not each worker tick. `resolved_at` is the confirmation time. Resolved incidents retain their final counters; a later sustained failure creates a new row.

## Persistence and safety

Migration `0006_detector` adds the data-model incident columns with UUID keys, UTC-aware timestamps, ownership through the project FK, deletion cascades, count/status constraints, and a partial unique index for active incidents. `detector_states` stores per-project/service streaks, evaluation status, counts, timestamps, and policy provenance.

Incidents, counters, and streaks commit in one transaction. A schema-scoped transaction advisory lock makes duplicate workers skip overlapping evaluations. Per-service cadence checks also prevent sequential duplicate invocations from counting twice. Project locks coordinate with deletion; deleting a project cascades its incidents and detector state along with events/keys. Database failures roll back the entire tick and retry on the next interval. Statements/lock waits are bounded, and logs do not print credentials or event contents.

Restarting within two intervals preserves consecutive checks. Longer gaps, policy/version changes, or a scheduling-cadence change reset confirmation streaks. Low traffic does not invent recovery. Active incidents retain their opening window/count/rate policy until resolved; new episodes use the current configuration. Worker scheduling follows the current interval, which is also recorded in state. This avoids changing an active episode's recovery definition midway through it.

This is a local worker, not a distributed production scheduler: it scans known projects/services, retains one state row per seen request service, and serializes ticks. State cleanup for historical services and retention tuning remain future operational work. A stalled or stopped worker does not affect ingestion, but incident state stays unchanged until it resumes. It does not backfill every missed historical window.

## Verify

From `backend`, run `.\.venv\Scripts\python.exe -m pytest tests/test_detector.py -q`. Tests use disposable schemas and deterministic clocks to cover defaults, volume/rate boundaries, exception exclusion, received-time windows, opening/update/recovery/reopening, restart persistence, concurrency, configuration changes, deletion cascades, and rollback.

The Phase 5 short scenario runner is not long enough to guarantee two default 30-second detector checks. For a manual default-policy check, send at least 20 requests including five failures into a dedicated demo project, keep the worker running for two qualifying ticks, then generate sufficient healthy traffic as old failures leave the five-minute window. Use authorized local database inspection of `incidents` and `detector_states` to inspect results; no unprotected read/debug endpoint is added. Event evidence remains available to the project owner in Events.

The implementation smoke test used an isolated schema and real API/worker processes with an eight-second window and one-second interval: healthy traffic produced none, failures opened one incident, repeat evaluation preserved it, and healthy recovery resolved it. This accelerated check is not a production benchmark or a change to the defaults.
