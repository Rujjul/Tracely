"""Bounded, project-key-authenticated, idempotent event ingestion."""
import json
import re
import time
from collections import defaultdict, deque
from datetime import timezone
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, ValidationError, field_validator
from psycopg.types.json import Jsonb
from app.auth import db, digest

router = APIRouter(prefix='/api/v1/events', tags=['events'])
bearer = HTTPBearer(auto_error=False, scheme_name='Project ingestion key')
MAX_BODY = 64 * 1024
RATE_LIMIT = 600
WINDOW = 60
attempts = defaultdict(deque)
rate_lock = Lock()


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    event_id: UUID
    timestamp: AwareDatetime
    event_type: Literal['request', 'exception']
    level: Literal['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL', 'FATAL']
    service: str = Field(min_length=1, max_length=255)
    message: str
    endpoint: str | None = None
    status_code: int | None = Field(default=None, ge=0, le=599)
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    exception_type: str | None = None
    stack_trace: str | None = None
    metadata: dict[str, JsonValue] | None = None

    @field_validator('service')
    @classmethod
    def service_name(cls, value):
        if not value.strip():
            raise ValueError('Service must not be blank')
        return value

    @field_validator('message', 'stack_trace', 'endpoint', 'exception_type')
    @classmethod
    def text_size(cls, value, info):
        limit = 8192 if info.field_name == 'stack_trace' else 2048
        if value is not None and len(value.encode('utf-8')) > limit:
            raise HTTPException(413, f'{info.field_name} exceeds {limit} UTF-8 bytes')
        return value

    @field_validator('metadata')
    @classmethod
    def metadata_size(cls, value):
        if value is not None and len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 4096:
            raise HTTPException(413, 'metadata exceeds 4096 UTF-8 bytes')
        return value


async def event_body(request: Request):
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise HTTPException(415, 'Use application/json')
    if request.headers.get('content-encoding', 'identity').lower() != 'identity':
        raise HTTPException(415, 'Compressed event bodies are not supported')
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            raise HTTPException(413, 'Event body exceeds 64 KiB')
        body.extend(chunk)
    try:
        event = Event.model_validate_json(bytes(body))
        # PostgreSQL text/JSONB cannot represent NUL or invalid Unicode.
        normalized = event.model_dump_json()
        if '\\u0000' in normalized:
            raise ValueError('NUL characters are not supported')
        normalized.encode('utf-8')
        return event
    except (ValidationError, ValueError, RecursionError):
        raise HTTPException(422, 'Invalid event. Check field types, timestamp timezone, and required fields.') from None


def active_project(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), connection=Depends(db)):
    if not credentials or not re.fullmatch(r'trc_[A-Za-z0-9_-]{43}', credentials.credentials):
        raise HTTPException(401, 'Invalid ingestion key', headers={'WWW-Authenticate': 'Bearer'})
    key_hash = digest(credentials.credentials)
    key = connection.execute('SELECT project_id FROM project_keys WHERE key_hash=%s AND revoked_at IS NULL', (key_hash,)).fetchone()
    if not key:
        raise HTTPException(401, 'Invalid ingestion key')
    # Follow the same project-before-key lock order as rotation/deletion.
    project = connection.execute('SELECT id FROM projects WHERE id=%s FOR SHARE', (key['project_id'],)).fetchone()
    current = connection.execute('SELECT id FROM project_keys WHERE key_hash=%s AND revoked_at IS NULL FOR SHARE', (key_hash,)).fetchone()
    if not project or not current:
        raise HTTPException(401, 'Invalid ingestion key')
    stamp = time.monotonic()
    with rate_lock:
        for stale in list(attempts):
            if not attempts[stale] or attempts[stale][-1] <= stamp - WINDOW:
                del attempts[stale]
        bucket = attempts[key_hash]
        while bucket and bucket[0] <= stamp - WINDOW:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT:
            raise HTTPException(429, 'Ingestion rate limit exceeded', headers={'Retry-After': str(max(1, int(WINDOW - (stamp-bucket[0])) + 1))})
        bucket.append(stamp)
    return key['project_id']


SECRET_NAME = re.compile(r'(?i)(password|passwd|secret|token|authorization|cookie|api[_-]?key)')
SECRET_TEXT = re.compile(r'(?i)(\b(?:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*)([^\s,;]+)')
BEARER_TEXT = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*')
PROJECT_KEY = re.compile(r'\btrc_[A-Za-z0-9_-]{43}\b')


def scrub(value):
    if isinstance(value, dict):
        return {scrub(key): '[REDACTED]' if SECRET_NAME.search(key) else scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, str):
        value = PROJECT_KEY.sub('[REDACTED]', value)
        value = BEARER_TEXT.sub('Bearer [REDACTED]', value)
        return SECRET_TEXT.sub(r'\1[REDACTED]', value)
    return value


event_schema = Event.model_json_schema()
# Metadata is arbitrary JSON. Avoid embedding recursive local $defs references
# that would point at the wrong root inside the OpenAPI document.
event_schema.pop('$defs', None)
event_schema['properties']['metadata'] = {'anyOf': [{'type': 'object', 'additionalProperties': True}, {'type': 'null'}]}


@router.post('', status_code=201, openapi_extra={'requestBody': {'required': True, 'content': {'application/json': {'schema': event_schema}}}})
def ingest(response: Response, project_id=Depends(active_project), event: Event = Depends(event_body), connection=Depends(db)):
    data = event.model_dump()
    row = connection.execute('''INSERT INTO events
        (id,project_id,event_id,timestamp,event_type,level,service,message,endpoint,status_code,latency_ms,exception_type,stack_trace,metadata)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (project_id,event_id) DO NOTHING RETURNING event_id''',
        (uuid4(), project_id, event.event_id, event.timestamp.astimezone(timezone.utc), event.event_type,
         event.level, scrub(event.service), scrub(event.message), scrub(event.endpoint), event.status_code,
         event.latency_ms, scrub(event.exception_type), scrub(event.stack_trace),
         Jsonb(scrub(data['metadata'])) if data['metadata'] is not None else None)).fetchone()
    connection.commit()  # Acknowledge persistence, never just receipt.
    response.status_code = 201 if row else 200
    return {'status': 'stored', 'event_id': str(event.event_id)}
