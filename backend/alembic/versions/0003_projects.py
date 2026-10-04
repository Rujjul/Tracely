"""Owner-scoped projects and one active hashed ingestion key per project."""
from alembic import op
import sqlalchemy as sa

revision = '0003_projects'
down_revision = '0002_auth_uuid_keys'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('projects',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('owner_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_projects_owner', 'projects', ['owner_id'])
    op.create_table('project_keys',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key_prefix', sa.String(16), nullable=False),
        sa.Column('key_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)))
    op.create_index('ix_project_keys_project', 'project_keys', ['project_id'])
    op.create_index('uq_project_active_key', 'project_keys', ['project_id'], unique=True,
                    postgresql_where=sa.text('revoked_at IS NULL'))


def downgrade():
    op.drop_table('project_keys')
    op.drop_table('projects')
