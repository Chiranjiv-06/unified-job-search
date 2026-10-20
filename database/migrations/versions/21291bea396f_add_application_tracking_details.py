"""add_application_tracking_details

Revision ID: 21291bea396f
Revises: b299cddee80c
Create Date: 2026-10-20 13:57:41.314962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21291bea396f'
down_revision: Union[str, Sequence[str], None] = 'b299cddee80c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('applications', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('applications', sa.Column('recruiter_contact', sa.String(length=255), nullable=True))
    op.add_column('applications', sa.Column('interview_details', sa.String(length=500), nullable=True))
    op.add_column('applications', sa.Column('resume_version', sa.String(length=100), nullable=True))
    op.add_column('applications', sa.Column('timeline_events', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('applications', 'timeline_events')
    op.drop_column('applications', 'resume_version')
    op.drop_column('applications', 'interview_details')
    op.drop_column('applications', 'recruiter_contact')
    op.drop_column('applications', 'notes')

