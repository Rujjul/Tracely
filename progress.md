# Tracely progress

Updated: 2026-09-28

## Current scope

React/Vite frontend and Python backend foundation. PostgreSQL and Docker are deferred at the user's request. Preview data is explicitly labeled and is not evidence of completed ingestion or detection.

## Completed

- [x] Tracely branding and responsive React + TypeScript + Vite application.
- [x] Overview with sample metrics, traffic chart, service health, and incident summary.
- [x] Event explorer with text search, severity filtering, empty state, and event details.
- [x] Sample incident list/details and local setup page.
- [x] Live API connection indicator, checked every 15 seconds.
- [x] FastAPI package, dependencies, isolated Python virtual environment, and OpenAPI documentation.
- [x] `GET /api/v1/health`, including explicit `storage: not_configured`.
- [x] CORS defaults for local frontend; environment examples and repository ignore rules.
- [x] Frontend dependency lockfile.

## Verification

- TypeScript check and production build passed (`npm run build`).
- Frontend server returned HTTP 200 on port 5173.
- Backend health endpoint returned `status: ok` on port 8000.
- Frontend dependency audit reported zero vulnerabilities at installation.
- Browser checks passed for the live API indicator, navigation, event search, severity filter, empty state, detail dialog, and Escape dismissal.
- Mobile viewport check passed at 390px after fixing horizontal overflow.

## Run locally (PowerShell)

Backend, from the project root using the environment already created:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On a fresh checkout, install Python 3.12+ and create the environment first:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend, in a separate terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Frontend: http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs.
The frontend API URL defaults to port 8000; override it with `VITE_API_BASE_URL` in `frontend/.env`. Backend CORS can be set through the `CORS_ORIGINS` process environment variable. No environment file is required with defaults.

## Fourteen-phase tracker

| Phase | Status | Remaining work |
|---|---|---|
| 1. Local setup | Partial — requested subset complete | PostgreSQL and Compose deferred |
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
| 13. Docker delivery | Deferred | Containers, volumes, startup migrations |
| 14. Documentation & handoff | Partial | Final instructions, benchmarks, deployment decision |

## Limitations

No authentication, project creation, ingestion, database, detector, investigator, or Docker configuration has been implemented. Sample chart and summary values are illustrative and are not calculated from the six sample event rows. Fonts use Google Fonts with local fallbacks. Backend requirements have version ranges; a full dependency lock is future work. Original specification documents describe the eventual product rather than the current runnable subset.
