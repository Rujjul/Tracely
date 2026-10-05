# Tracely progress

Updated: 2026-10-05

## Current scope

Phases 1–4 are implemented: React/Vite, FastAPI, PostgreSQL, account migrations, email/password registration and login, Google sign-in, 30-minute sessions, owner-scoped projects, and hashed ingestion keys with rotation. The user confirmed real Google sign-in works after the clock-tolerance fix. Password recovery is implemented; SMTP credentials and live inbox verification remain pending. Frontend and backend retain their local startup workflow. Dashboard events and incidents remain labeled sample data. Validated, idempotent event ingestion is implemented; Phase 5 has not started.

## Previous checkpoint — Phase 2 data-model review

- [x] Read `DATA_MODEL.md` and compared its account/database requirements with the implementation.
- [x] Confirmed the required user columns, UUID user IDs, unique normalized emails, established password hashing, foreign keys, and timezone-aware UTC timestamps.
- [x] Added UUID primary keys to authentication support tables through migration `0002_auth_uuid_keys`, preserving existing rows and unique token/state hashes.
- [x] Retained nullable password hashes for Google-only accounts, as required by the approved Google sign-in flow; every account must have a password hash or Google identity.
- [x] All nine backend tests passed; API health reported `storage: connected` after the update.
- [ ] Complete a real Google sign-in and return to the dashboard for final provider verification.

At that checkpoint, Phase 2 matched the relevant data-model requirements. Phase 3 work is recorded below.

## Remaining Phase 2 verification

### Authentication follow-up — 2026-10-05

- [x] Rechecked Phase 2 against `BUILD.md` and `DATA_MODEL.md`; account schema, hashing, authorization, and 30-minute sessions remain aligned.
- [x] Fixed Google account-linking screen losing its confirmation step on refresh. The URL is cleared after successful authentication or choosing a different account screen.
- [x] Investigated a real callback failure (`InvalidValue`) and measured the local clock approximately one second behind Google. Added a bounded five-second token clock tolerance; signature, audience, nonce, verified email, and expiration validation remain enabled.
- [x] Added safe callback diagnostics that omit codes, tokens, secrets, and provider error contents.
- [x] All 26 backend tests passed before the clock-tolerance change; all 11 authentication tests passed afterward, including signed-token checks for small clock drift, rejection of excessive drift/expired tokens/wrong audience, Google session revocation, and safe error logging.
- [x] Frontend production build, browser refresh/cancellation checks for linking, and live API/database health passed. Changes are limited to authentication, its tests, and this progress file.
- [x] User confirmed real Google sign-in works after the fix. The more specific checks below still need confirmation.

- [x] Sign in with a real Google account and confirm the callback opens the dashboard (user confirmed).
- [ ] For an existing password account with the same Google email, confirm that linking requires the existing password.
- [ ] Confirm the real Google session survives a page refresh and is revoked by Sign out.

These are manual provider checks; their corresponding local authentication paths already passed automated tests. These checks remain separate from Phase 3 project management.

## Completed

### Password recovery — 2026-10-05

- [x] Added Forgot password from Sign in and Google linking, email request confirmation, new password/confirmation screens, invalid/expired-link errors, retry, and return to Sign in.
- [x] Added `POST /api/v1/auth/forgot-password` and `POST /api/v1/auth/reset-password`. Generic request responses do not disclose registered emails; Google-only accounts retain Google sign-in.
- [x] Applied migration `0005_password_resets`: UUID IDs, user foreign key/cascade, unique hashed 256-bit tokens, UTC timestamps, 15-minute expiry, and one outstanding link per user.
- [x] Reset consumes the token, hashes the new password with Argon2id, and revokes all login/link sessions in one committed transaction. Row locking serializes reset attempts and password login. No automatic login after reset.
- [x] Existing trusted-Origin and attempt limits apply; email requests have a one-minute per-account cooldown. New links invalidate old links. Tokens stay in URL fragments rather than page requests/referrers.
- [x] Added SMTP delivery with TLS and safe failure logs, environment examples, and Gmail App Password setup instructions for development without a domain. No email credentials were added to source control.
- [x] All 33 backend tests passed, including recovery token hashing, expiry/replacement/replay rejection, concurrent consumption, session revocation, validation, account privacy, throttling, and SMTP TLS/failure handling. Frontend production build passed.
- [x] Browser checks passed for navigation, missing-SMTP errors, reset-link refresh, mismatched passwords, invalid tokens, success URL cleanup, and mobile layout. Success email/reset screens used mocked responses; database behavior was verified separately by integration tests.
- [x] Local migration applied, API restarted, and API/PostgreSQL health verified. Unrelated phase features were preserved.
- [ ] Configure SMTP credentials in the root `.env`, restart the backend, and verify delivery and reset through a real inbox. The user has no domain; Gmail SMTP is documented as the development option.

Delivery uses an in-process background task, not a durable mail queue. If delivery fails or the process stops, request another link after one minute. Google-only accounts cannot gain a password through this recovery flow.

### Phase 4 — Event ingestion, 2026-10-05

- [x] Existing migration `0004_events` provides the event schema, unique `(project_id,event_id)` constraint, and project/time/service indexes.
- [x] `POST /api/v1/events` accepts one JSON event and an active `Authorization: Bearer <project_ingestion_key>`. The key determines the project; client-supplied project IDs, received timestamps, fingerprints, and unexpected fields are rejected.
- [x] Strict UUID, offset-aware timestamp, event type, level, and field validation. Timestamps normalize to UTC; `received_at` is generated by PostgreSQL. Request and exception events remain distinct.
- [x] Streamed body capped at 64 KiB, message/endpoint/exception type at 2 KiB UTF-8 each, stack at 8 KiB, and serialized metadata at 4 KiB. Status codes: integer 0–599; latency: finite and nonnegative. Malformed payloads return 422; size violations 413; unsupported content type/encoding 415.
- [x] Database insert commits before returning 201. Replays return 200 without overwriting or adding a row, including concurrent retries. The same client event ID can exist in different projects.
- [x] Wrong, missing, revoked, or deleted-project keys return 401; browser login cookies cannot authorize ingestion. Lock ordering coordinates ingestion with rotation/deletion.
- [x] Common secret fields, bearer credentials, project keys, and password/token assignments are redacted before storage. This is heuristic redaction, not a guarantee against arbitrary sensitive data; source-side scrubbing belongs to demo instrumentation in Phase 5.
- [x] Per-key rolling limit of 600 attempts/minute returns 429 and `Retry-After`. This local limiter is process-local and resets on restart; shared enforcement is required before running multiple workers.
- [x] All 25 backend tests passed: the existing 19 plus six ingestion scenarios covering persistence, replay, cross-project IDs, credential rejection, validation, body/field limits, redaction, concurrent duplicates, rate limits, and database failure rollback.
- [x] Final ingestion checks passed again after redaction/schema refinements. OpenAPI includes the event body and project-key authorization. Frontend production build passed after updating availability text.
- [x] Live API smoke check: 201 on first insert, 200 on replay, 401 without an ingestion key, exactly one persisted event, and healthy database connection. Synthetic account, project, keys, and event were removed afterward.

Use the API documentation at `http://127.0.0.1:8000/docs`: authorize with a project ingestion key, then submit the example in `API.md` to `POST /api/v1/events`. Do not use a browser session token. The response confirms storage only, not incident detection. No batching, demo service, live event-reading endpoint, detector, or investigator was added.

### Delete Project — 2026-10-04

- [x] Projects & Keys includes Delete project with a permanent-deletion warning, exact typed-name confirmation, and cancellation.
- [x] `DELETE /api/v1/projects/{project_id}` requires a valid owner session, trusted Origin, and exact `confirmation_name`. Other owners receive 404; missing authentication receives 401; mismatched names receive 422.
- [x] Project, all active/revoked keys, and existing events are deleted atomically through existing cascading foreign keys. Success is returned only after commit; failure rolls the transaction back. No new migration required.
- [x] UI removes the deleted project, refreshes the list, reports success, and displays deletion/refresh errors. Other projects and accounts remain untouched.
- [x] All 19 backend tests and frontend production build passed, including deletion authorization, confirmation rejection, cascade cleanup, unrelated-data preservation, and rollback on a simulated related-data deletion failure.
- [x] Browser checks passed for exact-name gating, cancellation, a simulated API error, successful deletion, list refresh, and reload persistence. Temporary test account was removed afterward.

### Phase 3 — Projects and ingestion keys

- [x] Migration `0003_projects` adds `projects` and `project_keys` with UUID primary keys, ownership foreign keys, UTC timestamps, unique key hashes, and at most one active key per project.
- [x] `POST /api/v1/projects` creates an owned project and returns its plaintext ingestion key once.
- [x] `GET /api/v1/projects` lists only the signed-in owner's projects with safe key prefixes; never returns plaintext keys or hashes.
- [x] `POST /api/v1/projects/{project_id}/keys/rotate` atomically revokes previous keys and generates a replacement. Project row locking serializes concurrent rotations.
- [x] Keys use 32 random bytes (256 bits); only SHA-256 hashes and short display prefixes are persisted. Responses are `Cache-Control: no-store`.
- [x] Unauthorized access returns 401; another owner's project returns 404. Ingestion keys cannot authorize project management. Project creation cannot override ownership.
- [x] Projects & Keys frontend supports creation, listing, copying a newly issued key, one-time dismissal, explicit rotation confirmation, loading/error/empty states, and expired-session handling.
- [x] Login cookie path now covers `/api/v1`; `/auth/me` upgrades old cookies without extending session expiry. Logout clears both cookie paths. Google linking cookies remain restricted to auth routes.
- [x] All 16 backend tests passed (nine authentication regression tests and seven project tests), including concurrent rotation, rollback on replacement failure, cross-owner rejection, cookie migration, and expired sessions.
- [x] Browser checks passed for project creation, clipboard copying, key dismissal, refresh persistence without key disclosure, rotation cancellation/confirmation, logout, and mobile layout. No browser errors. Synthetic test account and its projects were removed afterward.
- [x] Frontend production build passed. Migration `0003_projects` applied to the local PostgreSQL database.

### Earlier phases

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
- [x] Alembic migration `0001_accounts`: users, hashed session tokens, and temporary OAuth state; project tables were added later in `0003_projects`.
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
- At the Phase 2 data-model checkpoint, all nine tests passed after UUID-key alignment. Migration was `0002_auth_uuid_keys`; PostgreSQL timezone was UTC. Phase 3 subsequently added project tables through `0003_projects`.

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
| 3. Projects & keys | Complete; backend and browser checks passed | None; event ingestion remains Phase 4 |
| 4. Event ingestion | Complete; schema and validated idempotent endpoint | None; demo instrumentation and live explorer remain later phases |
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

Detection and investigation have not been implemented. Ingestion keys now accept events, while dashboard logs remain sample data until Phase 6. Email delivery, password reset, and email verification for password registrations are outside this phase. Attempt throttling is in memory for the current single-process local setup and resets on restart; shared enforcement is needed before scaling. Expired session/OAuth rows are pruned during new session/flow creation. Sample chart values are illustrative and are not calculated from the six sample event rows. Fonts use Google Fonts with local fallbacks. Backend requirements have version ranges; a full dependency lock is future work. Original specifications describe the eventual product; this tracker records actual behavior.
