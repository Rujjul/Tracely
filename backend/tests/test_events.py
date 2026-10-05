import json
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from app import events
from app.main import app
from test_auth import client, register, ORIGIN


def setup(client):
    register(client)
    events.attempts.clear()
    return client.post('/api/v1/projects', headers=ORIGIN, json={'name':'Ingestion test'}).json()


def payload():
    return {'event_id':str(uuid4()), 'timestamp':'2026-10-05T15:30:00+05:30',
            'event_type':'request', 'level':'INFO', 'service':'demo', 'message':'Request completed',
            'status_code':200, 'latency_ms':12.5}


def send(client, key, body):
    return client.post('/api/v1/events', headers={'Authorization':'Bearer '+key}, json=body)


def test_persistence_replay_and_project_scope(client):
    project = setup(client)
    body = payload()
    key = project['ingestion_key']
    assert send(client,key,body).status_code == 201
    replay = send(client,key,{**body,'message':'Must not overwrite'})
    assert replay.status_code == 200 and replay.json() == {'status':'stored','event_id':body['event_id']}
    second = client.post('/api/v1/projects', headers=ORIGIN, json={'name':'Another'}).json()
    assert send(client,second['ingestion_key'],body).status_code == 201
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        rows = connection.execute('SELECT message,timestamp,received_at,project_id FROM events').fetchall()
        assert len(rows) == 2 and all(row[0] == body['message'] for row in rows)
        assert all(row[1].hour == 10 and row[2].tzinfo is not None for row in rows)
        assert len({row[3] for row in rows}) == 2


def test_wrong_revoked_deleted_keys_and_session_rejected(client):
    project = setup(client)
    body = payload()
    assert client.post('/api/v1/events',json=body).status_code == 401
    assert send(client,'trc_'+'x'*43,body).status_code == 401
    assert send(client,client.cookies.get('tracely_session'),body).status_code == 401
    rotated = client.post(f"/api/v1/projects/{project['project']['id']}/keys/rotate", headers=ORIGIN).json()
    assert send(client,project['ingestion_key'],body).status_code == 401
    assert send(client,rotated['ingestion_key'],body).status_code == 201
    client.request('DELETE',f"/api/v1/projects/{project['project']['id']}",headers=ORIGIN,json={'confirmation_name':'Ingestion test'})
    assert send(client,rotated['ingestion_key'],payload()).status_code == 401


def test_validation_and_size_limits(client):
    key = setup(client)['ingestion_key']
    base = payload()
    for change in [
        {'timestamp':'2026-10-05T10:00:00'}, {'timestamp':'invalid'}, {'timestamp':123},
        {'event_id':'bad'}, {'event_type':'deployment'}, {'level':'unknown'}, {'message':123},
        {'service':' '}, {'status_code':True}, {'status_code':600}, {'status_code':-1},
        {'status_code':'200'}, {'latency_ms':-1}, {'latency_ms':'12'}, {'metadata':[]},
        {'project_id':str(uuid4())}, {'received_at':'2026-10-05T10:00:00Z'}, {'fingerprint':'client-set'},
        {'message':'NUL\x00'},
    ]:
        assert send(client,key,{**base,**change}).status_code == 422, change
    for change in [{'message':'é'*1025},{'stack_trace':'x'*8193},{'metadata':{'large':'x'*4096}}]:
        assert send(client,key,{**base,**change}).status_code == 413
    headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
    assert client.post('/api/v1/events',headers=headers,content='x'*65537).status_code == 413
    assert client.post('/api/v1/events',headers=headers,content=iter([b' '*32768,b' '*32769])).status_code == 413
    for raw in ['{', '[]', json.dumps({**base,'latency_ms':float('nan')}), json.dumps({**base,'metadata':{'v':float('inf')}})]:
        assert client.post('/api/v1/events',headers=headers,content=raw).status_code == 422
    assert client.post('/api/v1/events',headers={'Authorization':'Bearer '+key},content='{}').status_code == 415
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM events').fetchone()[0] == 0


def test_redaction_and_exception_event(client):
    key = setup(client)['ingestion_key']
    body = {**payload(), 'event_type':'exception', 'level':'ERROR', 'status_code':None,
            'message':'password=hunter2 '+key, 'stack_trace':'Authorization: Bearer abc123',
            'metadata':{'password':'hunter2','nested':[{'api_key':'secret-value'}], 'safe':'keep'}}
    assert send(client,key,body).status_code == 201
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        row = connection.execute('SELECT event_type,message,stack_trace,metadata FROM events').fetchone()
        assert row[0] == 'exception' and row[3]['safe'] == 'keep'
        assert all(secret not in str(row) for secret in ['hunter2',key,'abc123','secret-value'])


def test_concurrent_duplicate_and_rate_limit(client, monkeypatch):
    project=setup(client)
    key=project['ingestion_key']
    body=payload()
    def post(_):
        with TestClient(app) as other:
            return send(other,key,body).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(post,range(2))) == [200,201]
    monkeypatch.setattr(events,'RATE_LIMIT',2)
    limited=send(client,key,payload())
    assert limited.status_code == 429 and int(limited.headers['Retry-After']) > 0
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM events').fetchone()[0] == 1


def test_database_failure_never_acknowledges_storage(client):
    key=setup(client)['ingestion_key']
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute("""CREATE FUNCTION fail_event_insert() RETURNS trigger LANGUAGE plpgsql AS
            $$ BEGIN RAISE EXCEPTION 'Synthetic failure'; END $$""")
        connection.execute('CREATE TRIGGER fail_insert BEFORE INSERT ON events FOR EACH ROW EXECUTE FUNCTION fail_event_insert()')
    assert send(client,key,payload()).status_code == 503
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM events').fetchone()[0] == 0
