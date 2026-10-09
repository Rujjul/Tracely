# Tracely progress

Updated: 2026-10-09

## Render + Neon deployment — 2026-10-08

- [x] Deployed API on Render Free in Ohio: https://tracely-api-mlqu.onrender.com. Existing migrations ran successfully against the user's fresh Neon Free PostgreSQL 18 database. Public health reports storage connected.
- [x] Connected https://tracely-rs.vercel.app to Render through a same-origin Vercel API proxy. Retained secure HTTP-only session cookies, existing application logic and local development setup. Vercel production deployment: dpl_GGxBMha8St78MEdA87pnBQ26Ss3H.
- [x] Public smoke checks passed: registration, session, secure cookie, logout, password login, project/key creation, ingestion, idempotent replay, event listing, dashboard overview, and unauthenticated access rejection. No local listeners were found on 5173/8000. Synthetic project/events/keys were deleted; one synthetic test account remains.
- [x] Deployment startup script syntax and frontend production build passed. Deployment setup committed as 41ce170; no paid compute or Render database provisioned.
- [x] User accepted demo limitations: Render idle sleep, continuous detector pending, SMTP password-reset delivery pending. Worker was not deployed and incident lifecycle was not verified in the cloud.
- [ ] Google login remains pending: credential values initially included surrounding quotes. Browser tool output accidentally exposed the old Google client secret; user was asked to rotate it and enter the replacement privately without quotes. Rotation and end-to-end Google consent still require verification. No secret values are recorded here.
- [ ] Cloud backups/restore, quota monitoring and cold-start behavior remain unverified. No existing local accounts/events were imported.
- [ ] Vercel build reported one high-severity dependency audit finding; investigate separately without an unreviewed dependency upgrade.

## Phase 9.5 — guided demo and debugging brief

- [x] Added a five-step, explicitly synthetic walkthrough under Setup: demo project, failure, grouped evidence, brief preview/copy and recovery. Supports back/next, skip/restart, keyboard focus and Projects navigation; no telemetry or fault controls are invoked.
- [x] Added owner-only `GET /projects/{project_id}/incidents/{incident_id}/debugging-brief`, integrated into real incident details. Exports at most ten cited events, clipped excerpts, project/service context, incident timestamps, detector counts/window length and evidence omissions. Exact counter evaluation time is honestly marked unavailable.
- [x] Redacts common credentials, email addresses, IPv4 addresses and phone-like strings. Omits metadata and full stacks; warns that redaction is best effort and requires review before sharing.
- [x] Preview precedes copying, with copy feedback and an always-available manual selection fallback. Briefs tell a coding assistant to inspect evidence/code, separate facts/hypotheses, propose a minimal fix and explain tests/rollback. Nothing is sent to an AI automatically.
- [x] All 67 backend tests passed, including ownership, cross-project isolation, ingestion-key rejection, citations, redaction, clipping and missing evidence. Frontend production build passed.
- [x] Browser component smoke checks passed: keyboard next-step/focus, evidence disclosure, preview, clipboard success, full manual selection, recovery, project callback, skip/restart and no horizontal overflow at 390px. The harness was removed afterward; real authenticated endpoint behavior was covered by integration tests.
- [ ] Production deployment is not performed by this task. Phase 9.5 and Phase 10 remain local changes.

## Phase 10 — deterministic investigations

- [x] Added data-model-aligned `investigations` table in migration `0009_investigations`, with UUIDs, JSONB evidence fields, UTC creation times, latest-version index and cascading incident/project deletion. Applied to local PostgreSQL; production migration is not applied by this task.
- [x] Added owner-only investigation run/refresh and latest-result endpoints. Mutations require the trusted browser origin; ingestion keys cannot read or run investigations.
- [x] Bounded retrieval to 200 same-project/service events and 24 hours, including five-minute pre-onset context where available. Deterministic error ranking, sample-only request counts, ten representative groups, clipped/redacted stacks, event citations, explicit truncation/missing-evidence limits and unverified candidate causes. No model or external calls.
- [x] Integrated Run/Refresh investigation into incident details, with saved result loading, citation buttons opening existing event details, excerpt disclosure, loading/error/retry states and mobile wrapping. Historical versions persist; UI retrieves latest only.
- [x] All **65 backend tests passed**, including new coverage for ownership, trusted Origin, citations, saved versions, project deletion cascade, time boundaries, limits, redaction and absent evidence. Frontend production build passed; diff whitespace check passed.
- [ ] Live-browser interaction/accessibility smoke check and production deployment remain pending. This implementation has not been pushed or deployed to Render/Vercel.

Phase 9.5 is now implemented locally; Phase 11 optional model drafting is not started. The cloud detector remains unavailable under the accepted free-tier deployment limits.

## Current scope

Phases 1–9 are implemented: React/Vite, FastAPI, PostgreSQL, account migrations, email/password registration and login, Google sign-in, 30-minute sessions, owner-scoped projects, hashed ingestion keys with rotation, validated idempotent ingestion, and an instrumented synthetic demo service with protected fault controls. The user confirmed real Google sign-in works after the clock-tolerance fix. Password recovery is implemented; the existing checklist marks SMTP setup and live inbox verification complete. Frontend and backend retain their local startup workflow. The Events page now reads stored project data with owner-only access, filters, pagination, and details. Overview metrics, recent events, and the incident list now read owned-project data. Phase 7 now runs a separate worker for persistent request-failure incidents. Phase 8 adds stable exception fingerprints and owner-only stored incident details. Phase 9 adds the browsable incident dashboard and project overview.

## Phase 9 — project overview and incident dashboard

- [x] Replaced authenticated overview and incident sample data with owner-scoped APIs and stored PostgreSQL results. Removed the hard-coded incident badge and sample modals.
- [x] Overview includes request totals, failure rate, median recorded request latency, current active incidents, 24 time buckets, service counts/last detector state, and recent event links. Supports 1-hour/24-hour/7-day windows, exact service filtering, and manual refresh.
- [x] Incident list supports active/resolved status, exact service, inclusive/exclusive UTC start-time filters, and keyset pagination. Click Inspect to open Phase 8 evidence without copying UUIDs; back navigation preserves the list.
- [x] Added migration `0008_dashboard` for incident pagination; applied locally and verified Alembic is at head. No detector/auth/ingestion logic changed.
- [x] Full backend suite: **61 passed** (five new Phase 9 tests). Covered metrics/denominators/buckets, latency, empty states, ownership, time bounds, status/service filters, same-time UUID pagination, cursor binding, and service response limits.
- [x] Browser checks with synthetic responses passed for overview/event dialog, incident navigation, paging, filters, project switching, empty/error/retry states, session expiry, and desktop/mobile overflow. Visually inspected desktop/mobile screenshots. Frontend build passed.
- [x] Updated API/usage documentation and public feature labels. Investigations remain Phase 10; no AI or later-phase work added.

## Phase 8 — exception grouping and incident details

- [x] Added versioned server-computed fingerprints at ingestion; similar Python/demo stack frames ignore line-number changes while different types/modules/functions remain separate. Grouping is scoped by project and service without changing detector counts.
- [x] Applied migration `0007_exception_groups` and ran the restart-safe backfill locally: 230 historical events fingerprinted, preserving original evidence.
- [x] Added owner-only incident detail API with lifecycle timestamps, recorded policy, latest-window counters, exception groups and correlated event evidence. Responses cap groups at 20 and events at 50 with explicit truncation flags and limitations.
- [x] Added stored-incident UUID lookup to Incidents and reused the event detail dialog for stack traces/fingerprints. Sample list remains labeled; live dashboard remains Phase 9.
- [x] Full backend suite: **56 passed**, including five Phase 8 tests. Frontend production build passed. Hidden browser checks using synthetic API responses passed for lookup, groups, event details/Escape, 404 handling, desktop/mobile overflow, and no browser errors.
- [x] Added `backend/EXCEPTION_GROUPING.md` with grouping limitations, migration/backfill commands, and usage. No Phase 9 dashboard, investigation, or AI added.

## Previous checkpoint — Phase 2 data-model review

- [x] Read `DATA_MODEL.md` and compared its account/database requirements with the implementation.
- [x] Confirmed the required user columns, UUID user IDs, unique normalized emails, established password hashing, foreign keys, and timezone-aware UTC timestamps.
- [x] Added UUID primary keys to authentication support tables through migration `0002_auth_uuid_keys`, preserving existing rows and unique token/state hashes.
- [x] Retained nullable password hashes for Google-only accounts, as required by the approved Google sign-in flow; every account must have a password hash or Google identity.
- [x] All nine backend tests passed; API health reported `storage: connected` after the update.
- [x] Real Google sign-in was subsequently confirmed working by the user on 2026-10-05 after the clock-tolerance fix.

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
- [x] For an existing password account with the same Google email, confirm that linking requires the existing password.
- [x] Confirm the real Google session survives a page refresh and is revoked by Sign out.

These are manual provider checks; their corresponding local authentication paths already passed automated tests. These checks remain separate from Phase 3 project management.

## Completed

### Public landing page — 2026-10-07

- [x] Built the public landing page from `LANDING_PAGE_DESIGN.md`: warm cream/navy/coral/mint palette, existing typography/icons, hero illustration, labeled interactive sample preview, how it works, available features, upcoming capabilities, and repeated account actions.
- [x] Unauthenticated visitors see the landing page at `/`. Sign up opens `/?auth=register`; Sign in opens `/?auth=login`. Refresh preserves the selected auth screen. Existing valid sessions open the authenticated dashboard directly.
- [x] Preserved Google linking/error callbacks, reset-token links, password recovery, session expiry, and existing dashboard behavior. Logout returns to an explicit sign-in URL. No backend, database, or dashboard code was changed.
- [x] Sample preview supports local search, an error-level toggle, and expandable details without backend access. Synthetic content and illustrated workflow are labeled; live incident views and later investigation capabilities remain explicitly upcoming. No testimonials or performance claims were added.
- [x] Added finite graphical animations, reduced-motion support, a keyboard skip link, visible focus styles, keyboard-operable details with Escape/focus return, and responsive layouts. Final browser checks confirmed no page overflow or overlapping illustration cards at 320, 390, 800, and 1440px widths.
- [x] TypeScript/production build passed. Browser checks covered preview interactions, auth entry/refresh/back navigation, signup/login/logout, direct authenticated dashboard access, Google callback screens, reset links, session expiry, reduced motion, and keyboard navigation. Authentication responses were mocked for these frontend regression checks; no real account was created and no new live Google/email verification was performed.

### Phase 7 — Request-failure detector, 2026-10-06

#### User-run verification with default settings — 2026-10-06

- [x] User-provided demo output reported **525 delivered events, zero dropped, zero retries, and zero queued**, with the fault reset to healthy at completion.
- [x] User-provided detector logs confirmed the default **300-second window / 30-second interval** lifecycle: no openings initially; **one incident opened at 17:36:02**, subsequent checks updated the existing incident, and **resolution occurred at 17:42:33** (local terminal times, Asia/Calcutta).
- [x] No additional openings appeared through the supplied final check at **17:50:04**. The displayed run had `evaluated: 1` and `skipped: 0`, confirming the service was evaluated without duplicate-worker skips.
- [x] The user’s Events screenshot showed stored `payment-api` failure requests with `ERROR` and HTTP 500. Together with the delivery counters and detector logs, this verifies the demo → ingestion → live Events explorer → incident lifecycle integration for this synthetic run.

This records the user's supplied output, not a new test execution or independent database inspection. The Incidents screen remains sample data; live incident views are still deferred. No application code or running services were changed for this progress update.

#### Implementation and automated verification

- [x] Added migration `0006_detector` with the `incidents` data-model columns, UUID keys, UTC timestamps, project cascades, valid lifecycle/count constraints, a project/status index, and a partial unique index preventing duplicate active project/service/type incidents.
- [x] Added durable `detector_states` for confirmation streaks, evaluation time/status, rolling counts, first failure, detector version, and policy. Restarts preserve progress; duplicate/early ticks do not advance it. Long gaps and policy/cadence changes reset streaks.
- [x] Added `python -m app.detector_worker` and `--once`. Default cadence is 30 seconds over a five-minute received-time window; only request events count. Failures are status >= 500 or level ERROR, counted once. Exception-only events are excluded.
- [x] Opening requires >=20 requests, >=5 failures, and >=10% failures for two evaluations. Active rows update in place. Resolution requires two sufficiently busy windows strictly below 5%; neutral and insufficient-data windows reset streaks but retain active incidents. A later sustained episode creates a new incident.
- [x] Incident counts represent the latest window; started/last-seen timestamps refer to observed failure evidence, and resolved time records the confirming evaluation. Severity is fixed at warning for this rule. Active episodes retain their opening detection/recovery policy; current configuration governs scheduling and new episodes.
- [x] Evaluations commit incident and state changes atomically. Advisory locking, persisted cadence, project locks, deletion cascades, and bounded database waits protect duplicate workers, project removal, and rollback. Worker logs omit credentials/event contents and retry database failures next interval.
- [x] Eight detector tests passed; full backend suite **51 passed**. Coverage includes volume/rate boundaries, exception exclusion, received-time bounds, restart/cadence/configuration handling, concurrent workers, opening/update/resolution/reopening, project/service isolation, deletion cascades, and rollback.
- [x] Isolated live API/worker smoke check passed: healthy traffic produced no incidents, repeated failures opened one, repeated checks retained one, and healthy traffic resolved it. The test used an eight-second window and one-second interval only in its temporary schema. Temporary processes/schema were removed; existing projects were untouched by synthetic data.
- [x] Applied the migration to the local database, verified a normal one-shot evaluation, and started the continuous worker with default 300/30-second settings. Frontend production build passed; frontend HTTP 200 and API `storage: connected` verified after starting their existing services.
- [x] Added `.env.example` detector settings and `backend/DETECTOR.md` run/behavior documentation. Existing sample incident labels now distinguish the implemented worker from the deferred live incident UI. No Phase 8 grouping, Phase 9 API/dashboard, or investigations were implemented.

Run the worker in a separate terminal from `backend`: `.\.venv\Scripts\python.exe -m app.detector_worker`. Restart it after reboot; it is not an installed startup service. The Incidents screen now reads these durable records through the Phase 9 owner-only list.

### Phase 6 — Live event explorer, 2026-10-05

- [x] Added `GET /api/v1/projects/{project_id}/events` and `GET /api/v1/projects/{project_id}/events/{event_id}`. Both require a live owner login cookie; ingestion keys cannot read events. Other-owner/missing projects and missing events return 404, and missing/expired sessions return 401.
- [x] Added combined filters for exact service, level, literal case-insensitive text, and offset-aware received-time bounds. The start is inclusive, the end exclusive; UI inputs and displayed times are explicitly UTC. Invalid filters/cursors return 422.
- [x] Added bounded keyset pagination (default 50, maximum 100), ordered by received time and UUID. Cursors bind project and filters and retain the initial received-time cutoff. Refresh starts again with newer arrivals. List responses omit large stack/metadata fields; details fetch them separately.
- [x] Replaced the Events page's sample table with an owned-project selector, service/level/text/time controls, 25/50/100 page sizes, Next/Previous, refresh, and stored detail dialog. Details include event/request timestamps, event ID, status, latency, exception, stack trace, and metadata.
- [x] Added loading, no-project/no-event, validation, retry, and expired-session handling. Project/filter changes reset pagination; obsolete fetches are aborted and cannot replace current data. Detail dialog supports keyboard focus and Escape; event content is rendered as text.
- [x] Updated preview labels and setup text: only overview charts/recent sample events and incidents remain previews. No detector, incident lifecycle, or live overview API was added.
- [x] Five new API tests verify cross-owner isolation, rejection of ingestion keys, detail scoping, combined/timezone/literal filters, malformed inputs, empty/deleted projects, same-time pagination, and new arrivals between pages. All **43 backend tests passed**.
- [x] Frontend TypeScript/production build passed. Browser verification used 56 real stored synthetic events across two owned projects and checked pagination, combined filters, detail content, safe HTML-like text rendering, Escape, empty results, invalid time range, error/retry, mobile overflow, and expired-session handling. Simulated errors were used only for browser error/expiry states.
- [x] Synthetic browser accounts/projects/events were removed. Existing API was restarted with the new routes. No migration or new dependency was required, and existing ingestion, auth, project, recovery, and demo tests remained green.
- [x] Updated `API.md`, root `README.md`, and `demo-app/README.md` with browsing behavior and setup. To view your data, sign in, open Events, choose a project, and refresh after sending telemetry.

### Phase 5 — Demo service and instrumentation, 2026-10-05

- [x] Added an independent FastAPI demo under `demo-app/`, its dependency list, ignored local environment setup, and detailed run instructions. `POST /payments` only simulates payments; no real payments or dependencies are modified.
- [x] Each application request emits one request event with UUID event/request IDs, UTC timestamp, status, measured latency, route template, and safe exception frames. Responses expose correlation IDs. Exceptions do not create a second request count. Health, documentation, and control requests are excluded.
- [x] Source privacy excludes bodies, headers, query strings, raw request paths, exception messages, stack source lines, and locals. Fault ground truth is recorded by the scenario runner rather than added to telemetry.
- [x] A bounded 128-event queue delivers asynchronously with a one-second attempt timeout, at most three attempts, stable retry IDs, delivery/drop/retry counters, and a five-second shutdown drain. Ingestion failures do not break demo requests. Ordinary 4xx are not retried; long rate-limit waits cause counted drops rather than early retries.
- [x] Implemented `db_timeout` (500), `unhandled_exception` (500), and `slow_dependency` (successful 200 with increased latency), plus `none` for recovery. Controls require explicit configuration, loopback peer/Host checks, and a separate control token. Faults start disabled and reset to healthy on restart.
- [x] Added a scenario runner for healthy traffic before and after each fault, automatic reset, UTC stage boundaries, correlated response IDs, and delivery checks. This is a functional smoke run; Phase 12's detector benchmarks remain deferred.
- [x] Five new tests cover real PostgreSQL ingestion across all faults/recovery, duplicate prevention after a lost acknowledgement, source privacy, control authorization, bounded queues/shutdown, rejected keys, and ingestion outages. Full suite: **38 tests passed**.
- [x] Live run against the existing API persisted exactly **14 events**: four failures and ten healthy/slow successes, with **zero dropped events**. All response event IDs matched stored rows; fault state returned to `none`. The temporary demo process and synthetic account/project/events were cleaned up.
- [x] Existing API/database health and frontend HTTP 200 verified. Existing frontend/backend implementation and Docker Compose were preserved; no Phase 6 event-read endpoint, live explorer, detector, or investigator was added.

To run the demo yourself, follow `demo-app/README.md`: create a dedicated project in Projects & Keys, put its one-time ingestion key in `demo-app/.env`, configure a separate control token, and start the demo on loopback port 8001. Run `run_scenarios.py` from that directory. The verification key was discarded during cleanup; no real user key was stored or changed. The demo queue is best-effort and non-durable, and its controls require a single local worker with proxy-header handling disabled.

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
- [x] Configure SMTP credentials in the root `.env`, restart the backend, and verify delivery and reset through a real inbox. The user has no domain; Gmail SMTP is documented as the development option.

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

Use the API documentation at `http://127.0.0.1:8000/docs`: authorize with a project ingestion key, then submit the example in `API.md` to `POST /api/v1/events`. Do not use a browser session token. The response confirms storage only, not incident detection. At the Phase 4 checkpoint, no batching, demo service, live event-reading endpoint, detector, or investigator was added. Demo instrumentation and event browsing were subsequently implemented in Phases 5 and 6.

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

- Latest full suite: **51 tests passed** (11 authentication, six password recovery, ten project, six event-ingestion, five demo-service, five event-reading, and eight detector tests). Earlier counts below describe historical checkpoints.
- Phase 5 live smoke persisted all 14 expected events with no drops, verified fault recovery, and removed only its synthetic test records. Existing frontend returned HTTP 200; backend reported `storage: connected`.
- Latest frontend production build and password-recovery browser checks passed; migration `0005_password_resets` was applied and API health reported `storage: connected`.
- Real Google sign-in is user-confirmed. SMTP credentials are configured, and the existing password-recovery checklist records real inbox/reset verification as complete. Delivery was not independently re-tested during this documentation review.
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
- Live Google authorization opens Google's sign-in page displaying “to continue to Tracely.” The user subsequently confirmed real-account sign-in succeeds after the five-second clock-tolerance fix. Separate manual confirmation of same-email password linking and Google-session refresh/sign-out remains pending.
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
- This replaces the original API specification's browser bearer-token proposal with the agreed HTTP-only cookie session. Endpoints: `/api/v1/auth/register`, `/login`, `/logout`, `/me`, `/config`, `/google/start`, `/google/callback`, `/google/link`, `/forgot-password`, `/reset-password`. Mutation requests require a trusted `Origin`; frontend requests include cookies.

## Password-reset email configuration

Password recovery is implemented and local SMTP settings are configured. Real inbox/reset verification is marked complete in the existing checklist. For a fresh local setup without a domain, add `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_SECURITY=starttls`, `SMTP_USERNAME`, `SMTP_FROM`, and `SMTP_PASSWORD` to the root `.env`. Use the same Gmail address for username/from and a Google App Password (requires 2-Step Verification), not the Gmail account password or Google OAuth secret. Keep credentials out of source control and chat. Setup instructions are in `README.md`.

Restart the backend after configuring delivery. Then request a link for a password account, check the inbox, open the link on the computer running Tracely, reset the password, and verify that the old password/session fails while the new password succeeds. Until configured, the UI displays a clear email-setup error. Automated tests use mocked delivery and do not establish real inbox delivery.

Run auth tests from `backend` with `.\.venv\Scripts\python.exe -m pytest tests -q`. Tests create and remove uniquely named schemas in the configured database, preserving real accounts.

## Phase tracker (including Phase 9.5)

| Phase | Status | Remaining work |
|---|---|---|
| 1. Local setup | Complete | None; PostgreSQL starts and API connection works |
| 2. Database & accounts | Implemented; data-model aligned; Google sign-in user-confirmed; password recovery added; 17 auth/recovery tests passed | Finish any outstanding specific Google linking and refresh/sign-out manual checks; SMTP/inbox setup is recorded complete |
| 3. Projects & keys | Complete; backend and browser checks passed | None; event ingestion remains Phase 4 |
| 4. Event ingestion | Complete; schema and validated idempotent endpoint | None; demo instrumentation and live explorer remain later phases |
| 5. Demo service | Complete; five demo tests and live ingestion smoke passed | Configure a dedicated local demo key/control token to run it yourself; instructions in `demo-app/README.md` |
| 6. Log explorer | Complete; owner-protected list/details, filters, pagination, browser checks | None; detection and live overview/incident views remain later phases |
| 7. Incident detector | Complete; persistent worker and incident lifecycle tested | Keep the worker running; Phase 9 now displays stored incidents |
| 8. Exception grouping | Complete; fingerprints, historical backfill, owner-only incident details implemented | None |
| 9. Incident dashboard | Complete; owner-scoped overview, filters, pagination, clickable evidence implemented | None |
| 9.5. Guided demo & debugging brief | Implemented locally | Production deployment pending |
| 10. Evidence investigation | Implemented locally | Production deployment and browser smoke verification pending |
| 11. Optional local AI | Not started | Model validation and fallback |
| 12. Evaluation | Not started | Controlled scenarios, integration tests, metrics |
| 13. Docker delivery | Not started (database foundation ready) | App containers, startup migrations, complete demo delivery |
| 14. Documentation & handoff | Partial | Final instructions, benchmarks, deployment decision |

## Limitations

- Deterministic investigation is implemented locally (Phase 10); optional model drafting remains Phase 11.
- Dashboard refresh is manual; automatic polling is not implemented.
- The detector requires a running worker. When it stops, incident status and detector state remain unchanged; check evaluation timestamps for freshness.
- Email verification for password registrations is not implemented.
- Reset email delivery uses an in-process background task without a durable queue; pending delivery can be lost if the process stops.
- Attempt throttling is in memory and resets on restart. Shared, persistent enforcement is needed before scaling.
- Expired session/OAuth records are pruned during new session/flow creation; there is no scheduled cleanup.
- Backend dependencies use version ranges; a full dependency lockfile remains future work.

The public landing-page demo is intentionally synthetic; authenticated charts use stored request events. Fonts have local fallbacks. These are current design choices rather than unfinished features.
