"""Phase 10 saved deterministic investigations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0009_investigations'
down_revision = '0008_dashboard'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('investigations',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('incident_id', sa.Uuid(), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('method', sa.String(32), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        *[sa.Column(name, JSONB(), nullable=False) for name in ('observations', 'hypotheses', 'suggested_checks', 'limitations')],
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_investigations_incident_created', 'investigations',
                    ['incident_id', sa.text('created_at DESC'), sa.text('id DESC')])


def downgrade():
    op.drop_table('investigations')
