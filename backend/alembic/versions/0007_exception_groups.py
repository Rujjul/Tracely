"""Phase 8: index exception groups without altering existing event evidence."""
from alembic import op

revision = '0007_exception_groups'
down_revision = '0006_detector'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_events_exception_group', 'events',
                    ['project_id', 'service', 'fingerprint', 'received_at'])


def downgrade():
    op.drop_index('ix_events_exception_group', table_name='events')
