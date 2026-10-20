"""add regret_measurements

Revision ID: 0006_regret_measurements
Revises: 0005_backtest_runs
Create Date: 2026-10-20

Phase 4 (F4.5): Store the regret of the recorded dispositions. Every row
carries a regret_kind so an observed regret is never confused with an
estimated one.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_regret_measurements"
down_revision: Union[str, None] = "0005_backtest_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the regret_measurements table."""
    op.create_table(
        "regret_measurements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("outcome_id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("channel_taken", sa.String(length=40), nullable=False),
        sa.Column("best_channel", sa.String(length=40), nullable=False),
        sa.Column("realized_net", sa.Float(), nullable=False),
        sa.Column("best_net", sa.Float(), nullable=False),
        sa.Column("regret", sa.Float(), nullable=False),
        sa.Column("regret_kind", sa.String(length=20), nullable=False),
        sa.Column("method", sa.String(length=60), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outcome_id"], ["outcomes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regret_measurements_org_id", "regret_measurements", ["org_id"]
    )
    op.create_index(
        "ix_regret_measurements_unit_id", "regret_measurements", ["unit_id"]
    )
    op.create_index(
        "ix_regret_measurements_outcome_id", "regret_measurements", ["outcome_id"]
    )
    op.create_index(
        "ix_regret_measurements_decision_id", "regret_measurements", ["decision_id"]
    )
    op.create_index(
        "ix_regret_measurements_regret_kind", "regret_measurements", ["regret_kind"]
    )
    op.create_index(
        "ix_regret_measurements_created_at", "regret_measurements", ["created_at"]
    )
    op.create_index(
        "ix_regret_measurements_unit_kind",
        "regret_measurements",
        ["unit_id", "regret_kind"],
    )
    op.create_index(
        "ix_regret_measurements_org_created",
        "regret_measurements",
        ["org_id", "created_at"],
    )

    # The table carries org_id, so it gets the same tenant isolation as
    # the rest of the tenant-scoped tables.
    op.execute("ALTER TABLE regret_measurements ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON regret_measurements
        USING (org_id = current_setting('app.current_org_id')::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id')::uuid)
        """
    )


def downgrade() -> None:
    """Drop the regret_measurements table."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON regret_measurements")
    op.execute("ALTER TABLE regret_measurements DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_regret_measurements_org_created", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_unit_kind", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_created_at", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_regret_kind", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_decision_id", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_outcome_id", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_unit_id", table_name="regret_measurements")
    op.drop_index("ix_regret_measurements_org_id", table_name="regret_measurements")
    op.drop_table("regret_measurements")
