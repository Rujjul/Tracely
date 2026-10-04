"""Phase 4 checkpoint 1: event storage schema only."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004_events'
down_revision = '0003_projects'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('event_type', sa.String(32), nullable=False),
        sa.Column('level', sa.String(32), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Double(), nullable=True),
        sa.Column('exception_type', sa.Text(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('fingerprint', sa.Text(), nullable=True),
        sa.UniqueConstraint('project_id', 'event_id', name='uq_events_project_event'))
    op.create_index('ix_events_project_received_at', 'events',
                    ['project_id', sa.text('received_at DESC')])
    op.create_index('ix_events_project_service_received_at', 'events',
                    ['project_id', 'service', sa.text('received_at DESC')])


def downgrade():
    op.drop_index('ix_events_project_service_received_at', table_name='events')
    op.drop_index('ix_events_project_received_at', table_name='events')
    op.drop_table('events')
