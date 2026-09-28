"""Align authentication support tables with the UUID primary-key contract."""
from alembic import op
import sqlalchemy as sa

revision = '0002_auth_uuid_keys'
down_revision = '0001_accounts'
branch_labels = None
depends_on = None


def upgrade():
    for table, hash_column in [('auth_sessions', 'token_hash'), ('oauth_attempts', 'state_hash')]:
        # PostgreSQL fills existing rows without changing tokens or expiry times.
        op.add_column(table, sa.Column('id', sa.Uuid(), nullable=False,
                                      server_default=sa.text('gen_random_uuid()')))
        op.create_unique_constraint(f'{table}_{hash_column}_key', table, [hash_column])
        op.drop_constraint(f'{table}_pkey', table, type_='primary')
        op.create_primary_key(f'{table}_pkey', table, ['id'])


def downgrade():
    for table, hash_column in [('oauth_attempts', 'state_hash'), ('auth_sessions', 'token_hash')]:
        op.drop_constraint(f'{table}_pkey', table, type_='primary')
        op.create_primary_key(f'{table}_pkey', table, [hash_column])
        op.drop_constraint(f'{table}_{hash_column}_key', table, type_='unique')
        op.drop_column(table, 'id')
