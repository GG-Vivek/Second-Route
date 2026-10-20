"""add the feedback tables

Revision ID: 0003_feedback_tables
Revises: 0002_phase3_market_intelligence
Create Date: 2026-10-20

Phase 4 (F4.1, F4.2): The overrides and outcomes tables. Both are
append-only: an override and an outcome are never updated or deleted.

This migration also repairs the revision chain. The RLS migration that
follows it was written against a "0002_overrides" revision that never
shipped, so `alembic upgrade head` failed before the tables existed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_feedback_tables"
down_revision: Union[str, None] = "0002_phase3_market_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the overrides and outcomes tables."""
    op.create_table(
        "overrides",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("chosen_channel", sa.String(length=40), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_overrides_decision_id", "overrides", ["decision_id"])
    op.create_index(
        "ix_overrides_decision_created", "overrides", ["decision_id", "created_at"]
    )

    op.create_table(
        "outcomes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
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
    op.create_index("ix_outcomes_unit_recorded", "outcomes", ["unit_id", "recorded_at"])
    op.create_index(
        "ix_outcomes_decision_recorded", "outcomes", ["decision_id", "recorded_at"]
    )


def downgrade() -> None:
    """Drop the overrides and outcomes tables."""
    op.drop_index("ix_outcomes_decision_recorded", table_name="outcomes")
    op.drop_index("ix_outcomes_unit_recorded", table_name="outcomes")
    op.drop_index("ix_outcomes_decision_id", table_name="outcomes")
    op.drop_index("ix_outcomes_unit_id", table_name="outcomes")
    op.drop_table("outcomes")
    op.drop_index("ix_overrides_decision_created", table_name="overrides")
    op.drop_index("ix_overrides_decision_id", table_name="overrides")
    op.drop_table("overrides")
