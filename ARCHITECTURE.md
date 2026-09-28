# Architecture and decisions

## Flow

1. Demo application emits one event per completed request, including failures. A small bounded client queue and timeout prevent telemetry from breaking the application.
2. `POST /api/v1/events` verifies a hashed project key, validates and caps fields, stamps `received_at`, and persists the event. The response confirms persistence, not incident processing.
3. A periodic worker aggregates recent events by project and service, groups normalized exceptions, and opens/updates/resolves incidents. A single worker is sufficient locally.
4. The investigation service retrieves the incident's bounded, project-scoped evidence. An optional local LLM drafts a hypothesis in a validated schema. A deterministic summary remains available if no model runs.
5. Browser sessions access project data through owner authorization. The dashboard polls overview and incident endpoints every 10–15 seconds; real-time sockets are deferred.

## Detector v1

Use `received_at` for rolling windows so late client clocks cannot alter detection. Every 30 seconds inspect the last 5 minutes for each active `(project_id, service)`. Count all request events (`event_type=request`) and failed requests (`status_code >= 500` or `level=ERROR`); avoid counting separate exception events as extra requests. Proposed trigger: at least 20 requests, at least 5 failures, and error rate >= 10% for two consecutive evaluations. Suppress duplicates by an active incident unique key `(project_id, service, incident_type)`; update its counters instead. Resolve after two consecutive healthy windows (< 5% error rate with sufficient traffic); label low-traffic windows `insufficient_data` rather than healthy. Store detector version and thresholds with each incident.

Also group exception events by `(project_id, service, fingerprint)` using normalized exception type plus stable top application stack frame. Strip variable IDs and request paths cautiously; retain raw messages separately. Do not group different exception types merely because their text looks similar.

## Investigation v1

Build evidence from the incident window plus 5 minutes before onset: grouped errors, representative stack traces, request counts, endpoints, and timestamps. Rank with deterministic rules first. Limit retrieved events and stack length; record exact event IDs. The response includes observations, candidate causes, suggested checks, and a `limitations` field. Model output is a hypothesis, not proof. Do not display an arbitrary numerical confidence percentage. There is no Git or deployment correlation in Plan A unless deployment events are explicitly instrumented and evaluated.

## Isolation and safety

Every query filters by authorized `project_id`. Browser session tokens never serve as ingestion keys; ingestion keys never authorize reading. Hash keys with a strong one-way hash, show plaintext once, support rotation/revocation, and avoid keys in logs. Cap event body and metadata size, reject unexpected types, redact obvious secrets at source and ingestion, and keep exception text and metadata out of LLM prompts unless scrubbed. Use local synthetic data first. Define a short retention period and deletion endpoint before onboarding other developers. Keep PostgreSQL and the model private to the Compose network.

## Practical constraints

PostgreSQL is sufficient for the first demo; index `(project_id, received_at DESC)`, `(project_id, service, received_at DESC)`, and incident status. Use migrations, not table creation on every boot. Start with synchronous batched inserts; add a queue only after measuring ingestion delays. An optional `pgvector` migration adds vector storage and project-scoped nearest-neighbor lookup. Semantic search is an enhancement, not a requirement for reliable incident detection.

## Decision record

| Choice | Why | Revisit when |
|---|---|---|
| Modular FastAPI app | One deployable service with clear boundaries | Ingestion and analysis loads diverge |
| Periodic worker | Reproducible local detection | Detection delay exceeds target |
| Polling dashboard | Simpler and testable | Many concurrent users need push updates |
| Rule detector | Auditable baseline | Labeled incidents justify ML comparison |
| Optional local model | Core demo runs for ₹0 API spend | Quality and resource use are measured |
