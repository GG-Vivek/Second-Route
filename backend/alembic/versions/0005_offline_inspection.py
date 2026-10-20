"""add offline_created to inspections

Revision ID: 0005_offline_inspection
Revises: 0004_rls_policies
Create Date: 2026-10-20

Phase 5 (F5.5): Add offline_created flag to inspections for offline support.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_offline_inspection"
down_revision: Union[str, None] = "0004_rls_policies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add offline_created column to inspections table."""
    op.add_column(
        "inspections",
        sa.Column("offline_created", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Drop offline_created column from inspections table."""
    op.drop_column("inspections", "offline_created")
