# Phase 5: synthetic payment demo

An independent FastAPI service on `http://127.0.0.1:8001`. It makes no real payments and changes no real database/dependency behavior. `POST /payments` produces one request event, including exception fields on failure, through the existing Tracely ingestion endpoint. Admin, health, and documentation requests are excluded from telemetry.

## Start locally (PowerShell)

Start PostgreSQL, the Tracely API on port 8000, and the frontend using the root `progress.md` instructions. In Projects & Keys, create a dedicated demo project and copy its one-time ingestion key.

From the project root:

```powershell
cd demo-app
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# First setup only; preserve an existing .env.
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edit `demo-app/.env`: put the project key in `TRACELY_INGESTION_KEY`, the separately generated token in `DEMO_CONTROL_TOKEN`, and set `DEMO_FAULTS_ENABLED=true` for fault exercises. These secrets stay in the ignored `.env`; do not put them in URLs, screenshots, or shell arguments. A browser session is not an ingestion key. The existing backend virtual environment can also run this demo because it already contains the dependencies.

```powershell
.\.venv\Scripts\python.exe -m uvicorn demo.main:app --host 127.0.0.1 --port 8001 --env-file .env --no-access-log --no-proxy-headers
```

Use one worker. Fault state and telemetry queues are process-local and reset on restart. Keep the listener on loopback; never expose this synthetic app through a reverse proxy or public tunnel. Controls require explicit opt-in, a loopback peer and Host, and the separate `X-Demo-Control-Token` header. They do not enable any faults in Tracely itself. Keep proxy-header handling disabled so a forwarded address cannot impersonate a local client.

## Run all fault scenarios

In a second terminal from `demo-app`:

```powershell
.\.venv\Scripts\python.exe run_scenarios.py --count 3
```

This runs healthy → database timeout → healthy → unhandled exception → healthy → slow dependency → healthy. It prints synthetic JSON evidence with UTC stage boundaries, request IDs, event IDs, status codes, client latencies, and delivery counters. It resets the fault to `none` in a `finally` block, including when a scenario fails. Stop the demo to reset state if the runner is forcibly terminated. You can save the JSON output for inspection; it contains synthetic IDs, not secrets. Do not run competing scenario processes against the same demo.

| Fault | `/payments` behavior | Stored request evidence |
|---|---|---|
| `none` | 200 after a small delay | INFO, ordinary latency |
| `db_timeout` | Synthetic timeout after 100 ms; 500 | ERROR, `DatabaseTimeout`, safe stack frames |
| `unhandled_exception` | Raises a synthetic runtime exception; 500 | ERROR, `RuntimeError`, safe stack frames |
| `slow_dependency` | 200 after a 250 ms fake dependency delay | INFO, increased latency; not a failed request |

`POST /_demo/fault` accepts `{"mode":"none"}` or one of the fault names. `GET /_demo/fault` returns mode and last change time; both require the control header. `GET /health` exposes queue/delivery/drop/retry counters without secrets. `POST /payments` returns `X-Request-ID` and `X-Tracely-Event-ID` to correlate each response with its stored event.

## Delivery and privacy

- One bounded queue of 128 events and one worker; requests do not await ingestion. Full queues drop new events and increment counters.
- Each attempt is bounded to one second; up to three attempts for transport errors/5xx. Retries reuse the exact event ID. Ordinary 4xx are not retried. A 429 is retried only if its `Retry-After` is at most one second; otherwise the event is dropped rather than retried too early.
- Graceful shutdown allows up to five seconds to drain, then counts remaining events as dropped. The queue is not durable: process termination can lose queued events. This is a demo, not a production telemetry SDK.
- Source minimization excludes request bodies, headers, query strings, actual dynamic paths, exception messages, stack source lines, and locals. Only a route template, generated IDs, safe stack frame names, method, and fixed demo metadata are emitted. Fault labels and stage ground truth stay in the runner output, not telemetry metadata.
- Rotate a project key in Tracely and update `demo-app/.env`, then restart the demo. Revoked/wrong keys produce dropped-event counters; demo requests remain available.
- Remote ingestion URLs require HTTPS; redirects are not followed, so keys are not forwarded to redirect targets.

## Verify

From `backend`, run `.\.venv\Scripts\python.exe -m pytest tests/test_demo.py -q`. Integration tests create a disposable PostgreSQL schema and exercise the real ingestion route for every fault, recovery, and lost-acknowledgement replay. Additional checks cover local fault gating, source privacy, queue limits, bounded shutdown, rejected credentials, and ingestion outages.

The scenario runner checks acknowledgements and counters. Persisted rows can be checked through authorized local database inspection using the emitted event IDs and the demo project's ID. There is no event-read API or live dashboard in Phase 5; those belong to Phase 6. Incident timestamps, detection, and investigator evaluation are not available yet. Stage timestamps are fault ground truth only. The short runner is a functional smoke check, not the five-minute benchmark specified for Phase 12.
