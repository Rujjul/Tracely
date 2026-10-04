import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from app import auth
from app.main import app
from app import projects
from test_auth import client, register, ORIGIN


def create(client, name='Payments API'):
    return client.post('/api/v1/projects', headers=ORIGIN, json={'name': name})


def delete(client, project_id, name='Payments API', headers=ORIGIN):
    return client.request('DELETE', f'/api/v1/projects/{project_id}', headers=headers,
                          json={'confirmation_name': name})


def seed_event(project_id):
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute('''INSERT INTO events(id,project_id,event_id,timestamp,event_type,level,service,message)
            VALUES (%s,%s,%s,now(),'request','INFO','test','Deletion test')''', (uuid4(), project_id, uuid4()))


def test_delete_authorization_and_confirmation(client):
    assert delete(client, uuid4()).status_code == 401
    register(client, 'owner@example.com')
    data = create(client).json()
    project_id = data['project']['id']
    assert delete(client, project_id, 'payments api').status_code == 422
    assert delete(client, project_id, 'Payments API ').status_code == 422
    assert delete(client, project_id, headers={}).status_code == 403
    assert len(client.get('/api/v1/projects').json()['projects']) == 1
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    assert delete(client, project_id, headers={**ORIGIN, 'Authorization':'Bearer '+data['ingestion_key']}).status_code == 401
    register(client, 'other@example.com')
    assert delete(client, project_id).status_code == 404
    assert delete(client, uuid4()).status_code == 404
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM projects').fetchone()[0] == 1


def test_delete_cascades_and_preserves_other_project(client):
    register(client)
    removed = create(client).json()['project']['id']
    kept = create(client, 'Keep me').json()['project']['id']
    seed_event(removed)
    seed_event(kept)
    client.post(f'/api/v1/projects/{removed}/keys/rotate', headers=ORIGIN)
    response = delete(client, removed)
    assert response.status_code == 200
    assert response.json()['status'] == 'deleted'
    assert response.headers['cache-control'] == 'no-store'
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT id FROM projects').fetchall() == [(UUID(kept),)]
        for table in ('project_keys', 'events'):
            assert connection.execute(f'SELECT count(*) FROM {table} WHERE project_id=%s', (removed,)).fetchone()[0] == 0
            assert connection.execute(f'SELECT count(*) FROM {table} WHERE project_id=%s', (kept,)).fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM users').fetchone()[0] == 1
    assert delete(client, removed).status_code == 404
    assert len(client.get('/api/v1/projects').json()['projects']) == 1


def test_delete_failure_rolls_back_all_related_records(client):
    register(client)
    project_id = create(client).json()['project']['id']
    seed_event(project_id)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute("""CREATE FUNCTION reject_event_delete() RETURNS trigger LANGUAGE plpgsql AS
            $$ BEGIN RAISE EXCEPTION 'Simulated deletion failure'; END $$""")
        connection.execute('CREATE TRIGGER reject_delete BEFORE DELETE ON events FOR EACH ROW EXECUTE FUNCTION reject_event_delete()')
    assert delete(client, project_id).status_code == 503
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        for table in ('projects','project_keys','events'):
            assert connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 1


def test_create_list_and_hashed_storage(client):
    register(client)
    response = create(client, '  Payments API  ')
    assert response.status_code == 201
    assert response.headers['cache-control'] == 'no-store'
    data = response.json()
    key = data['ingestion_key']
    assert data['project']['name'] == 'Payments API'
    assert key.startswith('trc_') and len(key) > 40
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        row = connection.execute('SELECT key_hash,key_prefix,revoked_at FROM project_keys').fetchone()
        assert row == (auth.digest(key), key[:12], None)
        assert key not in str(connection.execute('SELECT * FROM project_keys').fetchall())
    listing = client.get('/api/v1/projects')
    assert len(listing.json()['projects']) == 1
    assert key not in listing.text and 'key_hash' not in listing.text
    assert 'ingestion_key' not in listing.text


def test_isolation_and_unauthenticated_access(client):
    assert client.get('/api/v1/projects').status_code == 401
    assert create(client).status_code == 401
    register(client, 'owner@example.com')
    data = create(client).json()
    project_id = data['project']['id']
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    # An ingestion key must not authorize browser reads or key management.
    assert client.get('/api/v1/projects', headers={'Authorization': 'Bearer '+data['ingestion_key']}).status_code == 401
    register(client, 'other@example.com')
    assert client.get('/api/v1/projects').json()['projects'] == []
    assert client.post(f'/api/v1/projects/{project_id}/keys/rotate', headers=ORIGIN).status_code == 404
    assert client.post(f'/api/v1/projects/{uuid4()}/keys/rotate', headers=ORIGIN).status_code == 404


def test_rotation_revokes_old_key(client):
    register(client)
    original = create(client).json()
    response = client.post(f"/api/v1/projects/{original['project']['id']}/keys/rotate", headers=ORIGIN)
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    new = response.json()['ingestion_key']
    assert new != original['ingestion_key']
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT revoked_at IS NOT NULL FROM project_keys WHERE key_hash=%s', (auth.digest(original['ingestion_key']),)).fetchone()[0]
        assert connection.execute('SELECT key_hash FROM project_keys WHERE revoked_at IS NULL').fetchall() == [(auth.digest(new),)]


def test_validation_origin_and_expiry(client):
    register(client)
    for name in ('', '   ', 'x'*101):
        assert create(client, name).status_code == 422
    assert client.post('/api/v1/projects', headers=ORIGIN, json={'name':'Test', 'owner_id':str(uuid4())}).status_code == 422
    assert client.post('/api/v1/projects', json={'name':'Test'}).status_code == 403
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute("UPDATE auth_sessions SET expires_at=now()-interval '1 second'")
    assert client.get('/api/v1/projects').status_code == 401
    assert create(client).status_code == 401


def test_concurrent_rotations_keep_one_active_key(client):
    register(client)
    project_id = create(client).json()['project']['id']
    token = client.cookies.get(auth.SESSION_COOKIE)
    def rotate():
        with TestClient(app, base_url='http://127.0.0.1:8000') as other:
            other.cookies.set(auth.SESSION_COOKIE, token, domain='127.0.0.1', path='/api/v1')
            return other.post(f'/api/v1/projects/{project_id}/keys/rotate', headers=ORIGIN)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: rotate(), range(2)))
    assert all(response.status_code == 200 for response in responses)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM project_keys WHERE revoked_at IS NULL').fetchone()[0] == 1
        assert connection.execute('SELECT count(*) FROM project_keys WHERE revoked_at IS NOT NULL').fetchone()[0] == 2


def test_existing_session_cookie_upgrade_does_not_extend_expiry(client):
    register(client)
    token = client.cookies.get(auth.SESSION_COOKIE)
    client.cookies.clear()
    client.cookies.set(auth.SESSION_COOKIE, token, domain='127.0.0.1', path='/api/v1/auth')
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        before = connection.execute('SELECT expires_at FROM auth_sessions').fetchone()[0]
    assert client.get('/api/v1/projects').status_code == 401
    assert client.get('/api/v1/auth/me').status_code == 200
    assert client.get('/api/v1/projects').status_code == 200
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT expires_at FROM auth_sessions').fetchone()[0] == before
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    assert client.get('/api/v1/projects').status_code == 401


def test_failed_rotation_preserves_previous_key(client, monkeypatch):
    register(client)
    original = create(client).json()
    def fail(connection, project_id):
        raise RuntimeError('Simulated key creation failure')
    monkeypatch.setattr(projects, 'new_key', fail)
    with pytest.raises(RuntimeError, match='Simulated key creation failure'):
        client.post(f"/api/v1/projects/{original['project']['id']}/keys/rotate", headers=ORIGIN)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT key_hash FROM project_keys WHERE revoked_at IS NULL').fetchall() == [(auth.digest(original['ingestion_key']),)]
