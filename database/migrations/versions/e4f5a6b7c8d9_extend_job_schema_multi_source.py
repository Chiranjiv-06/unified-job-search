"""extend_job_schema_multi_source

Revision ID: e4f5a6b7c8d9
Revises: 994e110ac5ee
Create Date: 2026-10-27 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = '994e110ac5ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: extend jobs table for multi-source ingestion."""
    op.add_column('jobs', sa.Column('employment_type', sa.String(length=50), nullable=True))
    op.add_column('jobs', sa.Column('company_url', sa.String(length=1000), nullable=True))
    op.add_column('jobs', sa.Column('external_id', sa.String(length=255), nullable=True))
    op.add_column('jobs', sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('jobs', sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('jobs', sa.Column('is_expired', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('jobs', sa.Column('import_status', sa.String(length=50), server_default='active', nullable=True))
    op.add_column('jobs', sa.Column('raw_metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))

    op.create_index(op.f('ix_jobs_external_id'), 'jobs', ['external_id'], unique=False)
    op.create_index(op.f('ix_jobs_employment_type'), 'jobs', ['employment_type'], unique=False)
    op.create_index(op.f('ix_jobs_is_expired'), 'jobs', ['is_expired'], unique=False)
    op.create_index('ix_jobs_source_external_id', 'jobs', ['source_platform', 'external_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jobs_source_external_id', table_name='jobs')
    op.drop_index(op.f('ix_jobs_is_expired'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_employment_type'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_external_id'), table_name='jobs')

    op.drop_column('jobs', 'raw_metadata')
    op.drop_column('jobs', 'import_status')
    op.drop_column('jobs', 'is_expired')
    op.drop_column('jobs', 'last_seen_at')
    op.drop_column('jobs', 'first_seen_at')
    op.drop_column('jobs', 'external_id')
    op.drop_column('jobs', 'company_url')
    op.drop_column('jobs', 'employment_type')
