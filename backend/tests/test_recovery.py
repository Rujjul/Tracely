import os
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import auth, recovery
from app.main import app
from test_auth import client, register, google_callback, ORIGIN, PASSWORD

NEW_PASSWORD = 'my replacement passphrase 456'


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setenv('SMTP_HOST', 'smtp.example.com')
    monkeypatch.setenv('SMTP_FROM', 'tracely@example.com')
    monkeypatch.setenv('SMTP_SECURITY', 'starttls')
    monkeypatch.setattr(recovery, 'send_reset_email', lambda email, token: sent.append((email, token)))
    return sent


def forgot(client, email='person@example.com'):
    return client.post('/api/v1/auth/forgot-password', headers=ORIGIN, json={'email': email})


def reset(client, token, password=NEW_PASSWORD):
    return client.post('/api/v1/auth/reset-password', headers=ORIGIN, json={'token': token, 'password': password})


def test_reset_hashes_token_revokes_sessions_and_is_single_use(client, outbox):
    register(client)
    session = client.cookies.get(auth.SESSION_COOKIE)
    assert forgot(client, 'PERSON@EXAMPLE.COM').status_code == 200
    recipient, token = outbox[0]
    assert recipient == 'person@example.com'
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        row = conn.execute('SELECT token_hash,expires_at-created_at FROM password_resets').fetchone()
        assert row[0] == auth.digest(token) and row[0] != token
        assert 895 < row[1].total_seconds() <= 905
        conn.execute("INSERT INTO auth_sessions(token_hash,user_id,expires_at,purpose,google_sub) SELECT %s,id,now()+interval '5 minutes','link','pending-google' FROM users", (auth.digest('link-token'),))
    assert reset(client, token, 'short').status_code == 422
    assert reset(client, token).status_code == 200
    assert reset(client, token).status_code == 400
    client.cookies.set(auth.SESSION_COOKIE, session, domain='127.0.0.1', path='/api/v1')
    assert client.get('/api/v1/auth/me').status_code == 401
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        assert conn.execute('SELECT count(*) FROM auth_sessions').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM password_resets').fetchone()[0] == 0
        assert auth.hasher.verify(conn.execute('SELECT password_hash FROM users').fetchone()[0], NEW_PASSWORD)
    for password, status in [(PASSWORD, 401), (NEW_PASSWORD, 200)]:
        assert client.post('/api/v1/auth/login', headers=ORIGIN, json={'email':recipient, 'password':password}).status_code == status


def test_requests_do_not_reveal_account_or_send_to_google_only(client, outbox, monkeypatch):
    register(client)
    known = forgot(client)
    assert forgot(client).json() == known.json()  # One email per minute per account.
    unknown = forgot(client, 'unknown@example.com')
    google_callback(client, monkeypatch)
    google = forgot(client, 'google@example.com')
    assert known.status_code == unknown.status_code == google.status_code == 200
    assert known.json() == unknown.json() == google.json()
    assert len(outbox) == 1
    assert outbox[0][1] not in known.text


def test_expired_replaced_and_forged_tokens_rejected(client, outbox):
    register(client)
    forgot(client)
    old = outbox[-1][1]
    with psycopg.connect(os.environ['DATABASE_URL']) as conn:
        conn.execute("UPDATE password_resets SET created_at=now()-interval '20 minutes',expires_at=now()-interval '1 second'")
    assert reset(client, old).status_code == 400
    forgot(client)
    assert reset(client, old).status_code == 400
    assert reset(client, 'a' * 43).status_code == 400
    assert reset(client, outbox[-1][1]).status_code == 200


def test_reset_origin_throttle_and_missing_email_configuration(client, outbox, monkeypatch):
    assert client.post('/api/v1/auth/forgot-password', json={'email':'person@example.com'}).status_code == 403
    assert client.post('/api/v1/auth/reset-password', json={'token':'a'*43, 'password':NEW_PASSWORD}).status_code == 403
    monkeypatch.delenv('SMTP_HOST')
    assert forgot(client).status_code == 503
    for _ in range(29):
        forgot(client)
    assert forgot(client).status_code == 429


def test_simultaneous_resets_only_one_succeeds(client, outbox):
    register(client)
    forgot(client)
    token = outbox[0][1]
    def attempt(_):
        with TestClient(app, base_url='http://127.0.0.1:8000') as other:
            return reset(other, token).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [200, 400]


def test_smtp_uses_tls_and_does_not_log_secrets(monkeypatch, caplog):
    for key, value in {'SMTP_HOST':'smtp.example.com','SMTP_FROM':'tracely@example.com',
                       'SMTP_USERNAME':'user','SMTP_PASSWORD':'private-password','SMTP_SECURITY':'starttls'}.items():
        monkeypatch.setenv(key, value)
    actions = []
    class SMTP:
        def __init__(self, host, port, **kwargs): assert host == 'smtp.example.com'
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def starttls(self, **kwargs): actions.append('tls')
        def login(self, user, password):
            assert actions == ['tls'] and password == 'private-password'
            actions.append('login')
        def send_message(self, message):
            assert message['To'] == 'person@example.com'
            assert '#reset_token=private-token' in message.get_content()
            actions.append('sent')
    monkeypatch.setattr(recovery.smtplib, 'SMTP', SMTP)
    recovery.send_reset_email('person@example.com', 'private-token')
    assert actions == ['tls', 'login', 'sent']
    def fail(*args, **kwargs): raise OSError('private-password private-token person@example.com')
    monkeypatch.setattr(recovery.smtplib, 'SMTP', fail)
    recovery.send_reset_email('person@example.com', 'private-token')
    assert 'could not be delivered' in caplog.text
    assert all(secret not in caplog.text for secret in ('private-password', 'private-token', 'person@example.com'))
