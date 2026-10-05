"""Single-use, expiring password recovery tokens."""
from alembic import op
import sqlalchemy as sa

revision = '0005_password_resets'
down_revision = '0004_events'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('password_resets',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('password_resets')
