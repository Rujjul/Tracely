"""Bounded deterministic evidence; telemetry is data, never instructions."""
from collections import defaultdict
from datetime import timedelta
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from app.auth import db, same_origin
from app.projects import current_user
from app.event_reads import owned_project
from app.events import scrub

router = APIRouter(prefix='/api/v1/projects', tags=['investigations'])
MAX_EVENTS = 200
MAX_GROUPS = 10
STACK_LIMIT = 1000


def clean(value, limit=240):
    text = scrub(value or '')
    text = re.sub(r'(?i)\b[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@', '[REDACTED URL]@', text)
    text = re.sub(r'\bGOCSPX-[A-Za-z0-9_-]+', '[REDACTED]', text)
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', text)
    return text[:limit]


def failed(event):
    return event['event_type'] == 'request' and ((event['status_code'] or 0) >= 500 or event['level'] == 'ERROR')


def draft(events, start, end, truncated, window_capped):
    observations, hypotheses = [], []
    limitations = [
        f'Received-time evidence window: {start.isoformat()} through {end.isoformat()} (inclusive).',
        'Rules v1: correlation is not proof of root cause; no model, source code, deployments or dependency metrics were inspected.',
        'Counts describe the selected sample, not the detector window or the full incident. Exception-only events are not requests.',
        'At most 200 events, ranked failures/exceptions first then newest; this sample is not an unbiased error-rate estimate.',
        'Citations refer to retained event IDs; future event deletion can make them unavailable. Historical versions are snapshots.',
        'Representative text is scrubbed and clipped; metadata is excluded. Missing evidence cannot prove health.',
    ]
    if truncated:
        limitations.append('Event limit reached: additional matching events were omitted.')
    if window_capped:
        limitations.append('The 24-hour retrieval cap omitted older evidence, including some or all of the five-minute pre-onset context.')
    requests = [e for e in events if e['event_type'] == 'request']
    failures = [e for e in requests if failed(e)]
    if requests:
        observations.append({'text': f'Selected sample contains {len(requests)} request events, including {len(failures)} failures.',
                             'event_ids': [str(e['event_id']) for e in requests]})
    groups = defaultdict(list)
    for event in events:
        if event['event_type'] == 'exception' or failed(event):
            groups[event['fingerprint'] or 'ungrouped'].append(event)
    ordered = sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    for fingerprint, members in ordered[:MAX_GROUPS]:
        representative = members[0]
        ids = [str(e['event_id']) for e in members]
        name = clean(representative['exception_type']) if fingerprint != 'ungrouped' else 'Ungrouped failures/exceptions'
        observations.append({'text': f'{name or "Exception group"}: {len(members)} events in the selected sample.',
            'event_ids': ids, 'representative': {
                'event_id': ids[0], 'received_at': representative['received_at'].isoformat(),
                'endpoint': clean(representative['endpoint']), 'message': clean(representative['message'], 400),
                'stack_trace': clean(representative['stack_trace'], STACK_LIMIT)}})
        timeout_ids = [str(e['event_id']) for e in members if 'timeout' in (e['exception_type'] or '').lower()]
        if timeout_ids:
            hypotheses.append({'cause': 'A timed-out operation may contribute to this incident; the dependency and underlying cause are unverified.',
                               'supporting_event_ids': timeout_ids})
    if len(ordered) > MAX_GROUPS:
        limitations.append('Only the 10 largest exception/failure groups in the sample are shown.')
    if groups and not hypotheses:
        hypotheses.append({'cause': 'An application or dependency failure may explain these errors; inspect the cited requests and stack frames to distinguish causes.',
                           'supporting_event_ids': [str(e['event_id']) for e in events if failed(e) or e['event_type'] == 'exception']})
    if not events:
        limitations.append('No retained evidence exists in this window; a cause cannot be inferred.')
    elif not groups:
        limitations.append('No failed request or exception was found in the selected evidence; no cause is proposed.')
    if not any(e['stack_trace'] for e in events):
        limitations.append('No stack traces were available in the sample.')
    checks = ['Inspect cited event details and matching application code; distinguish observations from hypotheses.',
              'Compare dependency health, timeout settings and deployment history from your own records.',
              'Reproduce safely, test the smallest proposed fix, and verify recovery with fresh telemetry.'] if events else [
              'Check ingestion, service naming, event retention and detector timestamps before investigating again.']
    return dict(method='rules', summary=f'Rule-based review of {len(events)} sampled events: {len(failures)} failed requests. Root cause is not established.',
                observations=observations, hypotheses=hypotheses, suggested_checks=checks, limitations=limitations)


def authorized_incident(connection, project_id, incident_id, user, lock=False):
    owned_project(connection, project_id, user)
    row = connection.execute('SELECT * FROM incidents WHERE project_id=%s AND id=%s' + (' FOR UPDATE' if lock else ''),
                             (project_id, incident_id)).fetchone()
    if not row:
        raise HTTPException(404, 'Incident not found')
    return row


@router.get('/{project_id}/incidents/{incident_id}/investigation')
def latest(project_id: UUID, incident_id: UUID, user=Depends(current_user), connection=Depends(db)):
    authorized_incident(connection, project_id, incident_id, user)
    row = connection.execute('SELECT * FROM investigations WHERE incident_id=%s ORDER BY created_at DESC,id DESC LIMIT 1',
                             (incident_id,)).fetchone()
    return {'investigation': {**row, 'status': 'complete'} if row else None}


@router.post('/{project_id}/incidents/{incident_id}/investigate', dependencies=[Depends(same_origin)])
def investigate(project_id: UUID, incident_id: UUID, user=Depends(current_user), connection=Depends(db)):
    connection.execute("SET LOCAL statement_timeout='5s'")
    incident = authorized_incident(connection, project_id, incident_id, user, lock=True)
    end = incident['resolved_at'] or incident['last_seen_at']
    original_start = incident['started_at'] - timedelta(minutes=5)
    start = max(original_start, end - timedelta(hours=24))
    # One bounded read fixes the evidence set for every observation and citation.
    events = connection.execute('''SELECT event_id,received_at,event_type,level,status_code,
        left(message,2048) AS message,left(endpoint,2048) AS endpoint,
        left(exception_type,2048) AS exception_type,left(stack_trace,8192) AS stack_trace,fingerprint
        FROM events WHERE project_id=%s AND service=%s AND received_at>=%s AND received_at<=%s
        ORDER BY (event_type='exception' OR (event_type='request' AND (status_code>=500 OR level='ERROR'))) DESC NULLS LAST,
        received_at DESC,id DESC LIMIT %s''', (project_id, incident['service'], start, end, MAX_EVENTS + 1)).fetchall()
    result = draft(events[:MAX_EVENTS], start, end, len(events) > MAX_EVENTS, start != original_start)
    row = connection.execute('''INSERT INTO investigations
        (id,incident_id,method,summary,observations,hypotheses,suggested_checks,limitations)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
        (uuid4(), incident_id, result['method'], result['summary'],
         *[Jsonb(result[key]) for key in ('observations','hypotheses','suggested_checks','limitations')])).fetchone()
    connection.commit()
    return {**row, 'status': 'complete'}
