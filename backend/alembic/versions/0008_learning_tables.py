"""add the learning loop tables

Revision ID: 0008_learning_tables
Revises: 0007_regret_measurements
Create Date: 2026-10-20

Phase 6 (F6.2, F6.3, F6.9): the tables the learning loop writes to.

- ``shadow_predictions`` records what a candidate model would have said
  next to what the active model said.
- ``promotion_records`` records a promotion decision and the metrics it
  was based on.
- ``expert_review_labels`` records a reviewer's agreement with a
  decision.

These three models existed before this revision but had no migration, so a
database built from the migrations was missing them and the endpoints that
write to them would have failed.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_learning_tables"
down_revision: Union[str, None] = "0007_regret_measurements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create the learning loop tables."""
    op.create_table(
        "shadow_predictions",
        sa.Column("id", UUID, nullable=False),
        sa.Column("decision_id", UUID, nullable=False),
        sa.Column("candidate_model_version", sa.String(length=60), nullable=False),
        sa.Column("active_model_version", sa.String(length=60), nullable=False),
        sa.Column("shadow_recommended_channel", sa.String(length=40), nullable=True),
        sa.Column("shadow_confidence", sa.Float(), nullable=True),
        sa.Column("shadow_candidates_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("active_recommended_channel", sa.String(length=40), nullable=True),
        sa.Column("active_confidence", sa.Float(), nullable=True),
        sa.Column("channel_match", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence_delta", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_predictions_decision_id", "shadow_predictions", ["decision_id"])
    op.create_index(
        "ix_shadow_predictions_candidate_model_version",
        "shadow_predictions",
        ["candidate_model_version"],
    )
    op.create_index(
        "ix_shadow_predictions_decision", "shadow_predictions", ["decision_id"]
    )
    op.create_index(
        "ix_shadow_predictions_candidate", "shadow_predictions", ["candidate_model_version"]
    )

    op.create_table(
        "promotion_records",
        sa.Column("id", UUID, nullable=False),
        sa.Column("candidate_model_version", sa.String(length=60), nullable=False),
        sa.Column("active_model_version", sa.String(length=60), nullable=False),
        sa.Column("promoted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("net_mae_candidate", sa.Float(), nullable=True),
        sa.Column("net_mae_active", sa.Float(), nullable=True),
        sa.Column("ece_candidate", sa.Float(), nullable=True),
        sa.Column("ece_active", sa.Float(), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promoted_by", sa.String(length=255), nullable=False, server_default="admin"),
        sa.Column("promoted_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_promotion_records_candidate_model_version",
        "promotion_records",
        ["candidate_model_version"],
    )
    op.create_index("ix_promotion_records_promoted", "promotion_records", ["promoted"])
    op.create_index(
        "ix_promotion_records_candidate", "promotion_records", ["candidate_model_version"]
    )

    op.create_table(
        "expert_review_labels",
        sa.Column("id", UUID, nullable=False),
        sa.Column("decision_id", UUID, nullable=False),
        sa.Column("reviewer_id", sa.String(length=255), nullable=False),
        sa.Column("agreement", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("suggested_channel", sa.String(length=40), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expert_review_labels_decision_id", "expert_review_labels", ["decision_id"])
    op.create_index(
        "ix_expert_review_labels_reviewer_id", "expert_review_labels", ["reviewer_id"]
    )
    op.create_index(
        "ix_expert_review_labels_decision", "expert_review_labels", ["decision_id"]
    )
    op.create_index(
        "ix_expert_review_labels_reviewer", "expert_review_labels", ["reviewer_id"]
    )


def downgrade() -> None:
    """Drop the learning loop tables."""
    op.drop_index("ix_expert_review_labels_reviewer", table_name="expert_review_labels")
    op.drop_index("ix_expert_review_labels_decision", table_name="expert_review_labels")
    op.drop_index("ix_expert_review_labels_reviewer_id", table_name="expert_review_labels")
    op.drop_index("ix_expert_review_labels_decision_id", table_name="expert_review_labels")
    op.drop_table("expert_review_labels")

    op.drop_index("ix_promotion_records_candidate", table_name="promotion_records")
    op.drop_index("ix_promotion_records_promoted", table_name="promotion_records")
    op.drop_index(
        "ix_promotion_records_candidate_model_version", table_name="promotion_records"
    )
    op.drop_table("promotion_records")

    op.drop_index("ix_shadow_predictions_candidate", table_name="shadow_predictions")
    op.drop_index("ix_shadow_predictions_decision", table_name="shadow_predictions")
    op.drop_index(
        "ix_shadow_predictions_candidate_model_version", table_name="shadow_predictions"
    )
    op.drop_index("ix_shadow_predictions_decision_id", table_name="shadow_predictions")
    op.drop_table("shadow_predictions")
