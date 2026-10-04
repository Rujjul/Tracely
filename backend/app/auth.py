"""Password and Google authentication with opaque, server-expiring cookies."""
import base64
import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import partial
from threading import Lock
from urllib.parse import urlencode
from uuid import uuid4

import httpx
import psycopg
from psycopg.rows import dict_row
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr, Field, field_validator

router = APIRouter(prefix='/api/v1/auth', tags=['authentication'])
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
SESSION_COOKIE = 'tracely_session'
LINK_COOKIE = 'tracely_link'
STATE_COOKIE = 'tracely_oauth'
limits = defaultdict(deque)
limit_lock = Lock()


def now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def frontend():
    return os.getenv('FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')


def db():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise HTTPException(503, 'Database is not configured')
    with psycopg.connect(url, row_factory=dict_row, connect_timeout=3) as connection:
        yield connection


def same_origin(request: Request):
    # JSON mutation endpoints require a trusted Origin, including login (login CSRF).
    allowed = {frontend(), *os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')}
    if request.headers.get('origin') not in {x.strip() for x in allowed}:
        raise HTTPException(403, 'Untrusted request origin')


def throttle(request: Request):
    key = request.client.host if request.client else 'unknown'
    stamp = time.monotonic()
    with limit_lock:
        for stale in list(limits):
            if not limits[stale] or limits[stale][-1] <= stamp - 300:
                del limits[stale]
        attempts = limits[key]
        while attempts and attempts[0] <= stamp - 300:
            attempts.popleft()
        if len(attempts) >= 30:
            raise HTTPException(429, 'Too many attempts. Try again in five minutes.', headers={'Retry-After': '300'})
        attempts.append(stamp)


mutations = [Depends(same_origin), Depends(throttle)]


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('email')
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Registration(Credentials):
    password: str = Field(min_length=12, max_length=128)


class LinkPassword(BaseModel):
    password: str = Field(min_length=1, max_length=128)


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded or dummy_hash, password) and encoded is not None
    except (VerificationError, InvalidHashError):
        return False


def cookie(response, name, value, seconds):
    # Login sessions also authorize project routes. Remove the old narrower cookie
    # when replacing a session so browsers cannot send two different login tokens.
    if name == SESSION_COOKIE:
        response.delete_cookie(name, path='/api/v1/auth')
    response.set_cookie(name, value, max_age=seconds, httponly=True,
                        secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
                        samesite='lax', path='/api/v1' if name == SESSION_COOKIE else '/api/v1/auth')


def clear_cookie(response, name):
    response.delete_cookie(name, path='/api/v1/auth')
    if name == SESSION_COOKIE:
        response.delete_cookie(name, path='/api/v1')


def issue_session(connection, request, response, user, purpose='login', subject=None):
    token = secrets.token_urlsafe(32)
    seconds = 1800 if purpose == 'login' else 300
    expiry = now() + timedelta(seconds=seconds)
    name = SESSION_COOKIE if purpose == 'login' else LINK_COOKIE
    old = request.cookies.get(name)
    if old:
        connection.execute('DELETE FROM auth_sessions WHERE token_hash = %s', (digest(old),))
    connection.execute('DELETE FROM auth_sessions WHERE expires_at <= now()')
    connection.execute('INSERT INTO auth_sessions (token_hash,user_id,expires_at,purpose,google_sub) VALUES (%s,%s,%s,%s,%s)',
                       (digest(token), user['id'], expiry, purpose, subject))
    cookie(response, name, token, seconds)
    return {'user': {'id': str(user['id']), 'email': user['email']}, 'expires_at': expiry.isoformat()}


@router.get('/config')
def config():
    return {'google_enabled': bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'))}


@router.post('/register', status_code=201, dependencies=mutations)
def register(body: Registration, request: Request, response: Response, connection=Depends(db)):
    user = {'id': uuid4(), 'email': str(body.email)}
    try:
        connection.execute('INSERT INTO users (id,email,password_hash) VALUES (%s,%s,%s)',
                           (user['id'], user['email'], hasher.hash(body.password)))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, 'An account already exists. Please sign in.') from None
    return issue_session(connection, request, response, user)


@router.post('/login', dependencies=mutations)
def login(body: Credentials, request: Request, response: Response, connection=Depends(db)):
    user = connection.execute('SELECT * FROM users WHERE email = %s', (str(body.email),)).fetchone()
    if not verify_password(user['password_hash'] if user else None, body.password):
        raise HTTPException(401, 'Email or password is incorrect')
    if hasher.check_needs_rehash(user['password_hash']):
        connection.execute('UPDATE users SET password_hash=%s WHERE id=%s', (hasher.hash(body.password), user['id']))
    return issue_session(connection, request, response, user)


@router.get('/me')
def me(request: Request, connection=Depends(db), response: Response = None):
    token = request.cookies.get(SESSION_COOKIE, '')
    row = connection.execute('''SELECT u.id,u.email,s.expires_at FROM auth_sessions s
        JOIN users u ON u.id=s.user_id WHERE s.token_hash=%s AND s.purpose='login'
        AND s.expires_at > now()''', (digest(token),)).fetchone()
    if not row:
        raise HTTPException(401, 'Please sign in')
    if response is not None:
        # Migrate existing browser cookies without extending the original expiry.
        cookie(response, SESSION_COOKIE, token, max(0, int((row['expires_at'] - now()).total_seconds())))
    return {'user': {'id': str(row['id']), 'email': row['email']}, 'expires_at': row['expires_at'].isoformat()}


@router.post('/logout', dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response, connection=Depends(db)):
    for name in (SESSION_COOKIE, LINK_COOKIE):
        connection.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (digest(request.cookies.get(name, '')),))
        clear_cookie(response, name)
    return {'status': 'signed_out'}


def callback_url():
    return os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:8000/api/v1/auth/google/callback')


@router.get('/google/start', dependencies=[Depends(throttle)])
def google_start(connection=Depends(db)):
    if not config()['google_enabled']:
        raise HTTPException(503, 'Google sign-in is not configured yet')
    state, nonce, verifier = [secrets.token_urlsafe(32) for _ in range(3)]
    connection.execute('DELETE FROM oauth_attempts WHERE expires_at <= now()')
    connection.execute('INSERT INTO oauth_attempts (state_hash,nonce,verifier,expires_at) VALUES (%s,%s,%s,%s)',
                       (digest(state), nonce, verifier, now()+timedelta(minutes=5)))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    response = RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': os.environ['GOOGLE_CLIENT_ID'], 'redirect_uri': callback_url(),
        'response_type': 'code', 'scope': 'openid email profile', 'state': state,
        'nonce': nonce, 'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account'}))
    cookie(response, STATE_COOKIE, state, 300)
    return response


def google_identity(code, attempt):
    with httpx.Client(timeout=10) as client:
        result = client.post('https://oauth2.googleapis.com/token', data={
            'code': code, 'client_id': os.environ['GOOGLE_CLIENT_ID'],
            'client_secret': os.environ['GOOGLE_CLIENT_SECRET'], 'redirect_uri': callback_url(),
            'grant_type': 'authorization_code', 'code_verifier': attempt['verifier']})
        result.raise_for_status()
    claims = id_token.verify_oauth2_token(result.json()['id_token'], partial(GoogleRequest(), timeout=10), os.environ['GOOGLE_CLIENT_ID'])
    if not claims.get('email_verified') or not claims.get('sub') or not secrets.compare_digest(claims.get('nonce', ''), attempt['nonce']):
        raise ValueError('Invalid identity claims')
    # Reuse email validation without accepting arbitrary provider profile fields.
    email = Credentials(email=claims['email'], password='unused').email
    return {'email': str(email), 'sub': claims['sub']}


@router.get('/google/callback')
def google_callback(request: Request, state: str = '', code: str = '', error: str = '', connection=Depends(db)):
    failure = RedirectResponse(frontend() + '/?auth=google_error', status_code=303)
    clear_cookie(failure, STATE_COOKIE)
    browser_state = request.cookies.get(STATE_COOKIE, '')
    if not state or not browser_state or not secrets.compare_digest(state, browser_state):
        return failure
    attempt = connection.execute('DELETE FROM oauth_attempts WHERE state_hash=%s AND expires_at>now() RETURNING *', (digest(state),)).fetchone()
    connection.commit()  # Consume the browser-bound state even when Google fails.
    if not attempt or error or not code:
        return failure
    try:
        identity = google_identity(code, attempt)
    except Exception:
        # Never expose codes, provider tokens, secrets or provider error details.
        return failure
    response = RedirectResponse(frontend(), status_code=303)
    clear_cookie(response, STATE_COOKIE)
    user = connection.execute('SELECT * FROM users WHERE google_sub=%s', (identity['sub'],)).fetchone()
    if not user:
        user = connection.execute('SELECT * FROM users WHERE email=%s', (identity['email'],)).fetchone()
        if user:
            if not user['password_hash'] or user['google_sub']:
                return failure
            response = RedirectResponse(frontend() + '/?auth=link', status_code=303)
            clear_cookie(response, STATE_COOKIE)
            issue_session(connection, request, response, user, 'link', identity['sub'])
            return response
        user = {'id': uuid4(), 'email': identity['email']}
        try:
            connection.execute('INSERT INTO users(id,email,google_sub) VALUES (%s,%s,%s)',
                               (user['id'], user['email'], identity['sub']))
        except psycopg.errors.UniqueViolation:
            connection.rollback()
            return failure
    issue_session(connection, request, response, user)
    return response


@router.post('/google/link', dependencies=mutations)
def google_link(body: LinkPassword, request: Request, response: Response, connection=Depends(db)):
    token_hash = digest(request.cookies.get(LINK_COOKIE, ''))
    row = connection.execute('''SELECT s.google_sub AS pending_sub,u.* FROM auth_sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token_hash=%s AND s.purpose='link' AND s.expires_at>now() FOR UPDATE OF s,u''', (token_hash,)).fetchone()
    if not row:
        raise HTTPException(401, 'Link request expired. Start Google sign-in again.')
    if not verify_password(row['password_hash'], body.password):
        raise HTTPException(401, 'Password is incorrect')
    if row['google_sub'] and row['google_sub'] != row['pending_sub']:
        raise HTTPException(409, 'This account already has a different Google identity')
    try:
        connection.execute('UPDATE users SET google_sub=%s WHERE id=%s', (row['pending_sub'], row['id']))
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, 'Google identity is already linked') from None
    connection.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (token_hash,))
    clear_cookie(response, LINK_COOKIE)
    return issue_session(connection, request, response, row)
