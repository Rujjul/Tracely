import os
from datetime import timedelta
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient
from app.main import app
from test_auth import client, register, ORIGIN
from test_detector import BASE, add, project, tick


def window():
    return {'start_time': (BASE-timedelta(seconds=60)).isoformat(), 'end_time': BASE.isoformat()}


def test_overview_counts_buckets_services_and_request_semantics(client):
    register(client); pid = project(client)
    other = project(client, 'Other')
    add(pid,-30,requests=20,failures=5)
    add(pid,-30,requests=3,failures=3,event_type='exception')
    add(pid,-30,requests=2,failures=1,service='gateway',level_only=True)
    add(other,-30,requests=99,failures=99)
    add(pid,0,requests=7,failures=7)  # Exclusive end.
    add(pid,-61,requests=7,failures=7)
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("UPDATE events SET latency_ms=100 WHERE project_id=%s AND event_type='request'", (pid,))
        conn.execute("UPDATE events SET latency_ms=99999 WHERE event_type='exception'")
    response = client.get(f'/api/v1/projects/{pid}/overview', params=window())
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'no-store'
    body=response.json()
    assert body['requests']==22 and body['failures']==6 and body['total_events']==25
    assert body['error_rate']==6/22 and body['median_latency_ms']==100
    assert len(body['buckets'])==24 and sum(b['requests'] for b in body['buckets'])==22
    assert sum(b['failures'] for b in body['buckets'])==6
    assert body['total_services']==2 and sum(s['requests'] for s in body['services'])==22
    assert all(s['evaluation_status'] is None for s in body['services'])
    service=client.get(f'/api/v1/projects/{pid}/overview',params={**window(),'service':'gateway'}).json()
    assert service['requests']==2 and service['failures']==1 and service['total_services']==1


def test_empty_overview_and_current_incidents_outside_window(client):
    register(client);pid=project(client)
    add(pid,-30);tick(0);tick(30)
    body=client.get(f'/api/v1/projects/{pid}/overview',params={'start_time':(BASE+timedelta(hours=1)).isoformat(),'end_time':(BASE+timedelta(hours=2)).isoformat()}).json()
    assert body['requests']==0 and body['error_rate'] is None and body['median_latency_ms'] is None
    assert body['active_incidents']==1 and body['services']==[]
    assert all(b['requests']==0 for b in body['buckets'])
    body=client.get(f'/api/v1/projects/{pid}/overview',params=window()).json()
    assert body['services'][0]['active_incident']
    assert body['services'][0]['evaluation_status']=='breaching'
    assert body['services'][0]['last_evaluated_at']


def insert_incidents(pid):
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        for index in range(6):
            conn.execute('''INSERT INTO incidents(id,project_id,service,incident_type,status,severity,started_at,
                last_seen_at,resolved_at,request_count,failure_count,detector_version,thresholds)
                VALUES (%s,%s,%s,'request_failure_rate',%s,'warning',%s,%s,%s,20,5,'test','{}')''',
                (uuid4(),pid,'payments' if index<3 else 'gateway','active' if index==0 else 'resolved',BASE,BASE,
                 None if index==0 else BASE+timedelta(seconds=10)))


def test_incident_keyset_filters_details_and_cursor_binding(client):
    register(client);pid=project(client);insert_incidents(pid)
    url=f'/api/v1/projects/{pid}/incidents'
    first=client.get(url,params={'limit':2}).json()
    second=client.get(url,params={'limit':2,'cursor':first['next_cursor']}).json()
    third=client.get(url,params={'limit':2,'cursor':second['next_cursor']}).json()
    ids=[row['id'] for page in (first,second,third) for row in page['incidents']]
    assert len(set(ids))==6 and third['next_cursor'] is None
    assert ids==sorted(ids,reverse=True)  # Same timestamp: UUID tie-breaker.
    assert client.get(url+'/'+ids[0]).status_code==200
    assert len(client.get(url,params={'status':'active'}).json()['incidents'])==1
    assert len(client.get(url,params={'service':'gateway','status':'resolved'}).json()['incidents'])==3
    assert client.get(url,params={'end_time':BASE.isoformat()}).json()['incidents']==[]
    assert len(client.get(url,params={'start_time':BASE.isoformat()}).json()['incidents'])==6
    assert client.get(url,params={'cursor':first['next_cursor'],'status':'active'}).status_code==422
    other=project(client,'Other')
    assert client.get(f'/api/v1/projects/{other}/incidents',params={'cursor':first['next_cursor']}).status_code==422


def test_authentication_ownership_and_validation(client):
    register(client);pid=project(client)
    for route in ('overview','incidents'):
        url=f'/api/v1/projects/{pid}/{route}'
        with TestClient(app) as guest:
            assert guest.get(url).status_code==401
        assert client.get(url,params={'start_time':BASE.isoformat(),'end_time':BASE.isoformat()}).status_code==422
        assert client.get(url,params={'start_time':'2026-01-01'}).status_code==422
        assert client.get(url,params={'service':'bad\x00'}).status_code==422
    assert client.get(f'/api/v1/projects/{pid}/overview',params={'start_time':BASE.isoformat(),'end_time':(BASE+timedelta(days=8)).isoformat()}).status_code==422
    for params in ({'limit':0},{'limit':101},{'status':'unknown'},{'cursor':'garbage'}):
        assert client.get(f'/api/v1/projects/{pid}/incidents',params=params).status_code==422
    client.post('/api/v1/auth/logout',headers=ORIGIN);register(client,'other@example.com')
    for route in ('overview','incidents'):
        assert client.get(f'/api/v1/projects/{pid}/{route}').status_code==404


def test_service_response_bound_preserves_total_counts(client):
    register(client);pid=project(client)
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        for index in range(101):
            conn.execute('''INSERT INTO events(id,project_id,event_id,timestamp,received_at,event_type,level,service,message,status_code)
                VALUES (%s,%s,%s,%s,%s,'request','INFO',%s,'test',200)''',
                (uuid4(),pid,uuid4(),BASE,BASE-timedelta(seconds=1),f'service-{index}'))
    data=client.get(f'/api/v1/projects/{pid}/overview',params=window()).json()
    assert data['requests']==101 and data['total_services']==101
    assert len(data['services'])==100 and data['services_truncated']
