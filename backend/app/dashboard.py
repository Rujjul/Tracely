"""Owner-scoped project metrics and paginated incident browsing."""
import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, ValidationError
from app.auth import db
from app.projects import current_user
from app.event_reads import Cursor, owned_project

router = APIRouter(prefix='/api/v1/projects', tags=['dashboard'])


def validate_filters(service, start, end):
    if service and '\x00' in service:
        raise HTTPException(422, 'Invalid service name.')
    if start and end and start >= end:
        raise HTTPException(422, 'Start time must be earlier than end time.')


@router.get('/{project_id}/overview')
def overview(project_id: UUID, start_time: AwareDatetime | None = None,
             end_time: AwareDatetime | None = None,
             service: str | None = Query(None, min_length=1, max_length=255),
             user=Depends(current_user), connection=Depends(db)):
    owned_project(connection, project_id, user)
    end = (end_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = (start_time or end - timedelta(hours=1)).astimezone(timezone.utc)
    validate_filters(service, start, end)
    if end-start > timedelta(days=7):
        raise HTTPException(422, 'Overview windows cannot exceed seven days.')
    connection.execute("SET LOCAL statement_timeout='5s'")
    # One statement keeps cards, buckets and service totals on one DB snapshot.
    result = connection.execute('''WITH bounds AS (
        SELECT %s::uuid AS project,%s::timestamptz AS start,%s::timestamptz AS finish,%s::text AS service
    ), filtered AS MATERIALIZED (
        SELECT e.*, (event_type='request') AS request,
            (event_type='request' AND (status_code>=500 OR level='ERROR')) AS failed
        FROM events e,bounds b WHERE project_id=b.project AND received_at>=b.start AND received_at<b.finish
            AND (b.service IS NULL OR e.service=b.service)
    ), service_counts AS (
        SELECT service,count(*) AS events,count(*) FILTER(WHERE request) AS requests,
            count(*) FILTER(WHERE failed) AS failures FROM filtered GROUP BY service
    ), bucket_counts AS (
        SELECT floor(extract(epoch FROM (received_at-b.start)) /
            (extract(epoch FROM (b.finish-b.start))/24))::int AS bucket,
            count(*) FILTER(WHERE request) AS requests,count(*) FILTER(WHERE failed) AS failures
        FROM filtered,bounds b GROUP BY bucket
    ), services AS (
        SELECT c.*, d.last_evaluated_at,d.evaluation_status,
            EXISTS(SELECT 1 FROM incidents i,bounds b WHERE i.project_id=b.project
                AND i.service=c.service AND i.status='active') AS active_incident
        FROM service_counts c CROSS JOIN bounds b LEFT JOIN detector_states d
            ON d.project_id=b.project AND d.service=c.service
        ORDER BY c.requests DESC,c.service LIMIT 100
    ) SELECT count(*) AS total_events,count(*) FILTER(WHERE request) AS requests,
        count(*) FILTER(WHERE failed) AS failures,
        percentile_cont(0.5) WITHIN GROUP(ORDER BY latency_ms) FILTER(WHERE request AND latency_ms IS NOT NULL) AS median_latency_ms,
        (SELECT count(*) FROM incidents i,bounds b WHERE i.project_id=b.project
            AND i.status='active' AND (b.service IS NULL OR i.service=b.service)) AS active_incidents,
        (SELECT count(*) FROM service_counts) AS total_services,
        COALESCE((SELECT jsonb_agg(to_jsonb(services)) FROM services),'[]'::jsonb) AS services,
        COALESCE((SELECT jsonb_agg(to_jsonb(bucket_counts)) FROM bucket_counts),'[]'::jsonb) AS buckets
        FROM filtered''', (project_id,start,end,service)).fetchone()
    present = {bucket['bucket']: bucket for bucket in result['buckets']}
    result['buckets'] = [{'start_time': start + (end-start)*index/24,
                          'end_time': start + (end-start)*(index+1)/24,
                          'requests': present.get(index, {}).get('requests', 0),
                          'failures': present.get(index, {}).get('failures', 0)} for index in range(24)]
    result['error_rate'] = result['failures']/result['requests'] if result['requests'] else None
    result['services_truncated'] = result['total_services'] > len(result['services'])
    return {**result, 'start_time': start, 'end_time': end, 'generated_at': datetime.now(timezone.utc)}


@router.get('/{project_id}/incidents')
def list_incidents(project_id: UUID, status: Literal['active','resolved'] | None = None,
                   service: str | None = Query(None, min_length=1, max_length=255),
                   start_time: AwareDatetime | None = None, end_time: AwareDatetime | None = None,
                   limit: int = Query(50, ge=1, le=100), cursor: str | None = Query(None, max_length=2048),
                   user=Depends(current_user), connection=Depends(db)):
    owned_project(connection, project_id, user)
    validate_filters(service, start_time, end_time)
    filters = hashlib.sha256(json.dumps(['incidents',status,service,
        start_time.astimezone(timezone.utc).isoformat() if start_time else None,
        end_time.astimezone(timezone.utc).isoformat() if end_time else None]).encode()).hexdigest()
    snapshot = datetime.now(timezone.utc)
    where, params = ['project_id=%s'], [project_id]
    if cursor:
        try:
            page = Cursor.model_validate_json(base64.b64decode(cursor.encode(), altchars=b'-_', validate=True))
            if page.project != project_id or page.filters != filters or page.before > page.snapshot:
                raise ValueError()
        except (ValueError, ValidationError, UnicodeError):
            raise HTTPException(422, 'Invalid cursor. Refresh or keep the same filters.') from None
        snapshot = page.snapshot
        where.append('(started_at,id)<(%s,%s)')
        params.extend([page.before,page.id])
    where.append('started_at<=%s')
    params.append(snapshot)
    for value, clause in ((status,'status=%s'),(service,'service=%s'),
                          (start_time,'started_at>=%s'),(end_time,'started_at<%s')):
        if value is not None:
            where.append(clause); params.append(value)
    connection.execute("SET LOCAL statement_timeout='5s'")
    rows = connection.execute(f'''SELECT id,service,incident_type,status,severity,started_at,last_seen_at,
        resolved_at,failure_count,request_count FROM incidents WHERE {' AND '.join(where)}
        ORDER BY started_at DESC,id DESC LIMIT %s''', (*params,limit+1)).fetchall()
    more, rows = len(rows)>limit, rows[:limit]
    next_cursor = None
    if more:
        last = rows[-1]
        page = Cursor(version=1,project=project_id,filters=filters,before=last['started_at'],id=last['id'],snapshot=snapshot)
        next_cursor = base64.urlsafe_b64encode(page.model_dump_json().encode()).decode()
    return {'incidents': rows, 'next_cursor': next_cursor}
