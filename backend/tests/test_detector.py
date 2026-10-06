import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
import pytest

from app.detector import Config, evaluate
from test_auth import client, register, ORIGIN

BASE = datetime(2026, 10, 6, tzinfo=timezone.utc)


def project(client, name='Detector test'):
    return client.post('/api/v1/projects', headers=ORIGIN, json={'name':name}).json()['project']['id']


def add(project_id, second, requests=20, failures=5, service='payments', event_type='request', level_only=False):
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        with conn.cursor() as cursor:
            cursor.executemany('''INSERT INTO events(id,project_id,event_id,timestamp,received_at,event_type,level,service,message,status_code)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'synthetic detector evidence',%s)''',
                [(uuid4(),project_id,uuid4(),BASE-timedelta(days=30),BASE+timedelta(seconds=second),event_type,
                  'ERROR' if i<failures and level_only else 'INFO',service,500 if i<failures and not level_only else 200) for i in range(requests)])


def tick(second, config=None):
    with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True) as conn:
        return evaluate(conn, config, at=BASE+timedelta(seconds=second))


def rows(table):
    with psycopg.connect(os.environ['DATABASE_URL'],row_factory=dict_row) as conn:
        # Table names are test constants only.
        return conn.execute('SELECT * FROM ' + table).fetchall()


def test_open_update_insufficient_resolve_and_reopen(client):
    register(client); pid=project(client)
    add(pid,-1,failures=0)
    tick(0);tick(30)
    assert not rows('incidents')
    add(pid,50)
    assert tick(60)['opened'] == 0
    assert tick(90)['opened'] == 1
    incident=rows('incidents')[0]
    assert incident['request_count']==40 and incident['failure_count']==5
    assert incident['started_at']==BASE+timedelta(seconds=50)
    assert incident['thresholds']['opening_evaluations']==2 and incident['detector_version']=='request-failure-v1'
    assert tick(120)['updated']==1 and len(rows('incidents'))==1
    tick(600)
    assert rows('detector_states')[0]['evaluation_status']=='insufficient_data'
    assert rows('incidents')[0]['status']=='active'
    assert rows('incidents')[0]['last_seen_at']==incident['last_seen_at']
    add(pid,610,failures=0)
    tick(630)
    assert rows('incidents')[0]['status']=='active'
    assert tick(660)['resolved']==1
    add(pid,670)
    tick(690);tick(720)
    assert sorted(row['status'] for row in rows('incidents'))==['active','resolved']


def test_exception_denominator_minimums_and_received_time_boundaries(client):
    register(client);pid=project(client)
    add(pid,-300,failures=20)  # Lower boundary excluded.
    add(pid,100,failures=20)  # Future received_at excluded.
    add(pid,-1,requests=20,failures=4,level_only=True)
    add(pid,-1,requests=100,failures=100,event_type='exception')
    tick(0);tick(30)
    state=rows('detector_states')[0]
    assert state['request_count']==20 and state['failure_count']==4
    assert state['evaluation_status']=='neutral' and not rows('incidents')
    add(pid,40,requests=1,failures=1,level_only=True)
    tick(60);tick(90)
    assert rows('incidents')[0]['failure_count']==5
    assert rows('incidents')[0]['request_count']==21


def test_low_traffic_and_exact_recovery_threshold_do_not_resolve(client):
    register(client);pid=project(client)
    add(pid,-1,requests=19,failures=19)
    tick(0);tick(30)
    assert not rows('incidents')
    add(pid,40,requests=1,failures=0)
    tick(60);tick(90)
    add(pid,400,requests=20,failures=1)
    tick(420);tick(450)
    assert rows('detector_states')[0]['evaluation_status']=='neutral'  # Exactly 5% is not healthy.
    assert rows('incidents')[0]['status']=='active'


def test_restart_cadence_concurrency_and_config_provenance(client):
    register(client);pid=project(client)
    add(pid,-1)
    tick(0)
    assert tick(0)['skipped']==1 and tick(29)['skipped']==1
    # Fresh connections represent independent/restarted workers.
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(tick,[30,30]))
    assert sum(item['opened'] for item in results)==1
    assert len(rows('incidents'))==1
    # Active incidents keep their original rules after environment changes.
    tick(60,Config(min_requests=1000))
    assert rows('incidents')[0]['thresholds']['min_requests']==20
    assert rows('detector_states')[0]['evaluation_status']=='breaching'
    add(pid,500,failures=0)
    changed=Config(interval_seconds=120,min_requests=1000)
    tick(510,changed);tick(630,changed)
    assert rows('incidents')[0]['status']=='resolved'


def test_missed_ticks_and_configuration_changes_reset_streaks(client):
    register(client);pid=project(client)
    add(pid,-1)
    tick(0);tick(90)
    assert not rows('incidents')
    tick(120,Config(trigger_rate=0.20))
    assert not rows('incidents')
    tick(150,Config(trigger_rate=0.20))
    assert len(rows('incidents'))==1


def test_project_service_isolation_and_deletion_cascades(client):
    register(client);first=project(client);second=project(client,'Second')
    add(first,-1,service='payments');add(first,-1,service='gateway',failures=0)
    add(second,-1,service='payments',failures=0)
    tick(0);tick(30)
    assert len(rows('incidents'))==1 and str(rows('incidents')[0]['project_id'])==first
    result=client.request('DELETE',f'/api/v1/projects/{first}',headers=ORIGIN,json={'confirmation_name':'Detector test'})
    assert result.status_code==200
    assert not rows('incidents')
    assert len(rows('detector_states'))==1 and str(rows('detector_states')[0]['project_id'])==second
    tick(60)
    assert not rows('incidents')


def test_failed_transaction_rolls_back_incident_and_streak(client):
    register(client);pid=project(client);add(pid,-1);tick(0)
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("""CREATE FUNCTION reject_detector_update() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic write failure'; END $$""")
        conn.execute('CREATE TRIGGER reject_update BEFORE UPDATE ON detector_states FOR EACH ROW EXECUTE FUNCTION reject_detector_update()')
    with pytest.raises(psycopg.Error): tick(30)
    assert not rows('incidents') and rows('detector_states')[0]['bad_streak']==1
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute('DROP TRIGGER reject_update ON detector_states')
    assert tick(30)['opened']==1


def test_detector_configuration_rejects_invalid_values():
    for values in ({'window_seconds':0},{'interval_seconds':301},{'trigger_rate':float('nan')},
                   {'resolve_rate':0.1},{'min_requests':-1},{'min_failures':True}):
        with pytest.raises(ValueError): Config(**values)
