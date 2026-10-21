"""make the policies of the last two tables bind

Revision ID: 0013_force_rls
Revises: 0012_enum_values
Create Date: 2026-10-21

Two tables were given a tenant-isolation policy without the clause that
makes it bind. A policy only applies to the owner of the table when
``FORCE ROW LEVEL SECURITY`` is set, and the application role owns every
table, because it is the role the migrations run as. The two policies were
therefore never evaluated.

The result was that one organisation could read another organisation's
calibration versions and regret measurements, and could write to them.
The clearest symptom was that recalibrating the calibration deactivated
every other organisation's active version, because the code that looks for
the other active versions was not restricted to one tenant.

The policies are also rewritten to fail closed. They read the setting
with the ``missing_ok`` flag and cast it through ``NULLIF``, so a
connection with no organisation set sees no rows rather than raising. The
0004 migration says as much, and these two were written without it.

A migration cannot remove a value from a native enum, and a policy
cannot be weakened by accident, so the old policies are dropped and
replaced rather than altered.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0013_force_rls"
down_revision: Union[str, None] = "0012_enum_values"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The tables whose policies did not bind.
TABLES = ("regret_measurements", "calibration_versions")


def upgrade() -> None:
    """Make the policies of these tables bind, and make them fail closed."""
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
            WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
            """
        )
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Put the policies back the way they were.

    That puts the isolation back to where it was, which is not a state
    worth going back to on purpose. The downgrade exists so that the
    migration can be reverted mechanically; the tables keep their data and
    their rows are still there.
    """
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (org_id = current_setting('app.current_org_id')::uuid)
            WITH CHECK (org_id = current_setting('app.current_org_id')::uuid)
            """
        )
