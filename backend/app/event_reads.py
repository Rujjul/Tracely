"""Owner-only event browsing with bounded, stable keyset pagination."""
import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError

from app.auth import db
from app.projects import current_user

router = APIRouter(prefix='/api/v1/projects', tags=['events'])
Level = Literal['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL', 'FATAL']
SUMMARY = 'id,event_id,timestamp,received_at,event_type,level,service,message,endpoint,status_code,latency_ms,exception_type'


class Cursor(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: Literal[1]
    project: UUID
    filters: str
    before: AwareDatetime
    id: UUID
    snapshot: AwareDatetime


def owned_project(connection, project_id, user):
    if not connection.execute('SELECT id FROM projects WHERE id=%s AND owner_id=%s', (project_id, user['id'])).fetchone():
        raise HTTPException(404, 'Project not found')


def utc_rows(rows):
    for row in rows:
        for field in ('timestamp', 'received_at'):
            row[field] = row[field].astimezone(timezone.utc)
    return rows


@router.get('/{project_id}/events')
def list_events(project_id: UUID, limit: int = Query(50, ge=1, le=100),
                cursor: str | None = Query(None, max_length=2048),
                service: str | None = Query(None, min_length=1, max_length=255),
                level: Level | None = None,
                q: str | None = Query(None, max_length=200),
                start_time: AwareDatetime | None = None, end_time: AwareDatetime | None = None,
                user=Depends(current_user), connection=Depends(db)):
    owned_project(connection, project_id, user)
    if start_time and end_time and start_time >= end_time:
        raise HTTPException(422, 'Start time must be earlier than end time.')
    q = (q or '').strip()
    if '\x00' in q or (service and '\x00' in service):
        raise HTTPException(422, 'Filters contain invalid characters.')
    filters = hashlib.sha256(json.dumps([service, level, q,
        start_time.astimezone(timezone.utc).isoformat() if start_time else None,
        end_time.astimezone(timezone.utc).isoformat() if end_time else None]).encode()).hexdigest()
    snapshot = datetime.now(timezone.utc)
    where, params = ['project_id=%s'], [project_id]
    if cursor:
        try:
            decoded = base64.b64decode(cursor.encode(), altchars=b'-_', validate=True)
            page = Cursor.model_validate_json(decoded)
            if page.project != project_id or page.filters != filters or page.before > page.snapshot:
                raise ValueError()
        except (ValueError, ValidationError, UnicodeError):
            raise HTTPException(422, 'Invalid cursor. Refresh results or keep the same filters.') from None
        snapshot = page.snapshot
        where.append('(received_at,id)<(%s,%s)')
        params.extend([page.before, page.id])
    where.append('received_at<=%s')
    params.append(snapshot)
    for value, condition in ((service, 'service=%s'), (level, 'level=%s'),
                             (start_time, 'received_at>=%s'), (end_time, 'received_at<%s')):
        if value is not None:
            where.append(condition)
            params.append(value)
    if q:
        # Literal substring search: percent/underscore are not user wildcards.
        pattern = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        where.append("(message ILIKE %s OR service ILIKE %s OR endpoint ILIKE %s OR exception_type ILIKE %s)")
        params.extend([pattern] * 4)
    params.append(limit + 1)
    rows = connection.execute(f'SELECT {SUMMARY} FROM events WHERE {" AND ".join(where)} ORDER BY received_at DESC,id DESC LIMIT %s', params).fetchall()
    more, rows = len(rows) > limit, rows[:limit]
    next_cursor = None
    if more:
        last = rows[-1]
        page = Cursor(version=1, project=project_id, filters=filters, before=last['received_at'], id=last['id'], snapshot=snapshot)
        next_cursor = base64.urlsafe_b64encode(page.model_dump_json().encode()).decode()
    return {'events': utc_rows(rows), 'next_cursor': next_cursor}


@router.get('/{project_id}/events/{event_id}')
def event_detail(project_id: UUID, event_id: UUID, user=Depends(current_user), connection=Depends(db)):
    owned_project(connection, project_id, user)
    row = connection.execute(f'SELECT {SUMMARY},stack_trace,metadata,fingerprint FROM events WHERE project_id=%s AND event_id=%s', (project_id, event_id)).fetchone()
    if not row:
        raise HTTPException(404, 'Event not found')
    return {'event': utc_rows([row])[0]}
