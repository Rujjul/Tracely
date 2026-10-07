# Phase 8: exception grouping and incident details

Newly ingested events with an exception type and nonempty stack receive a server-computed `exc-v1:<sha256>` fingerprint. The hash uses the trimmed, case-sensitive exception type plus the innermost application frame. Group identity is **project + service + fingerprint**; the hash alone is not an authorization boundary. Both request events carrying exceptions and exception-only events can be grouped. This does not change the request-failure detector or its denominator.

Python tracebacks and the demo's `file.py:line in function` format are supported, along with single `file.py:line` locations. Frame line/column numbers are ignored; path separators and UUID path segments are normalized. File directories and function names remain significant. Known Python dependency paths are skipped when an application frame exists. Different exception types or application locations stay separate. Messages, endpoint paths, request IDs, and metadata are not fingerprint inputs. Stored scrubbed evidence is preserved.

If no frame is recognized, the complete whitespace-normalized stack is hashed conservatively; unknown languages can therefore split equivalent failures. Missing exception type or stack leaves the event ungrouped. Absolute deployment roots remain significant to avoid accidentally merging equal basenames; consistent source paths are recommended. Grouping is deterministic, not a root-cause claim.

## Existing data and upgrades

From `backend`, run:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.backfill_fingerprints
```

Migration `0007_exception_groups` adds a project/service/fingerprint/time index; the nullable fingerprint column already exists. The explicit backfill commits batches of 500, updates only null fingerprints, can be rerun safely, and prints only an updated-row count. It does not change event messages, timestamps, stack traces, or existing nonnull fingerprints. Run it again if historical writers inserted null fingerprints concurrently. New ingestion writes the fingerprint atomically with the event; idempotent replays preserve the original.

Restart FastAPI after updating the code. The detector worker has no Phase 8 logic changes.

## Inspect an incident

The Incidents page now has a **Stored incident details** lookup: select an owned project and enter the incident UUID. Use an ID from your existing detector/database verification. The owner-only API is `GET /api/v1/projects/{project_id}/incidents/{incident_id}`. The browsable incident list and overview remain Phase 9; their existing illustrations are still labeled sample data.

The detail response includes lifecycle timestamps, status, severity, detector version, recorded policy, and the latest detector counters. Correlated evidence is reconstructed using the same project/service and the inclusive interval from `started_at` to `last_seen_at`, measured by server `received_at`. Only failed requests or exception-only events are evidence candidates. This is an episode interval, not the latest rolling window; its counts may differ from incident counters.

Responses contain the 20 largest exception groups, the latest 50 correlated event summaries, exact retained evidence/group counts, and explicit truncation flags. Event links open the existing owner-only stack/metadata detail dialog, now including fingerprints. Use Events for further browsing. The endpoint bounds query time to five seconds. Retention/deletion can leave an incident with no evidence; it returns an honest empty state. No join table, new detector incident type, automatic investigation, or LLM is added.

Missing/expired sessions return 401; inaccessible projects/incidents return 404; malformed UUIDs return 422. Ingestion keys cannot read incident evidence. Project deletion continues to cascade through incidents and events.

## Checks

`python -m pytest tests/test_phase8.py -q` covers stable fingerprints, different types/modules/functions, dependency frames, unknown/absent stacks, ingestion replay, grouping counts, service isolation, owner authorization, bounded evidence/time intervals, repeatable backfill, and deletion cascades. Full backend tests also retain all detector/auth/ingestion regression checks.
