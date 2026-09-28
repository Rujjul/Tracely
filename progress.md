# Tracely progress

Updated: 2026-09-28

## Current scope

Phase 1 is complete: React/Vite frontend, Python backend, and local PostgreSQL through Docker Compose. Frontend and backend retain their existing local startup workflow. Preview data is explicitly labeled and is not evidence of completed ingestion or detection. Phase 2 has not started.

## Completed

- [x] Tracely branding and responsive React + TypeScript + Vite application.
- [x] Overview with sample metrics, traffic chart, service health, and incident summary.
- [x] Event explorer with text search, severity filtering, empty state, and event details.
- [x] Sample incident list/details and local setup page.
- [x] Live API connection indicator, checked every 15 seconds.
- [x] FastAPI package, dependencies, isolated Python virtual environment, and OpenAPI documentation.
- [x] `GET /api/v1/health`: checks PostgreSQL with `SELECT 1` when `DATABASE_URL` is set; reports `storage: connected`, or returns HTTP 503 without exposing connection details on failure. Without configuration, the existing `storage: not_configured` behavior is preserved.
- [x] CORS defaults for local frontend; environment examples and repository ignore rules.
- [x] Frontend dependency lockfile.
- [x] PostgreSQL 17 Compose service with readiness check and named persistent volume.
- [x] Local-only database access on `127.0.0.1:5433` (5432 was already occupied).
- [x] Root `.env.example`, ignored local `.env`, and Python PostgreSQL driver.

## Verification

- TypeScript check and production build passed (`npm run build`).
- Frontend server returned HTTP 200 on port 5173.
- Backend health endpoint returned `status: ok` on port 8000.
- Frontend dependency audit reported zero vulnerabilities at installation.
- Browser checks passed for the live API indicator, navigation, event search, severity filter, empty state, detail dialog, and Escape dismissal.
- Mobile viewport check passed at 390px after fixing horizontal overflow.
- Phase 1 completion: `docker compose up -d --wait` passed; PostgreSQL 17.11 is healthy and authenticated SQL queries succeed. The public schema has zero application tables.
- Updated backend returned HTTP 200 with `storage: connected`; invalid database credentials produced a sanitized 503, and unconfigured standalone mode still passed.
- Rechecked frontend production build, API docs HTTP 200, frontend HTTP 200, browser API-connected indicator, sample event search, and absence of browser errors after database setup.

## Run locally (PowerShell)

Start PostgreSQL from the project root (copy the environment example once on a fresh checkout; preserve any existing `.env`):

```powershell
Copy-Item .env.example .env
docker compose up -d --wait
```

Compose currently manages PostgreSQL only. Its `tracely_postgres_data` volume retains database files across normal restarts and `docker compose down`. Use `docker compose stop` to stop it; do not use `down -v` unless you intend to delete its data. The example credentials are for local development only. Keep `DATABASE_URL` consistent if changing database credentials or port; credentials initialize a new volume only.

Backend, from the project root using the environment already created:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file ../.env
```

On a fresh checkout, install Python 3.12+ and create the environment first:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file ../.env
```

Frontend, in a separate terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Frontend: http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs.
The frontend API URL defaults to port 8000; override it with `VITE_API_BASE_URL` in `frontend/.env`. Backend CORS can be set through the `CORS_ORIGINS` process environment variable. Omit `--env-file ../.env` to run the backend without a database as before.

## Fourteen-phase tracker

| Phase | Status | Remaining work |
|---|---|---|
| 1. Local setup | Complete | None; PostgreSQL starts and API connection works |
| 2. Database & accounts | Not started | Migrations, registration, login, password hashing |
| 3. Projects & keys | Not started | Ownership, hashed keys, rotation |
| 4. Event ingestion | Not started | Validation, storage, idempotency |
| 5. Demo service | Not started | Real instrumentation and fault toggles |
| 6. Log explorer | Frontend preview only | Live retrieval, pagination, authorization |
| 7. Incident detector | Not started | Rolling windows and incident lifecycle |
| 8. Exception grouping | Not started | Fingerprints and real incident evidence |
| 9. Incident dashboard | Frontend preview only | Real overview and incident endpoints |
| 10. Evidence investigation | Not started | Bounded retrieval and cited rule summaries |
| 11. Optional local AI | Not started | Model validation and fallback |
| 12. Evaluation | Not started | Controlled scenarios, integration tests, metrics |
| 13. Docker delivery | Not started (database foundation ready) | App containers, startup migrations, complete demo delivery |
| 14. Documentation & handoff | Partial | Final instructions, benchmarks, deployment decision |

## Limitations

No application tables, migrations, authentication, users, projects, API keys, event ingestion, detector, or investigator have been implemented. Sample chart and summary values are illustrative and are not calculated from the six sample event rows. Fonts use Google Fonts with local fallbacks. Backend requirements have version ranges; a full dependency lock is future work. Original specification documents describe the eventual product rather than the current runnable subset.
