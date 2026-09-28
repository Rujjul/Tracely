"""Phase 2 accounts and short-lived authentication state only."""
from alembic import op
import sqlalchemy as sa

revision = '0001_accounts'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('google_sub', sa.String(255), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('password_hash IS NOT NULL OR google_sub IS NOT NULL', name='user_has_identity'))
    op.create_table('auth_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('purpose', sa.String(16), nullable=False),
        sa.Column('google_sub', sa.String(255)))
    op.create_index('ix_auth_sessions_expires', 'auth_sessions', ['expires_at'])
    op.create_table('oauth_attempts',
        sa.Column('state_hash', sa.String(64), primary_key=True),
        sa.Column('nonce', sa.String(128), nullable=False),
        sa.Column('verifier', sa.String(128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('oauth_attempts')
    op.drop_table('auth_sessions')
    op.drop_table('users')
