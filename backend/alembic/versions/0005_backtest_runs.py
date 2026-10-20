"""add backtest_runs

Revision ID: 0005_backtest_runs
Revises: 0004_offline_inspection
Create Date: 2026-10-20

Phase 5 (F5.6): Store the backtest reports so the result can be shown and
reproduced. A backtest records the baseline it compared against and the
seed and sample count of its interval, so the same report can be rebuilt.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_backtest_runs"
down_revision: Union[str, None] = "0004_offline_inspection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the backtest_runs table."""
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("baseline_name", sa.String(length=60), nullable=False),
        sa.Column("baseline_channel", sa.String(length=40), nullable=True),
        sa.Column("window_start", sa.DateTime(), nullable=True),
        sa.Column("window_end", sa.DateTime(), nullable=True),
        sa.Column("decision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mean_difference", sa.Float(), nullable=True),
        sa.Column("ci_lower", sa.Float(), nullable=True),
        sa.Column("ci_upper", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.95"),
        sa.Column(
            "method",
            sa.String(length=60),
            nullable=False,
            server_default="paired-bootstrap-percentile",
        ),
        sa.Column("samples", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("seed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backtest_runs_org_id", "backtest_runs", ["org_id"])
    op.create_index("ix_backtest_runs_created_at", "backtest_runs", ["created_at"])
    op.create_index(
        "ix_backtest_runs_org_created", "backtest_runs", ["org_id", "created_at"]
    )


def downgrade() -> None:
    """Drop the backtest_runs table."""
    op.drop_index("ix_backtest_runs_org_created", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_created_at", table_name="backtest_runs")
    op.drop_index("ix_backtest_runs_org_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
