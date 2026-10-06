"""Phase 7 incident lifecycle and durable detector evaluations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0006_detector'
down_revision = '0005_password_resets'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('incidents',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('incident_type', sa.String(64), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False),
        sa.Column('detector_version', sa.String(64), nullable=False),
        sa.Column('thresholds', JSONB(), nullable=False),
        sa.CheckConstraint("status IN ('active','resolved')", name='incident_status_valid'),
        sa.CheckConstraint("(status='active' AND resolved_at IS NULL) OR (status='resolved' AND resolved_at IS NOT NULL)", name='incident_resolution_valid'),
        sa.CheckConstraint('failure_count >= 0 AND request_count >= failure_count', name='incident_counts_valid'))
    op.create_index('uq_incidents_active', 'incidents', ['project_id','service','incident_type'],
                    unique=True, postgresql_where=sa.text("status='active'"))
    op.create_index('ix_incidents_project_status', 'incidents', ['project_id','status'])
    op.create_table('detector_states',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('service', sa.String(255), nullable=False),
        sa.Column('bad_streak', sa.Integer(), nullable=False),
        sa.Column('healthy_streak', sa.Integer(), nullable=False),
        sa.Column('first_failure_at', sa.DateTime(timezone=True)),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluation_status', sa.String(32), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False),
        sa.Column('detector_version', sa.String(64), nullable=False),
        sa.Column('thresholds', JSONB(), nullable=False),
        sa.UniqueConstraint('project_id','service', name='uq_detector_project_service'),
        sa.CheckConstraint("evaluation_status IN ('breaching','healthy','neutral','insufficient_data')", name='detector_status_valid'),
        sa.CheckConstraint('bad_streak >= 0 AND healthy_streak >= 0 AND failure_count >= 0 AND request_count >= failure_count', name='detector_counts_valid'))


def downgrade():
    op.drop_table('detector_states')
    op.drop_table('incidents')
