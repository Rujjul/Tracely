"""Phase 8 owner-only incident evidence, without a dashboard or investigation."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from app.auth import db
from app.projects import current_user
from app.event_reads import owned_project, utc_rows, SUMMARY

router = APIRouter(prefix='/api/v1/projects', tags=['incidents'])


@router.get('/{project_id}/incidents/{incident_id}')
def incident_detail(project_id: UUID, incident_id: UUID,
                    user=Depends(current_user), connection=Depends(db)):
    owned_project(connection, project_id, user)
    incident = connection.execute('SELECT * FROM incidents WHERE project_id=%s AND id=%s',
                                  (project_id, incident_id)).fetchone()
    if not incident:
        raise HTTPException(404, 'Incident not found')
    connection.execute("SET LOCAL statement_timeout='5s'")
    # Correlation is reconstructed from stored service and failure interval. It
    # is not a claim of root cause, nor the detector's latest rolling window.
    where = '''project_id=%s AND service=%s AND received_at>=%s AND received_at<=%s
        AND (event_type='exception' OR (event_type='request' AND (status_code>=500 OR level='ERROR')))'''
    params = (project_id, incident['service'], incident['started_at'], incident['last_seen_at'])
    counts = connection.execute(f'''SELECT count(*) AS total_events,
        count(*) FILTER (WHERE fingerprint IS NULL) AS ungrouped_events,
        count(DISTINCT fingerprint) AS total_groups FROM events WHERE {where}''', params).fetchone()
    groups = connection.execute(f'''SELECT fingerprint, min(exception_type) AS exception_type,
        count(*) AS event_count, min(received_at) AS first_seen_at, max(received_at) AS last_seen_at
        FROM events WHERE {where} AND fingerprint IS NOT NULL GROUP BY fingerprint
        ORDER BY count(*) DESC,fingerprint LIMIT 20''', params).fetchall()
    events = connection.execute(f'''SELECT {SUMMARY},fingerprint FROM events WHERE {where}
        ORDER BY received_at DESC,id DESC LIMIT 50''', params).fetchall()
    return {'incident': incident, 'evidence': {
        **counts, 'groups': groups, 'events': utc_rows(events),
        'events_truncated': counts['total_events'] > len(events),
        'groups_truncated': counts['total_groups'] > len(groups),
        'start_time': incident['started_at'], 'end_time': incident['last_seen_at'],
        'limitations': [
            'Events are correlated by project, service and inclusive received-time range; this does not establish causation.',
            'Evidence counts cover retained events in the failure interval; incident counters describe the latest detector window.',
            'Events without a usable exception type and stack remain ungrouped. Historical events require the fingerprint backfill.',
        ]}}
