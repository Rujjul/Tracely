import os
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from app.main import app
from test_auth import client, register, ORIGIN
from test_events import setup, payload, send


def url(project):
    return f"/api/v1/projects/{project['project']['id']}/events"


def test_event_reads_require_owner_cookie_for_list_and_detail(client):
    project = setup(client)
    body = payload()
    body.update(stack_trace='safe stack', metadata={'request_id':'test-request'})
    assert send(client, project['ingestion_key'], body).status_code == 201
    detail_url = url(project) + '/' + body['event_id']
    listed = client.get(url(project))
    assert listed.status_code == 200 and listed.headers['cache-control'] == 'no-store'
    assert 'stack_trace' not in listed.json()['events'][0]
    detail = client.get(detail_url).json()['event']
    assert detail['stack_trace'] == 'safe stack' and detail['metadata']['request_id'] == 'test-request'
    assert client.get(url(project) + '/' + str(uuid4())).status_code == 404
    with TestClient(app) as other:
        for path in (url(project), detail_url):
            assert other.get(path).status_code == 401
            assert other.get(path, headers={'Authorization':'Bearer '+project['ingestion_key']}).status_code == 401
        register(other, 'another@example.com')
        for path in (url(project), detail_url, f'/api/v1/projects/{uuid4()}/events'):
            assert other.get(path).status_code == 404
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("UPDATE auth_sessions SET expires_at=now()-interval '1 second'")
    assert client.get(url(project)).status_code == 401


def test_filters_are_literal_combined_and_time_zone_aware(client):
    project = setup(client)
    for level, service, message in [('ERROR', 'payments', '100%_done'), ('INFO', 'gateway', '100 percent done'), ('WARN', 'payments', 'Slow dependency')]:
        body = {**payload(), 'level':level, 'service':service, 'message':message, 'endpoint':'/payments', 'exception_type':'DemoException'}
        assert send(client, project['ingestion_key'], body).status_code == 201
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("UPDATE events SET received_at='2026-10-05T10:00:00Z'")
    result = client.get(url(project), params={'service':'payments', 'level':'ERROR','q':'%_','start_time':'2026-10-05T15:30:00+05:30','end_time':'2026-10-05T10:01:00Z'})
    assert result.status_code == 200 and len(result.json()['events']) == 1
    for params, count in [({'q':'DEMOEXCEPTION'},3), ({'q':'/payments'},3), ({'q':"' OR true --"},0), ({'q':'missing'},0), ({'end_time':'2026-10-05T10:00:00Z'},0), ({'service':'gateway'},1)]:
        assert len(client.get(url(project),params=params).json()['events']) == count


def test_keyset_pagination_handles_ties_new_arrivals_and_filter_binding(client):
    project = setup(client)
    for _ in range(7): assert send(client, project['ingestion_key'], payload()).status_code == 201
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("UPDATE events SET received_at='2026-01-01T00:00:00Z'")
        expected = [str(row[0]) for row in conn.execute('SELECT event_id FROM events ORDER BY received_at DESC,id DESC')]
    first = client.get(url(project), params={'limit':2}).json()
    cursor = first['next_cursor']
    collected = [row['event_id'] for row in first['events']]
    # Newer arrivals are reserved for a refresh, not inserted into later pages.
    assert send(client, project['ingestion_key'], payload()).status_code == 201
    assert client.get(url(project),params={'cursor':cursor,'q':'changed'}).status_code == 422
    second_project = client.post('/api/v1/projects',headers=ORIGIN,json={'name':'Another'}).json()
    assert client.get(url(second_project),params={'cursor':cursor}).status_code == 422
    while cursor:
        response = client.get(url(project), params={'limit':2,'cursor':cursor})
        assert response.status_code == 200
        page = response.json()
        collected.extend(row['event_id'] for row in page['events'])
        cursor = page['next_cursor']
    assert collected == expected and len(set(collected)) == 7
    assert len(client.get(url(project)).json()['events']) == 8


def test_bounds_invalid_cursors_empty_and_deleted_projects(client):
    project = setup(client)
    assert client.get(url(project)).json() == {'events':[], 'next_cursor':None}
    for params in ({'limit':0}, {'limit':101}, {'level':'invalid'}, {'cursor':'%%%invalid'}, {'cursor':'e30='}, {'q':'x'*201}, {'q':'\x00'}, {'start_time':'2026-01-01'}, {'start_time':'2026-01-02T00:00:00Z','end_time':'2026-01-01T00:00:00Z'}):
        assert client.get(url(project),params=params).status_code == 422
    assert client.request('DELETE',f"/api/v1/projects/{project['project']['id']}",headers=ORIGIN,json={'confirmation_name':'Ingestion test'}).status_code == 200
    assert client.get(url(project)).status_code == 404


def test_detail_is_scoped_even_when_event_ids_match(client):
    first = setup(client)
    second = client.post('/api/v1/projects',headers=ORIGIN,json={'name':'Second'}).json()
    body = payload()
    assert send(client,first['ingestion_key'],{**body,'message':'First project'}).status_code == 201
    assert send(client,second['ingestion_key'],{**body,'message':'Second project'}).status_code == 201
    for project, expected in [(first,'First project'),(second,'Second project')]:
        assert client.get(url(project)+'/'+body['event_id']).json()['event']['message'] == expected
