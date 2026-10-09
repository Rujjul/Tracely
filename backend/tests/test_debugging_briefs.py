from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.debugging_briefs import format_brief, redact
from test_auth import client, register, ORIGIN
from test_phase8 import setup_incident, ingest_exception
from test_detector import BASE


def test_brief_owner_citations_and_redaction(client):
    project, incident, path = setup_incident(client)
    event = ingest_exception(client, project, message='token=SECRET person@example.com 192.168.1.2 +1 (555) 123-4567',
                             endpoint='https://example.com/pay?token=SECRET', metadata={'private':'DO_NOT_EXPORT'},
                             stack_trace='PRIVATE_STACK')
    response = client.get(path+'/debugging-brief')
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    text = response.json()['text']
    assert event['event_id'] in text and project['project']['id'] in text
    for sensitive in ('SECRET','person@example.com','192.168.1.2','555','DO_NOT_EXPORT','PRIVATE_STACK'):
        assert sensitive not in text
    assert 'counter evaluation timestamp is not stored' in text
    assert response.json()['synthetic'] is False
    with TestClient(app) as guest:
        assert guest.get(path+'/debugging-brief').status_code == 401
        assert guest.get(path+'/debugging-brief', headers={'Authorization':'Bearer '+project['ingestion_key']}).status_code == 401
    other = client.post('/api/v1/projects',headers=ORIGIN,json={'name':'other'}).json()['project']['id']
    assert client.get(f'/api/v1/projects/{other}/incidents/{incident["id"]}/debugging-brief').status_code == 404
    client.post('/api/v1/auth/logout',headers=ORIGIN)
    register(client,'another@example.com')
    assert client.get(path+'/debugging-brief').status_code == 404


def test_brief_bounded_missing_evidence_and_secret_patterns():
    incident=dict(id=uuid4(),service='payments',status='active',started_at=BASE,last_seen_at=BASE,
                  resolved_at=None,failure_count=5,request_count=20,thresholds={'window_seconds':300})
    evidence=dict(start_time=BASE-timedelta(minutes=5),end_time=BASE,total_events=500,total_groups=30,
                  events=[dict(event_id=uuid4(),received_at=BASE,message='x'*2048,endpoint='y'*2048,exception_type='z'*2048) for _ in range(50)])
    project=dict(id=uuid4(),name='demo')
    text = format_brief(project,incident,evidence)
    assert text.count('Event ID:') == 10 and len(text) < 14000
    assert '10 of 500' in text and '300 seconds' in text
    evidence.update(events=[],total_events=0,total_groups=0)
    assert 'No retained event evidence' in format_brief(project,incident,evidence)
    assert 'privatepass' not in redact('postgresql://user:privatepass@host/db')
    assert 'GOCSPX-example' not in redact('GOCSPX-example')
