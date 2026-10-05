"""Phase 5 demo checks, including real ingestion into an isolated PostgreSQL schema."""
import asyncio
import json
import os
from pathlib import Path
import sys
from uuid import UUID

import httpx
import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'demo-app'))
from demo.main import Settings, create_app
from demo.telemetry import Telemetry
from app.main import app as ingestion_app
from test_auth import client, register, ORIGIN

CONTROL = 'local-demo-control-' + 'a' * 32
KEY = 'trc_' + 'a' * 43


def test_demo_faults_persist_one_event_per_request(client):
    register(client)
    project = client.post('/api/v1/projects', headers=ORIGIN, json={'name': 'Phase 5 test'}).json()
    async def run():
        demo = create_app(Settings('https://ingestion/api/v1/events', project['ingestion_key'], True, CONTROL),
                          transport=httpx.ASGITransport(app=ingestion_app))
        recorded = []
        async with demo.router.lifespan_context(demo):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=demo, client=('127.0.0.1', 1234)), base_url='http://127.0.0.1') as web:
                for mode in ('none', 'db_timeout', 'none', 'unhandled_exception', 'none', 'slow_dependency', 'none'):
                    response = await web.post('/_demo/fault', headers={'X-Demo-Control-Token': CONTROL}, json={'mode': mode})
                    assert response.status_code == 200 and response.json()['changed_at']
                    result = await web.post('/payments?password=should-not-be-collected', json={'secret':'private-body'}, headers={'Authorization':'Bearer private-header'})
                    assert result.status_code == (500 if mode in ('db_timeout', 'unhandled_exception') else 200)
                    recorded.append((mode, result.headers['x-tracely-event-id'], result.headers['x-request-id']))
                await asyncio.wait_for(demo.state.telemetry.queue.join(), 10)
                assert demo.state.telemetry.stats()['delivered'] == 7
                assert demo.state.telemetry.stats()['dropped'] == 0
        return recorded
    recorded = asyncio.run(run())
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        rows = conn.execute('SELECT event_id,event_type,status_code,latency_ms,exception_type,stack_trace,metadata,endpoint FROM events WHERE project_id=%s', (project['project']['id'],)).fetchall()
    assert len(rows) == 7
    for mode, event_id, request_id in recorded:
        row = next(row for row in rows if row[0] == UUID(event_id))
        assert row[1] == 'request' and row[6]['request_id'] == request_id and row[7] == '/payments'
        assert row[3] >= 0
        if mode == 'db_timeout': assert row[4] == 'DatabaseTimeout' and row[5]
        elif mode == 'unhandled_exception': assert row[4] == 'RuntimeError' and row[5]
        else: assert row[4] is None and row[2] == 200
        if mode == 'slow_dependency': assert row[3] >= 240
    assert all(secret not in str(rows) for secret in ('should-not-be-collected', 'private-body', 'private-header', CONTROL, project['ingestion_key']))


def test_fault_controls_require_opt_in_loopback_and_separate_token():
    async def run():
        for enabled, host, base, token, expected in [
            (False, '127.0.0.1', '127.0.0.1', CONTROL, 404),
            (True, '192.0.2.1', '127.0.0.1', CONTROL, 403),
            (True, '127.0.0.1', 'evil.example', CONTROL, 403),
            (True, '127.0.0.1', '127.0.0.1', '', 403),
            (True, '127.0.0.1', '127.0.0.1', CONTROL, 200),
        ]:
            demo = create_app(Settings('http://127.0.0.1:8000/api/v1/events', KEY, enabled, CONTROL))
            async with demo.router.lifespan_context(demo):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=demo, client=(host, 1)), base_url=f'http://{base}') as web:
                    result = await web.post('/_demo/fault', headers={'X-Demo-Control-Token':token}, json={'mode':'db_timeout'})
                    assert result.status_code == expected
                    if expected == 200:
                        assert (await web.post('/_demo/fault', headers={'X-Demo-Control-Token':token}, json={'mode':'arbitrary'})).status_code == 422
                    assert demo.state.telemetry.queue.empty()
    asyncio.run(run())
    with pytest.raises(ValueError): Settings('http://remote.example/events', KEY)
    with pytest.raises(ValueError): Settings('http://127.0.0.1/events', KEY, True, 'short')


def test_retry_after_lost_response_reuses_id_and_does_not_duplicate(client):
    register(client)
    project = client.post('/api/v1/projects', headers=ORIGIN, json={'name':'Retry test'}).json()
    async def run():
        inner = httpx.ASGITransport(app=ingestion_app)
        ids = []
        class LostResponse(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                ids.append(json.loads(request.content)['event_id'])
                response = await inner.handle_async_request(request)
                if len(ids) == 1:
                    assert response.status_code == 201
                    raise httpx.ReadTimeout('Synthetic lost acknowledgement')
                assert response.status_code == 200
                return response
        demo = create_app(Settings('http://127.0.0.1/api/v1/events', project['ingestion_key']), transport=LostResponse())
        async with demo.router.lifespan_context(demo):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=demo), base_url='http://demo') as web:
                assert (await web.post('/payments')).status_code == 200
            await asyncio.wait_for(demo.state.telemetry.queue.join(), 5)
            assert demo.state.telemetry.retries == 1 and demo.state.telemetry.delivered == 1
        assert len(ids) == 2 and ids[0] == ids[1]
    asyncio.run(run())
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        assert conn.execute('SELECT count(*) FROM events').fetchone()[0] == 1


def test_delivery_failures_queue_bounds_and_shutdown():
    async def run():
        calls = []
        async def blocked(request):
            calls.append(1)
            await asyncio.sleep(60)
        telemetry = Telemetry('http://127.0.0.1/events', KEY, transport=httpx.MockTransport(blocked), capacity=1, timeout=0.01)
        telemetry.emit({'event_id':'one'})
        telemetry.emit({'event_id':'two'})
        assert telemetry.queue.qsize() == 1 and telemetry.dropped == 1
        telemetry.start()
        await asyncio.wait_for(telemetry.queue.join(), 2)
        assert len(calls) == 3 and telemetry.dropped == 2
        telemetry.emit({'event_id':'three'})
        await telemetry.close(grace=0.01)
        assert telemetry.task.done() and telemetry.dropped == 3
        for code in (401, 422, 429):
            calls.clear()
            def rejected(request):
                calls.append(1)
                return httpx.Response(code, headers={'Retry-After':'60'})
            telemetry = Telemetry('http://127.0.0.1/events', KEY, transport=httpx.MockTransport(rejected))
            telemetry.start()
            telemetry.emit({'event_id':'event'})
            await telemetry.queue.join()
            await telemetry.close()
            assert len(calls) == 1 and telemetry.dropped == 1
    asyncio.run(run())


def test_ingestion_outage_does_not_break_payment_requests():
    async def run():
        async def unavailable(request):
            raise httpx.ConnectError('Unavailable')
        demo = create_app(Settings('http://127.0.0.1/events', KEY), transport=httpx.MockTransport(unavailable))
        async with demo.router.lifespan_context(demo):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=demo), base_url='http://demo') as web:
                for _ in range(4): assert (await web.post('/payments')).status_code == 200
            await asyncio.wait_for(demo.state.telemetry.queue.join(), 3)
            assert demo.state.telemetry.dropped == 4
    asyncio.run(run())
