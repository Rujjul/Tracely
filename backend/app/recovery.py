"""Email-based password recovery; plaintext tokens exist only in delivery."""
import logging
import os
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from app.auth import db, digest, frontend, hasher, mutations, now, clear_cookie, SESSION_COOKIE, LINK_COOKIE

router = APIRouter(prefix='/api/v1/auth', tags=['authentication'])
NOTICE = 'If an account with a password matches that email, a reset link will arrive shortly. Google-only accounts should use Continue with Google.'


class ForgotPassword(BaseModel):
    email: EmailStr = Field(max_length=254)


class ResetPassword(BaseModel):
    token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')
    password: str = Field(min_length=12, max_length=128)


def send_reset_email(recipient, token):
    message = EmailMessage()
    message['Subject'] = 'Reset your Tracely password'
    message['From'] = os.environ['SMTP_FROM']
    message['To'] = recipient
    # Fragments are not sent in page requests or Referer headers.
    message.set_content(f'Reset your Tracely password:\n\n{frontend()}/#reset_token={token}\n\n'
                        'This link expires in 15 minutes and can be used once. '
                        'If you did not request this, ignore this email. Your password has not changed.')
    try:
        mode = os.getenv('SMTP_SECURITY', 'starttls')
        port = int(os.getenv('SMTP_PORT', '465' if mode == 'ssl' else '587'))
        factory = smtplib.SMTP_SSL if mode == 'ssl' else smtplib.SMTP
        options = {'context': ssl.create_default_context()} if mode == 'ssl' else {}
        with factory(os.environ['SMTP_HOST'], port, timeout=10, **options) as smtp:
            if mode == 'starttls':
                smtp.starttls(context=ssl.create_default_context())
            if os.getenv('SMTP_USERNAME'):
                smtp.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            smtp.send_message(message)
    except Exception:
        # A background failure must not reveal account existence or credentials.
        logging.getLogger(__name__).error('Password reset email could not be delivered; check SMTP configuration.')


@router.post('/forgot-password', dependencies=mutations)
def forgot_password(body: ForgotPassword, tasks: BackgroundTasks, connection=Depends(db)):
    if not os.getenv('SMTP_HOST') or not os.getenv('SMTP_FROM') or os.getenv('SMTP_SECURITY', 'starttls') not in ('starttls', 'ssl'):
        raise HTTPException(503, 'Password reset email is not configured. Please contact support or use Google sign-in if already linked.')
    user = connection.execute('SELECT id,email,password_hash FROM users WHERE email=%s FOR UPDATE',
                              (str(body.email).lower(),)).fetchone()
    if user and user['password_hash']:
        recent = connection.execute("SELECT id FROM password_resets WHERE user_id=%s AND created_at > now() - interval '1 minute'", (user['id'],)).fetchone()
        if not recent:
            token = secrets.token_urlsafe(32)
            connection.execute('DELETE FROM password_resets WHERE user_id=%s', (user['id'],))
            connection.execute('INSERT INTO password_resets(id,user_id,token_hash,expires_at) VALUES (%s,%s,%s,%s)',
                               (uuid4(), user['id'], digest(token), now() + timedelta(minutes=15)))
            connection.commit()  # The emailed token must be usable before delivery starts.
            tasks.add_task(send_reset_email, user['email'], token)
    return {'message': NOTICE}


@router.post('/reset-password', dependencies=mutations)
def reset_password(body: ResetPassword, response: Response, connection=Depends(db)):
    # Lock users first, as in reset issuance and Google linking, to serialize recovery.
    user = connection.execute('''SELECT u.id FROM users u JOIN password_resets r ON r.user_id=u.id
        WHERE r.token_hash=%s FOR UPDATE OF u''', (digest(body.token),)).fetchone()
    if not user:
        raise HTTPException(400, 'This reset link is invalid or expired. Request a new link.')
    token = connection.execute('''DELETE FROM password_resets WHERE user_id=%s AND token_hash=%s
        AND expires_at>now() RETURNING id''', (user['id'], digest(body.token))).fetchone()
    if not token:
        raise HTTPException(400, 'This reset link is invalid or expired. Request a new link.')
    connection.execute('UPDATE users SET password_hash=%s WHERE id=%s', (hasher.hash(body.password), user['id']))
    connection.execute('DELETE FROM auth_sessions WHERE user_id=%s', (user['id'],))
    connection.commit()
    clear_cookie(response, SESSION_COOKIE)
    clear_cookie(response, LINK_COOKIE)
    return {'message': 'Password updated. Sign in with your new password. All previous sessions have been signed out.'}
