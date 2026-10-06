"""Transactional request-failure detector. No fingerprints or investigation logic."""
import math
import os
from dataclasses import asdict, dataclass
from datetime import timedelta
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

VERSION = 'request-failure-v1'
INCIDENT_TYPE = 'request_failure_rate'


@dataclass(frozen=True)
class Config:
    window_seconds: int = 300
    interval_seconds: int = 30
    min_requests: int = 20
    min_failures: int = 5
    trigger_rate: float = 0.10
    resolve_rate: float = 0.05

    def __post_init__(self):
        if any(type(value) is not int or value < 1 for value in (self.window_seconds, self.interval_seconds, self.min_requests, self.min_failures)):
            raise ValueError('Detector durations and counts must be positive integers.')
        if self.interval_seconds > self.window_seconds or self.window_seconds > 86400:
            raise ValueError('Detector interval must fit in a window of at most one day.')
        if not all(math.isfinite(value) for value in (self.trigger_rate,self.resolve_rate)) or not 0 < self.resolve_rate < self.trigger_rate <= 1:
            raise ValueError('Require 0 < resolve rate < trigger rate <= 1.')

    @classmethod
    def from_env(cls):
        return cls(**{name: cast(os.getenv('DETECTOR_' + name.upper(), str(default)))
                     for name, default, cast in [('window_seconds',300,int), ('interval_seconds',30,int),
                        ('min_requests',20,int), ('min_failures',5,int), ('trigger_rate',0.10,float), ('resolve_rate',0.05,float)]})

    def recorded(self):
        return {**asdict(self), 'opening_evaluations':2, 'closing_evaluations':2}

    @classmethod
    def recorded_config(cls, values):
        return cls(**{name: values[name] for name in cls.__dataclass_fields__})


def evaluate(connection, config=None, *, at=None):
    """Commit one evaluation atomically; `at` is an internal deterministic-test clock."""
    config = config or Config()
    if at is not None and (at.tzinfo is None or at.utcoffset() is None):
        raise ValueError('Evaluation time must be timezone-aware.')
    stats = {'evaluated':0, 'opened':0, 'updated':0, 'resolved':0, 'skipped':0}
    with connection.transaction(), connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute("SET LOCAL statement_timeout='15s'")
        cursor.execute("SET LOCAL lock_timeout='2s'")
        # Transaction-scoped lock covers worker duplicates without sticky session locks.
        cursor.execute('SELECT pg_try_advisory_xact_lock(731007,hashtext(current_schema())) AS acquired')
        if not cursor.fetchone()['acquired']:
            return {**stats, 'skipped':1}
        if at is None:
            cursor.execute('SELECT clock_timestamp() AS at')
            at = cursor.fetchone()['at']
        # Lock in project-first order, matching ingestion/deletion. A deleted project
        # cannot acquire new incident/state rows partway through an evaluation.
        cursor.execute('SELECT id FROM projects ORDER BY id FOR SHARE')
        projects = cursor.fetchall()
        for project in projects:
            project_id = project['id']
            cursor.execute('SELECT * FROM detector_states WHERE project_id=%s', (project_id,))
            states = {row['service']: row for row in cursor.fetchall()}
            cursor.execute("SELECT * FROM incidents WHERE project_id=%s AND incident_type=%s AND status='active'", (project_id,INCIDENT_TYPE))
            active = {row['service']: row for row in cursor.fetchall()}
            # Current and active-incident windows can differ after a config change.
            windows = {config.window_seconds, *(row['thresholds']['window_seconds'] for row in active.values())}
            cursor.execute('''SELECT DISTINCT service FROM events WHERE project_id=%s AND event_type='request'
                AND received_at>%s AND received_at<=%s''', (project_id,at-timedelta(seconds=max(windows)),at))
            services = set(states) | set(active) | {row['service'] for row in cursor.fetchall()}
            for service in sorted(services):
                incident, previous = active.get(service), states.get(service)
                policy = Config.recorded_config(incident['thresholds']) if incident else config
                recorded = {**policy.recorded(), 'cadence_seconds': config.interval_seconds}
                if previous and at < previous['last_evaluated_at'] + timedelta(seconds=config.interval_seconds):
                    stats['skipped'] += 1
                    continue
                continuous = (previous is not None and previous['detector_version'] == VERSION
                    and previous['thresholds'] == recorded
                    and at - previous['last_evaluated_at'] <= timedelta(seconds=2*config.interval_seconds))
                cursor.execute('''SELECT count(*) AS requests,
                    count(*) FILTER (WHERE status_code>=500 OR level='ERROR') AS failures,
                    min(received_at) FILTER (WHERE status_code>=500 OR level='ERROR') AS first_failure,
                    max(received_at) FILTER (WHERE status_code>=500 OR level='ERROR') AS last_failure
                    FROM events WHERE project_id=%s AND service=%s AND event_type='request'
                    AND received_at>%s AND received_at<=%s''', (project_id,service,at-timedelta(seconds=policy.window_seconds),at))
                counts = cursor.fetchone()
                requests, failures = counts['requests'], counts['failures']
                rate = failures/requests if requests else 0
                status = ('insufficient_data' if requests < policy.min_requests else
                          'breaching' if failures >= policy.min_failures and rate >= policy.trigger_rate else
                          'healthy' if rate < policy.resolve_rate else 'neutral')
                bad = min(2, (previous['bad_streak'] if continuous else 0) + 1) if status == 'breaching' else 0
                good = min(2, (previous['healthy_streak'] if continuous else 0) + 1) if status == 'healthy' else 0
                first = (previous['first_failure_at'] if continuous and previous['bad_streak'] else counts['first_failure']) if bad else None
                if incident:
                    resolved = good >= 2
                    cursor.execute('''UPDATE incidents SET request_count=%s,failure_count=%s,
                        last_seen_at=GREATEST(last_seen_at,COALESCE(%s,last_seen_at)),
                        status=%s,resolved_at=%s WHERE id=%s AND project_id=%s''',
                        (requests,failures,counts['last_failure'],'resolved' if resolved else 'active',at if resolved else None,incident['id'],project_id))
                    stats['resolved' if resolved else 'updated'] += 1
                elif bad >= 2:
                    cursor.execute('''INSERT INTO incidents(id,project_id,service,incident_type,status,severity,
                        started_at,last_seen_at,failure_count,request_count,detector_version,thresholds)
                        VALUES (%s,%s,%s,%s,'active','warning',%s,%s,%s,%s,%s,%s)''',
                        (uuid4(),project_id,service,INCIDENT_TYPE,first,counts['last_failure'],failures,requests,VERSION,Jsonb(recorded)))
                    stats['opened'] += 1
                cursor.execute('''INSERT INTO detector_states(id,project_id,service,bad_streak,healthy_streak,
                    first_failure_at,last_evaluated_at,evaluation_status,failure_count,request_count,detector_version,thresholds)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (project_id,service) DO UPDATE SET bad_streak=EXCLUDED.bad_streak,
                    healthy_streak=EXCLUDED.healthy_streak,first_failure_at=EXCLUDED.first_failure_at,
                    last_evaluated_at=EXCLUDED.last_evaluated_at,evaluation_status=EXCLUDED.evaluation_status,
                    failure_count=EXCLUDED.failure_count,request_count=EXCLUDED.request_count,
                    detector_version=EXCLUDED.detector_version,thresholds=EXCLUDED.thresholds''',
                    (uuid4(),project_id,service,bad,good,first,at,status,failures,requests,VERSION,Jsonb(recorded)))
                stats['evaluated'] += 1
    return stats
