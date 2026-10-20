"""add the decision explanations

Revision ID: 0010_decision_explanations
Revises: 0009_learning_tables
Create Date: 2026-10-20

Phase 5 (F5.7): Store the explanations of a decision. The model is slow, so
the explanation is written once and read many times. Every row says
whether it was written by the model or by the template, and why.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_decision_explanations"
down_revision: Union[str, None] = "0009_learning_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the decision_explanations table."""
    op.create_table(
        "decision_explanations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=60), nullable=True),
        sa.Column("unseen_numbers", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_decision_explanations_decision_id", "decision_explanations", ["decision_id"]
    )
    op.create_index(
        "ix_decision_explanations_source", "decision_explanations", ["source"]
    )
    op.create_index(
        "ix_decision_explanations_created_at", "decision_explanations", ["created_at"]
    )
    op.create_index(
        "ix_decision_explanations_decision_created",
        "decision_explanations",
        ["decision_id", "created_at"],
    )


def downgrade() -> None:
    """Drop the decision_explanations table."""
    op.drop_index(
        "ix_decision_explanations_decision_created", table_name="decision_explanations"
    )
    op.drop_index("ix_decision_explanations_created_at", table_name="decision_explanations")
    op.drop_index("ix_decision_explanations_source", table_name="decision_explanations")
    op.drop_index(
        "ix_decision_explanations_decision_id", table_name="decision_explanations"
    )
    op.drop_table("decision_explanations")
