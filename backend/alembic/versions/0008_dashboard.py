"""Phase 9 incident pagination index."""
from alembic import op
import sqlalchemy as sa

revision = '0008_dashboard'
down_revision = '0007_exception_groups'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_incidents_project_started_id', 'incidents',
                    ['project_id', sa.text('started_at DESC'), sa.text('id DESC')])


def downgrade():
    op.drop_index('ix_incidents_project_started_id', table_name='incidents')
