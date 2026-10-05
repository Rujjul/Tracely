"""Local-only synthetic payment service; no real payments or dependencies."""
import asyncio
import ipaddress
import os
import re
import secrets
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from demo.telemetry import Telemetry


def utc():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Settings:
    url: str
    key: str = field(repr=False)
    faults_enabled: bool = False
    control_token: str = field(default='', repr=False)

    def __post_init__(self):
        target = urlsplit(self.url)
        local = target.hostname in ('localhost', '127.0.0.1', '::1')
        if target.scheme not in ('http', 'https') or not target.hostname or target.username or target.password or target.query or target.fragment:
            raise ValueError('Use an HTTP(S) ingestion URL without credentials, query, or fragment.')
        if target.scheme == 'http' and not local:
            raise ValueError('Remote ingestion requires HTTPS.')
        if not re.fullmatch(r'trc_[A-Za-z0-9_-]{43}', self.key):
            raise ValueError('Set TRACELY_INGESTION_KEY to a project ingestion key.')
        if self.faults_enabled and (len(self.control_token) < 32 or secrets.compare_digest(self.control_token, self.key)):
            raise ValueError('Enabled faults require a separate DEMO_CONTROL_TOKEN of at least 32 characters.')

    @classmethod
    def from_env(cls):
        return cls(os.getenv('TRACELY_INGEST_URL', 'http://127.0.0.1:8000/api/v1/events'),
                   os.getenv('TRACELY_INGESTION_KEY', ''),
                   os.getenv('DEMO_FAULTS_ENABLED', 'false').lower() == 'true',
                   os.getenv('DEMO_CONTROL_TOKEN', ''))


class DatabaseTimeout(TimeoutError):
    pass


class Fault(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['none', 'db_timeout', 'unhandled_exception', 'slow_dependency']


class Instrumentation:
    def __init__(self, app, owner):
        self.app, self.owner = app, owner

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] in ('/health', '/docs', '/docs/oauth2-redirect', '/redoc', '/openapi.json') or scope['path'].startswith('/_demo/'):
            return await self.app(scope, receive, send)
        event_id, request_id = str(uuid4()), str(uuid4())
        start, timestamp = time.perf_counter(), utc()
        status, started, exception = 500, False, None

        async def capture(message):
            nonlocal status, started
            if message['type'] == 'http.response.start':
                status, started = message['status'], True
                message = {**message, 'headers': [*message.get('headers', []),
                    (b'x-request-id', request_id.encode()), (b'x-tracely-event-id', event_id.encode())]}
            await send(message)
        try:
            await self.app(scope, receive, capture)
        except Exception as error:
            exception = error
            if not started:
                await JSONResponse({'detail': 'Synthetic demo request failed', 'request_id': request_id}, status_code=500)(scope, receive, capture)
            else:
                raise
        finally:
            route = scope.get('route')
            # Never collect bodies, headers, query strings, raw paths, exception
            # messages, locals, or source lines: these may contain user secrets.
            stack = None
            if exception:
                frames = traceback.extract_tb(exception.__traceback__)
                stack = '\n'.join(f'{os.path.basename(f.filename)}:{f.lineno} in {f.name}' for f in frames[-12:])[:2048]
            self.owner.state.telemetry.emit({
                'event_id': event_id, 'timestamp': timestamp, 'event_type': 'request',
                'level': 'ERROR' if status >= 500 or exception else 'INFO',
                'service': 'payment-api', 'message': 'Request failed' if exception or status >= 500 else 'Request completed',
                'endpoint': route.path if route else '/unmatched', 'status_code': status,
                'latency_ms': round((time.perf_counter() - start) * 1000, 3),
                'exception_type': type(exception).__name__ if exception else None,
                'stack_trace': stack, 'metadata': {'request_id': request_id, 'environment': 'demo', 'method': scope['method']},
            })


def create_app(settings=None, *, transport=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.settings = settings or Settings.from_env()
        configured = app.state.settings
        app.state.telemetry = Telemetry(configured.url, configured.key, transport=transport)
        app.state.fault = 'none'
        app.state.changed_at = utc()
        app.state.telemetry.start()
        try:
            yield
        finally:
            await app.state.telemetry.close()

    app = FastAPI(title='Tracely synthetic demo', lifespan=lifespan)
    app.add_middleware(Instrumentation, owner=app)

    def control(request: Request):
        configured = app.state.settings
        if not configured.faults_enabled:
            raise HTTPException(404, 'Demo controls are disabled')
        try:
            local_peer = ipaddress.ip_address(request.client.host).is_loopback
        except (ValueError, AttributeError):
            local_peer = False
        if not local_peer or request.url.hostname not in ('127.0.0.1', 'localhost', '::1'):
            raise HTTPException(403, 'Demo controls require loopback access')
        if not secrets.compare_digest(request.headers.get('x-demo-control-token', ''), configured.control_token):
            raise HTTPException(403, 'Invalid demo control token')

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'service': 'payment-api', 'environment': 'demo', 'telemetry': app.state.telemetry.stats()}

    @app.get('/_demo/fault', dependencies=[Depends(control)])
    async def current_fault():
        return {'mode': app.state.fault, 'changed_at': app.state.changed_at}

    @app.post('/_demo/fault', dependencies=[Depends(control)])
    async def set_fault(body: Fault):
        app.state.fault, app.state.changed_at = body.mode, utc()
        return await current_fault()

    @app.post('/payments')
    async def payment():
        mode = app.state.fault
        if mode == 'db_timeout':
            await asyncio.sleep(0.1)
            raise DatabaseTimeout('Synthetic database timeout')
        if mode == 'unhandled_exception':
            raise RuntimeError('Synthetic payment exception')
        await asyncio.sleep(0.25 if mode == 'slow_dependency' else 0.005)
        return {'status': 'accepted', 'synthetic': True}

    return app


app = create_app()
