"""add the calibration versions and the decision calibration version

Revision ID: 0008_calibration
Revises: 0007_regret_measurements
Create Date: 2026-10-20

Phase 4 (F4.6): Store the fitted recalibration versions, and record the
version in force on every decision. A recalibration is never applied
silently, so the earlier versions stay in the table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_calibration"
down_revision: Union[str, None] = "0007_regret_measurements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the calibration_versions table and the decision column."""
    op.create_table(
        "calibration_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.String(length=60), nullable=False),
        sa.Column("mapping_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ece_before", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ece_after", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bins", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index("ix_calibration_versions_org_id", "calibration_versions", ["org_id"])
    op.create_index(
        "ix_calibration_versions_created_at", "calibration_versions", ["created_at"]
    )
    op.create_index(
        "ix_calibration_versions_org_created",
        "calibration_versions",
        ["org_id", "created_at"],
    )

    op.add_column("decisions", sa.Column("calibration_version", sa.String(length=60)))
    op.create_index("ix_decisions_calibration_version", "decisions", ["calibration_version"])

    # The table carries org_id, so it gets the same tenant isolation as
    # the rest of the tenant-scoped tables.
    op.execute("ALTER TABLE calibration_versions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON calibration_versions
        USING (org_id = current_setting('app.current_org_id')::uuid)
        WITH CHECK (org_id = current_setting('app.current_org_id')::uuid)
        """
    )


def downgrade() -> None:
    """Drop the calibration_versions table and the decision column."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON calibration_versions")
    op.execute("ALTER TABLE calibration_versions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_decisions_calibration_version", table_name="decisions")
    op.drop_column("decisions", "calibration_version")
    op.drop_index("ix_calibration_versions_org_created", table_name="calibration_versions")
    op.drop_index("ix_calibration_versions_created_at", table_name="calibration_versions")
    op.drop_index("ix_calibration_versions_org_id", table_name="calibration_versions")
    op.drop_table("calibration_versions")
