"""create overrides table

Revision ID: 0002_overrides
Revises: 0001_baseline
Create Date: 2026-10-20

Phase 4 (F4.1): human overrides of decision recommendations.

Appendix B schema: overrides(id, decision_id, user_id, chosen_channel,
reason_text, created_at). Append-only: no update or delete path exists.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_overrides"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create the overrides table."""
    op.create_table(
        "overrides",
        sa.Column("id", UUID, nullable=False),
        sa.Column("decision_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("chosen_channel", sa.String(length=40), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_overrides_decision_id", "overrides", ["decision_id"])
    op.create_index("ix_overrides_user_id", "overrides", ["user_id"])
    op.create_index("ix_overrides_created_at", "overrides", ["created_at"])
    op.create_index(
        "ix_overrides_decision_created", "overrides", ["decision_id", "created_at"]
    )


def downgrade() -> None:
    """Drop the overrides table."""
    op.drop_index("ix_overrides_decision_created", table_name="overrides")
    op.drop_index("ix_overrides_created_at", table_name="overrides")
    op.drop_index("ix_overrides_user_id", table_name="overrides")
    op.drop_index("ix_overrides_decision_id", table_name="overrides")
    op.drop_table("overrides")
