"""Short Phase 5 smoke run, not a detector benchmark. Prints synthetic JSON evidence."""
import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from dotenv import load_dotenv


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=3, help='Requests per stage (1–20)')
    parser.add_argument('--url', default='http://127.0.0.1:8001')
    args = parser.parse_args()
    target = urlsplit(args.url)
    if not 1 <= args.count <= 20 or target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1') or target.username or target.password or target.query or target.fragment:
        parser.error('Use 1–20 requests and a local HTTP demo URL without credentials.')
    load_dotenv(Path(__file__).with_name('.env'))
    token = os.getenv('DEMO_CONTROL_TOKEN', '')
    if len(token) < 32:
        parser.error('Set DEMO_CONTROL_TOKEN in demo-app/.env first.')
    headers = {'X-Demo-Control-Token': token}
    report = {'scenario_id': str(uuid4()), 'started_at': utc(), 'service': 'payment-api', 'stages': []}
    with httpx.Client(base_url=args.url, timeout=5, follow_redirects=False) as client:
        # Ensure the token/controls work before starting or attempting reset.
        client.get('/_demo/fault', headers=headers).raise_for_status()
        baseline = client.get('/health').json()['telemetry']
        try:
            for mode in ('none', 'db_timeout', 'none', 'unhandled_exception', 'none', 'slow_dependency', 'none'):
                changed = client.post('/_demo/fault', headers=headers, json={'mode': mode})
                changed.raise_for_status()
                stage = {'fault': mode, 'started_at': changed.json()['changed_at'], 'requests': []}
                report['stages'].append(stage)
                for _ in range(args.count):
                    started = time.perf_counter()
                    response = client.post('/payments')
                    expected = 500 if mode in ('db_timeout', 'unhandled_exception') else 200
                    if response.status_code != expected:
                        raise RuntimeError('Unexpected demo status; check the demo service.')
                    stage['requests'].append({'event_id': response.headers['x-tracely-event-id'],
                        'request_id': response.headers['x-request-id'], 'status_code': response.status_code,
                        'client_latency_ms': round((time.perf_counter() - started) * 1000, 3)})
                    time.sleep(0.2)
                stage['ended_at'] = utc()
        finally:
            reset = client.post('/_demo/fault', headers=headers, json={'mode': 'none'})
            reset.raise_for_status()
            report['reset_at'] = reset.json()['changed_at']
        expected_count = 7 * args.count
        deadline = time.monotonic() + 10
        while True:
            totals = client.get('/health').json()['telemetry']
            if totals['delivered'] - baseline['delivered'] >= expected_count or time.monotonic() >= deadline:
                break
            time.sleep(0.2)
        report['telemetry'] = totals
        report['ended_at'] = utc()
        print(json.dumps(report, indent=2))
        if totals['dropped'] > baseline['dropped'] or totals['delivered'] - baseline['delivered'] < expected_count:
            raise RuntimeError('Telemetry was not fully delivered. Check API availability and ingestion key; inspect /health counters.')


if __name__ == '__main__':
    main()
