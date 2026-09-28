# Tracely progress

Updated: 2026-09-28

## Current scope

Phases 1 and 2 are implemented: React/Vite, FastAPI, PostgreSQL, account migrations, email/password registration and login, Google sign-in, and 30-minute sessions. A real Google account completion remains a manual verification step. Frontend and backend retain their local startup workflow. Dashboard events and incidents remain labeled sample data. Phase 3 has not started.

## Latest checkpoint — Phase 2 data-model review

- [x] Read `DATA_MODEL.md` and compared its account/database requirements with the implementation.
- [x] Confirmed the required user columns, UUID user IDs, unique normalized emails, established password hashing, foreign keys, and timezone-aware UTC timestamps.
- [x] Added UUID primary keys to authentication support tables through migration `0002_auth_uuid_keys`, preserving existing rows and unique token/state hashes.
- [x] Retained nullable password hashes for Google-only accounts, as required by the approved Google sign-in flow; every account must have a password hash or Google identity.
- [x] All nine backend tests passed; API health reported `storage: connected` after the update.
- [ ] Complete a real Google sign-in and return to the dashboard for final provider verification.

Phase 2 matches the relevant data-model requirements. No Phase 3 or later backend features were added.

## Remaining Phase 2 verification

- [ ] Sign in with a real Google account and confirm the callback opens the dashboard.
- [ ] For an existing password account with the same Google email, confirm that linking requires the existing password.
- [ ] Confirm the real Google session survives a page refresh and is revoked by Sign out.

These are manual provider checks; their corresponding local authentication paths already passed automated tests. Phase 3 remains not started.

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
- [x] Alembic migration `0001_accounts`: users, hashed session tokens, and temporary OAuth state. No projects, API keys, or events tables.
- [x] Data-model alignment migration `0002_auth_uuid_keys`: UUID primary keys for session and OAuth-state tables; token/state hashes remain unique. Existing rows and sessions are preserved. Required user columns, normalized unique email, Argon2id hashing, foreign keys, and timezone-aware UTC storage already matched `DATA_MODEL.md`.
- [x] Separate responsive Sign up and Sign in screens with validation, password visibility, confirmation, loading, and error states.
- [x] Normalized unique email addresses and Argon2id password hashes (12–128-character registration passwords).
- [x] Opaque HTTP-only, SameSite=Lax session cookie; server-enforced absolute 30-minute expiry, refresh persistence, and logout revocation. No automatic session extension or localStorage tokens.
- [x] Google authorization-code flow with state, nonce, PKCE, server-side token verification, and verified email checks. Secrets remain backend-only.
- [x] Matching password accounts require their existing password before linking Google; the browser-bound link request expires in five minutes and is single-use.
- [x] Trusted-Origin checks on authentication mutations, no-store responses, sanitized errors, and local single-process attempt throttling.
- [x] Existing sample dashboard now opens after authentication; health endpoint remains public.

## Verification

- TypeScript check and production build passed (`npm run build`).
- Frontend server returned HTTP 200 on port 5173.
- Backend health endpoint returned `status: ok` on port 8000.
- Frontend dependency audit reported zero vulnerabilities at installation.
- Browser checks passed for the live API indicator, navigation, event search, severity filter, empty state, detail dialog, and Escape dismissal.
- Mobile viewport check passed at 390px after fixing horizontal overflow.
- At Phase 1 completion, `docker compose up -d --wait` passed; PostgreSQL 17.11 was healthy and authenticated SQL queries succeeded. The public schema had zero application tables at that checkpoint; Phase 2 subsequently added account/authentication tables.
- Updated backend returned HTTP 200 with `storage: connected`; invalid database credentials produced a sanitized 503, and unconfigured standalone mode still passed.
- Rechecked frontend production build, API docs HTTP 200, frontend HTTP 200, browser API-connected indicator, sample event search, and absence of browser errors after database setup.
- Phase 2: nine tests passed after the data-model review. Coverage includes migration setup in disposable schemas, existing-data preservation, UUID keys, duplicate accounts, password hashing, invalid credentials, unauthenticated access, expiry, logout revocation, origin validation, Google linking, OAuth state replay, invalid nonce/unverified email, disabled Google configuration, and throttling. Provider responses are mocked in automated Google flow tests.
- Phase 2 browser checks passed: register → dashboard → refresh → sign out → incorrect password → successful sign in, plus mobile overflow and console checks. Frontend production build passed.
- Live Google authorization opens Google's sign-in page displaying “to continue to Tracely.” A full real-account consent/callback has not been performed; the user must complete that last manual check.
- Data-model review: all nine tests passed after UUID-key alignment, including migration of existing session/OAuth rows and continued uniqueness enforcement. Local migration is at `0002_auth_uuid_keys`; PostgreSQL timezone is UTC. No Phase 3 tables or features added.

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
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file ../.env --no-access-log
```

On a fresh checkout, install Python 3.12+ and create the environment first:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --env-file ../.env --no-access-log
```

Frontend, in a separate terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Frontend: http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs.
The auth frontend API URL defaults to port 8000 on the browser's hostname; override it with `VITE_API_BASE_URL` in `frontend/.env`. Use `http://127.0.0.1:5173` for the configured local Google flow. Backend CORS can be set through `CORS_ORIGINS`. Without database configuration, the public health endpoint still works, but accounts require PostgreSQL and the migration.

## Google and session configuration

Root `.env` supports `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`, and `COOKIE_SECURE`. The current client fields are populated; never commit or put the client secret into frontend variables.

- Google Web client authorized redirect URI: `http://127.0.0.1:8000/api/v1/auth/google/callback`.
- Frontend return URL: `http://127.0.0.1:5173`.
- Local HTTP uses `COOKIE_SECURE=false`. HTTPS deployments require `COOKIE_SECURE=true` and matching HTTPS origins/redirects.
- Access logs are disabled in the startup command to avoid recording OAuth codes in callback query strings.
- Missing Google credentials disable the Google button without preventing password login.
- This replaces the original API specification's browser bearer-token proposal with the agreed HTTP-only cookie session. Endpoints: `/api/v1/auth/register`, `/login`, `/logout`, `/me`, `/config`, `/google/start`, `/google/callback`, `/google/link`. Mutation requests require a trusted `Origin`; frontend requests include cookies.

Run auth tests from `backend` with `.\.venv\Scripts\python.exe -m pytest tests -q`. Tests create and remove uniquely named schemas in the configured database, preserving real accounts.

## Fourteen-phase tracker

| Phase | Status | Remaining work |
|---|---|---|
| 1. Local setup | Complete | None; PostgreSQL starts and API connection works |
| 2. Database & accounts | Implemented; data-model aligned; nine tests and browser checks passed | User completes real Google sign-in for final provider end-to-end verification |
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

No projects, API keys, event ingestion, detector, or investigator have been implemented. Email delivery, password reset, and email verification for password registrations are outside this phase. Attempt throttling is in memory for the current single-process local setup and resets on restart; shared enforcement is needed before scaling. Expired session/OAuth rows are pruned during new session/flow creation. Sample chart values are illustrative and are not calculated from the six sample event rows. Fonts use Google Fonts with local fallbacks. Backend requirements have version ranges; a full dependency lock is future work. Original specifications describe the eventual product; this tracker records actual behavior.
