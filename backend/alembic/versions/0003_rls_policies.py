"""add RLS policies for tenant isolation

Revision ID: 0003_rls_policies
Revises: 0003_feedback_tables
Create Date: 2026-10-20

Phase 5 (F5.2): PostgreSQL Row-Level Security policies for tenant isolation.

Each table with org_id gets an RLS policy that filters rows by the
current_org_id setting. The app.current_org_id is set via a GUC
(SET LOCAL app.current_org_id = '<uuid>') at the start of each request.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_rls_policies"
down_revision: Union[str, None] = "0003_feedback_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enable_rls(table: str) -> None:
    """Enable RLS on a table."""
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def _create_policy(table: str, name: str, using: str, with_check: str = None) -> None:
    """Create an RLS policy."""
    check_clause = f"WITH CHECK ({with_check})" if with_check else ""
    op.execute(
        f"CREATE POLICY {name} ON {table} "
        f"USING ({using}) {check_clause}"
    )


def _drop_policies(table: str) -> None:
    """Drop all policies on a table."""
    op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


# Tables that carry org_id directly, so their policy is a plain comparison.
RLS_TABLES = [
    "units",
    "decisions",
    "audit_log",
    "cost_tables",
    "price_observations",
]

# Tables that reach org_id through another table, so their policy needs a
# join. The overrides and outcomes tables were written in Phase 4, before
# every table carried org_id.
RLS_JOIN_TABLES = ["overrides", "outcomes"]


def upgrade() -> None:
    """Create RLS policies for all tables with org_id."""

    # Helper to get current org_id from GUC
    # Current org_id is set via: SET LOCAL app.current_org_id = '<uuid>'
    # We use current_setting('app.current_org_id')::uuid to get it

    for table in RLS_TABLES:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create policy: users can only see rows where org_id = current_org_id
        # For tables with org_id column directly
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (org_id = current_setting('app.current_org_id')::uuid)
            WITH CHECK (org_id = current_setting('app.current_org_id')::uuid)
            """
        )

    for table in RLS_JOIN_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Special case: overrides table has org_id through decision
    # The overrides table has decision_id, and decisions have org_id
    # We need a join for the USING clause
    op.execute("""
        CREATE POLICY tenant_isolation ON overrides
        USING (
            decision_id IN (
                SELECT id FROM decisions
                WHERE org_id = current_setting('app.current_org_id')::uuid
            )
        )
        WITH CHECK (
            decision_id IN (
                SELECT id FROM decisions
                WHERE org_id = current_setting('app.current_org_id')::uuid
            )
        )
    """)

    # outcomes table has unit_id and decision_id, both have org_id
    # Use unit_id to filter by org
    op.execute("""
        CREATE POLICY tenant_isolation ON outcomes
        USING (
            unit_id IN (
                SELECT id FROM units
                WHERE org_id = current_setting('app.current_org_id')::uuid
            )
        )
        WITH CHECK (
            unit_id IN (
                SELECT id FROM units
                WHERE org_id = current_setting('app.current_org_id')::uuid
            )
        )
    """)


def downgrade() -> None:
    """Drop RLS policies."""
    for table in RLS_TABLES + RLS_JOIN_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
