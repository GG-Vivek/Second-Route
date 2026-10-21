"""give the unit somewhere to keep the intake notes

Revision ID: 0014_unit_notes
Revises: 0013_force_rls
Create Date: 2026-10-21

The intake form asks for notes about the return. The only place notes
were kept was the inspection, and the inspection does not exist yet when
the return is logged, so the notes the operator typed were thrown away.

The notes belong on the unit: they are about the return, they are written
before anybody has inspected the device, and the next person to open the
unit should see them.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_unit_notes"
down_revision: Union[str, None] = "0013_force_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the notes column."""
    op.add_column("units", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    """Take the notes column away again."""
    op.drop_column("units", "notes")
