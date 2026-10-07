import os
from datetime import timedelta
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from app.main import app
from app.fingerprints import fingerprint
from app.backfill_fingerprints import backfill
from test_auth import client, register, ORIGIN
from test_events import payload, send
from test_detector import BASE, add, tick, rows


def test_fingerprints_normalize_locations_without_merging_types_or_modules():
    a = fingerprint('ValueError', 'app/pay.py:12 in charge')
    assert a == fingerprint(' ValueError ', 'app/pay.py:999 in charge')
    assert a == fingerprint('ValueError', '  File "app/pay.py", line 44, in charge\nValueError: request 123')
    assert a == fingerprint('ValueError', 'app\\pay.py:99 in charge')
    assert a != fingerprint('TimeoutError', 'app/pay.py:12 in charge')
    assert a != fingerprint('ValueError', 'app/refunds.py:12 in charge')
    assert a != fingerprint('ValueError', 'other/pay.py:12 in charge')
    assert a != fingerprint('ValueError', 'app/pay.py:12 in refund')
    assert a == fingerprint('ValueError', 'app/pay.py:12 in charge\n.venv/lib/python3.12/site-packages/httpx/client.py:4 in get')
    assert fingerprint(None, 'app.py:1 in run') is None
    assert fingerprint('ValueError', ' ') is None
    assert fingerprint('ValueError', 'unknown trace A') != fingerprint('ValueError', 'unknown trace B')
    assert fingerprint('ValueError', 'db.py:82') == fingerprint('ValueError', 'ValueError at db.py:99')


def setup_incident(client):
    register(client)
    project = client.post('/api/v1/projects', headers=ORIGIN, json={'name': 'Phase 8'}).json()
    pid = project['project']['id']
    add(pid, -1)
    tick(0); tick(30)
    incident = rows('incidents')[0]
    path = f"/api/v1/projects/{pid}/incidents/{incident['id']}"
    return project, incident, path


def ingest_exception(client, project, **changes):
    body = {**payload(), 'event_type': 'exception', 'service': 'payments', 'level': 'ERROR',
            'exception_type': 'ValueError', 'stack_trace': 'app/pay.py:12 in charge', **changes}
    assert send(client, project['ingestion_key'], body).status_code == 201
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute('UPDATE events SET received_at=%s WHERE event_id=%s', (BASE-timedelta(seconds=1), body['event_id']))
    return body


def test_ingestion_groups_and_replay_preserves_original(client):
    project, incident, path = setup_incident(client)
    first = ingest_exception(client, project)
    ingest_exception(client, project, stack_trace='app/pay.py:99 in charge', message='different request 123')
    ingest_exception(client, project, stack_trace='app/refunds.py:12 in refund')
    ingest_exception(client, project, exception_type='TimeoutError')
    ingest_exception(client, project, service='other')
    assert send(client, project['ingestion_key'], {**first, 'stack_trace': 'other.py:1 in run'}).status_code == 200
    response = client.get(path)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    data = response.json()
    assert data['evidence']['total_groups'] == 3
    assert [g['event_count'] for g in data['evidence']['groups']] == [2, 1, 1]
    assert data['evidence']['total_events'] == 9  # Five failed requests plus four exception events.
    assert data['evidence']['ungrouped_events'] == 5
    assert data['incident']['request_count'] == 20  # Grouping does not affect detector truth.
    assert all(event['service'] == 'payments' for event in data['evidence']['events'])
    detail = client.get(f"/api/v1/projects/{project['project']['id']}/events/{first['event_id']}").json()['event']
    assert detail['fingerprint'] == fingerprint('ValueError', 'app/pay.py:12 in charge')


def test_incident_authorization_and_cross_project_ids(client):
    project, incident, path = setup_incident(client)
    with TestClient(app) as guest:
        assert guest.get(path).status_code == 401
        assert guest.get(path, headers={'Authorization': 'Bearer ' + project['ingestion_key']}).status_code == 401
    other = client.post('/api/v1/projects', headers=ORIGIN, json={'name': 'Other'}).json()['project']['id']
    assert client.get(f"/api/v1/projects/{other}/incidents/{incident['id']}").status_code == 404
    assert client.get(path.rsplit('/', 1)[0] + '/' + str(uuid4())).status_code == 404
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    register(client, 'other@example.com')
    assert client.get(path).status_code == 404


def test_bounded_evidence_and_interval(client):
    project, incident, path = setup_incident(client)
    for index in range(55):
        ingest_exception(client, project, stack_trace=f'app/module{index}.py:1 in run')
    outside = ingest_exception(client, project)
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute('UPDATE events SET received_at=%s WHERE event_id=%s', (BASE, outside['event_id']))
    data = client.get(path).json()['evidence']
    assert data['total_events'] == 60 and data['total_groups'] == 55
    assert len(data['events']) == 50 and data['events_truncated']
    assert len(data['groups']) == 20 and data['groups_truncated']
    assert outside['event_id'] not in [e['event_id'] for e in data['events']]


def test_backfill_is_repeatable_and_preserves_evidence(client):
    project, incident, path = setup_incident(client)
    body = ingest_exception(client, project)
    with psycopg.connect(os.environ['DATABASE_URL'], autocommit=True) as conn:
        conn.execute('UPDATE events SET fingerprint=NULL WHERE event_id=%s', (body['event_id'],))
        assert backfill(conn) == 1
        assert backfill(conn) == 0
        stored = conn.execute('SELECT stack_trace,message,fingerprint FROM events WHERE event_id=%s', (body['event_id'],)).fetchone()
        assert stored[:2] == (body['stack_trace'], body['message'])
        assert stored[2] == fingerprint(body['exception_type'], body['stack_trace'])
    assert client.get(path).json()['evidence']['total_groups'] == 1
    assert client.request('DELETE', f"/api/v1/projects/{project['project']['id']}", headers=ORIGIN,
                          json={'confirmation_name': 'Phase 8'}).status_code == 200
    assert client.get(path).status_code == 404
    assert not rows('incidents') and not rows('events')
