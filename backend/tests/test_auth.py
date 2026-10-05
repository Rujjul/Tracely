"""Integration tests use a disposable schema in the configured PostgreSQL database."""
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlencode
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from psycopg import sql

load_dotenv(Path(__file__).resolve().parents[2] / '.env')
from app import auth
from app.main import app

ORIGIN = {'origin': 'http://127.0.0.1:5173'}
PASSWORD = 'a long test passphrase 123'


@pytest.fixture()
def client(monkeypatch):
    original = os.environ['DATABASE_URL']
    schema = 'test_auth_' + uuid4().hex
    with psycopg.connect(original) as connection:
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    separator = '&' if '?' in original else '?'
    monkeypatch.setenv('DATABASE_URL', original + separator + urlencode({'options': '-csearch_path=' + schema}))
    monkeypatch.setenv('FRONTEND_URL', 'http://127.0.0.1:5173')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    auth.limits.clear()
    try:
        command.upgrade(Config('alembic.ini'), 'head')
        with TestClient(app, base_url='http://127.0.0.1:8000', follow_redirects=False) as test_client:
            yield test_client
    finally:
        with psycopg.connect(original) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def register(client, email='person@example.com'):
    return client.post('/api/v1/auth/register', headers=ORIGIN, json={'email': email, 'password': PASSWORD})


def google_callback(client, monkeypatch, email='google@example.com', subject='google-user-1'):
    start = client.get('/api/v1/auth/google/start')
    assert start.status_code == 307
    params = parse_qs(urlparse(start.headers['location']).query)
    assert params['code_challenge_method'] == ['S256']
    monkeypatch.setattr(auth, 'google_identity', lambda code, attempt: {'email': email, 'sub': subject})
    return client.get('/api/v1/auth/google/callback', params={'state': params['state'][0], 'code': 'test-code'})


def test_register_hash_cookie_and_duplicate(client):
    result = register(client, 'Person@Example.com')
    assert result.status_code == 201
    assert result.json()['user']['email'] == 'person@example.com'
    lifetime = datetime.fromisoformat(result.json()['expires_at']) - datetime.now(timezone.utc)
    assert 1790 < lifetime.total_seconds() <= 1800
    assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=lax' in result.headers['set-cookie']
    assert 'Max-Age=1800' in result.headers['set-cookie']
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        encoded = connection.execute('SELECT password_hash FROM users').fetchone()[0]
        assert encoded.startswith('$argon2id$') and auth.hasher.verify(encoded, PASSWORD)
        stored_token = connection.execute('SELECT token_hash FROM auth_sessions').fetchone()[0]
        assert stored_token == auth.digest(client.cookies.get(auth.SESSION_COOKIE))
    assert register(client).status_code == 409
    assert client.get('/api/v1/auth/me').status_code == 200


def test_login_logout_revocation_expiry(client):
    assert client.get('/api/v1/auth/me').status_code == 401
    register(client)
    old_token = client.cookies.get(auth.SESSION_COOKIE)
    assert client.post('/api/v1/auth/logout', headers=ORIGIN).status_code == 200
    client.cookies.set(auth.SESSION_COOKIE, old_token, domain='127.0.0.1', path='/api/v1/auth')
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/login', headers=ORIGIN, json={'email':'person@example.com','password':'wrong'}).status_code == 401
    assert client.post('/api/v1/auth/login', headers=ORIGIN, json={'email':'PERSON@example.com','password':PASSWORD}).status_code == 200
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        connection.execute("UPDATE auth_sessions SET expires_at = now() - interval '1 second'")
    assert client.get('/api/v1/auth/me').status_code == 401


def test_origin_and_validation(client):
    assert client.post('/api/v1/auth/register', json={'email':'person@example.com','password':PASSWORD}).status_code == 403
    assert client.post('/api/v1/auth/login', headers={'origin':'https://evil.example'}, json={'email':'person@example.com','password':PASSWORD}).status_code == 403
    assert client.post('/api/v1/auth/register', headers=ORIGIN, json={'email':'not-email','password':PASSWORD}).status_code == 422
    assert client.post('/api/v1/auth/register', headers=ORIGIN, json={'email':'person@example.com','password':'short'}).status_code == 422


def test_google_new_account_and_repeated_sign_in(client, monkeypatch):
    result = google_callback(client, monkeypatch)
    assert result.status_code == 303 and result.headers['location'] == auth.frontend()
    session = client.get('/api/v1/auth/me').json()
    assert session['user']['email'] == 'google@example.com'
    assert client.get('/api/v1/auth/me').json()['expires_at'] == session['expires_at']
    token = client.cookies.get(auth.SESSION_COOKIE)
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    client.cookies.set(auth.SESSION_COOKIE, token, domain='127.0.0.1', path='/api/v1')
    assert client.get('/api/v1/auth/me').status_code == 401
    google_callback(client, monkeypatch)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        assert connection.execute('SELECT count(*) FROM users').fetchone()[0] == 1


def test_google_provider_failure_does_not_log_credentials(client, monkeypatch, caplog):
    start = client.get('/api/v1/auth/google/start')
    state = parse_qs(urlparse(start.headers['location']).query)['state'][0]
    def failed_provider(*args):
        raise ValueError('private-provider-token')
    monkeypatch.setattr(auth, 'google_identity', failed_provider)
    response = client.get('/api/v1/auth/google/callback', params={'state': state, 'code': 'private-code'})
    assert response.headers['location'].endswith('google_error')
    assert 'verification failed (ValueError)' in caplog.text
    assert all(value not in caplog.text for value in ('private-provider-token', 'private-code', state))
    assert client.get('/api/v1/auth/me').status_code == 401


def test_google_link_requires_password_and_is_single_use(client, monkeypatch):
    register(client)
    client.post('/api/v1/auth/logout', headers=ORIGIN)
    result = google_callback(client, monkeypatch, email='person@example.com')
    assert result.headers['location'].endswith('?auth=link')
    assert client.get('/api/v1/auth/me').status_code == 401
    assert client.post('/api/v1/auth/google/link', headers=ORIGIN, json={'password':'wrong'}).status_code == 401
    pending_cookie = client.cookies.get(auth.LINK_COOKIE)
    assert client.post('/api/v1/auth/google/link', headers=ORIGIN, json={'password':PASSWORD}).status_code == 200
    assert client.get('/api/v1/auth/me').status_code == 200
    client.cookies.set(auth.LINK_COOKIE, pending_cookie, domain='127.0.0.1', path='/api/v1/auth')
    assert client.post('/api/v1/auth/google/link', headers=ORIGIN, json={'password':PASSWORD}).status_code == 401


def test_google_state_replay_and_denial(client, monkeypatch):
    def unexpected(*args):
        raise AssertionError('Provider must not be called for invalid state')
    monkeypatch.setattr(auth, 'google_identity', unexpected)
    response = client.get('/api/v1/auth/google/callback?state=forged&code=anything')
    assert response.headers['location'].endswith('google_error')
    start = client.get('/api/v1/auth/google/start')
    state = parse_qs(urlparse(start.headers['location']).query)['state'][0]
    response = client.get('/api/v1/auth/google/callback', params={'state':state,'error':'access_denied'})
    assert response.headers['location'].endswith('google_error')
    client.cookies.set(auth.STATE_COOKIE, state, domain='127.0.0.1', path='/api/v1/auth')
    response = client.get('/api/v1/auth/google/callback', params={'state':state,'code':'replay'})
    assert response.headers['location'].endswith('google_error')


def test_disabled_google_and_throttle(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_CLIENT_SECRET')
    assert client.get('/api/v1/auth/config').json()['google_enabled'] is False
    assert client.get('/api/v1/auth/google/start').status_code == 503
    for _ in range(29):
        client.post('/api/v1/auth/login', headers=ORIGIN, json={'email':'bad','password':'x'})
    assert client.post('/api/v1/auth/login', headers=ORIGIN, json={'email':'bad','password':'x'}).status_code == 429


def test_provider_claims_rejected(monkeypatch):
    class FakeResponse:
        def raise_for_status(self): pass
        def json(self): return {'id_token':'test-token'}
    monkeypatch.setattr(auth.httpx.Client, 'post', lambda *args, **kwargs: FakeResponse())
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    for claims in [
        {'email':'a@example.com','sub':'1','email_verified':False,'nonce':'expected'},
        {'email':'a@example.com','sub':'1','email_verified':True,'nonce':'wrong'},
    ]:
        monkeypatch.setattr(auth.id_token, 'verify_oauth2_token', lambda *args, **kwargs: claims)
        with pytest.raises(ValueError):
            auth.google_identity('code', {'verifier':'v','nonce':'expected'})


def test_uuid_migration_preserves_existing_authentication(client):
    config = Config('alembic.ini')
    command.downgrade(config, '0001_accounts')
    assert register(client).status_code == 201
    start = client.get('/api/v1/auth/google/start')
    state = parse_qs(urlparse(start.headers['location']).query)['state'][0]
    token = client.cookies.get(auth.SESSION_COOKIE)
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        before = connection.execute('SELECT token_hash,user_id,expires_at FROM auth_sessions').fetchone()
    command.upgrade(config, 'head')
    assert client.get('/api/v1/auth/me').status_code == 200
    assert client.cookies.get(auth.SESSION_COOKIE) == token
    with psycopg.connect(os.environ['DATABASE_URL']) as connection:
        from uuid import UUID
        for table in ('users', 'auth_sessions', 'oauth_attempts'):
            identifier = connection.execute(sql.SQL('SELECT id FROM {}').format(sql.Identifier(table))).fetchone()[0]
            assert isinstance(identifier, UUID)
            key = connection.execute('''SELECT a.attname FROM pg_constraint c
                JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=ANY(c.conkey)
                WHERE c.conrelid=%s::regclass AND c.contype='p' ''', (table,)).fetchall()
            assert key == [('id',)]
        assert connection.execute('SELECT token_hash,user_id,expires_at FROM auth_sessions').fetchone() == before
        assert connection.execute('SELECT state_hash FROM oauth_attempts').fetchone()[0] == auth.digest(state)
        for table, column, value in [('auth_sessions', 'token_hash', auth.digest(token)),
                                      ('oauth_attempts', 'state_hash', auth.digest(state))]:
            with pytest.raises(psycopg.errors.UniqueViolation):
                with connection.transaction():
                    connection.execute(sql.SQL('UPDATE {} SET {}=%s WHERE {}=%s RETURNING id').format(
                        sql.Identifier(table), sql.Identifier(column), sql.Identifier(column)), (value, value))
                    if table == 'auth_sessions':
                        connection.execute('''INSERT INTO auth_sessions(token_hash,user_id,expires_at,purpose)
                            SELECT token_hash,user_id,expires_at,purpose FROM auth_sessions''')
                    else:
                        connection.execute('''INSERT INTO oauth_attempts(state_hash,nonce,verifier,expires_at)
                            SELECT state_hash,nonce,verifier,expires_at FROM oauth_attempts''')


def test_google_token_clock_tolerance(monkeypatch):
    import json
    import time
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from google.auth import crypt, jwt
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-secret')
    class Certificates:
        status = 200
        data = json.dumps({'test-key': public}).encode()
    monkeypatch.setattr(auth, 'GoogleRequest', lambda: lambda *args, **kwargs: Certificates())
    timestamp = int(time.time())
    claims = {'iss': 'https://accounts.google.com', 'aud': 'test-client', 'sub': 'subject',
              'email': 'google@example.com', 'email_verified': True, 'nonce': 'expected',
              'iat': timestamp + 2, 'exp': timestamp + 3600}
    class TokenResponse:
        def raise_for_status(self): pass
        def json(self): return {'id_token': jwt.encode(crypt.RSASigner.from_string(private, key_id='test-key'), claims).decode()}
    monkeypatch.setattr(auth.httpx.Client, 'post', lambda *args, **kwargs: TokenResponse())
    assert auth.google_identity('code', {'verifier': 'v', 'nonce': 'expected'})['sub'] == 'subject'
    for changes in ({'iat': timestamp + 60}, {'iat': timestamp - 3600, 'exp': timestamp - 60}, {'aud': 'other-client'}):
        original = claims.copy()
        claims.update(changes)
        with pytest.raises(ValueError):
            auth.google_identity('code', {'verifier': 'v', 'nonce': 'expected'})
        claims.clear()
        claims.update(original)
