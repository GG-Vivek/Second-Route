"""create outcomes table

Revision ID: 0004_outcomes
Revises: 0003_merge_phase3_overrides
Create Date: 2026-10-20

Phase 4 (F4.2): outcome logging for disposed units.

Appendix B schema: outcomes(id, unit_id, decision_id, channel_taken,
sale_price, fees_actual, repair_cost_actual, logistics_actual,
days_to_disposition, final_status, recorded_at). Append-only.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_outcomes"
down_revision: Union[str, None] = "0003_merge_phase3_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create the outcomes table."""
    op.create_table(
        "outcomes",
        sa.Column("id", UUID, nullable=False),
        sa.Column("unit_id", UUID, nullable=False),
        sa.Column("decision_id", UUID, nullable=False),
        sa.Column("channel_taken", sa.String(length=40), nullable=False),
        sa.Column("sale_price", sa.Float(), nullable=False),
        sa.Column("fees_actual", sa.Float(), nullable=False),
        sa.Column("repair_cost_actual", sa.Float(), nullable=False),
        sa.Column("logistics_actual", sa.Float(), nullable=False),
        sa.Column("days_to_disposition", sa.Integer(), nullable=False),
        sa.Column("final_status", sa.String(length=30), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outcomes_unit_id", "outcomes", ["unit_id"])
    op.create_index("ix_outcomes_decision_id", "outcomes", ["decision_id"])
    op.create_index("ix_outcomes_recorded_at", "outcomes", ["recorded_at"])
    op.create_index("ix_outcomes_unit_recorded", "outcomes", ["unit_id", "recorded_at"])
    op.create_index("ix_outcomes_decision_recorded", "outcomes", ["decision_id", "recorded_at"])


def downgrade() -> None:
    """Drop the outcomes table."""
    op.drop_index("ix_outcomes_decision_recorded", table_name="outcomes")
    op.drop_index("ix_outcomes_unit_recorded", table_name="outcomes")
    op.drop_index("ix_outcomes_recorded_at", table_name="outcomes")
    op.drop_index("ix_outcomes_decision_id", table_name="outcomes")
    op.drop_index("ix_outcomes_unit_id", table_name="outcomes")
    op.drop_table("outcomes")
