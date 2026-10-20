"""add RLS policies for tenant isolation

Revision ID: 0005_rls_policies
Revises: 0004_outcomes
Create Date: 2026-10-20

Phase 5 (F5.2): PostgreSQL Row-Level Security policies for tenant isolation.

Each tenant-scoped table gets a policy that filters rows by the current
organisation. The organisation comes from the ``app.current_org_id``
setting, which the application sets per transaction with
``set_config('app.current_org_id', ..., true)``.

Two shapes of policy are needed:

- Tables that carry ``org_id`` themselves filter on it directly.
- Tables that belong to an organisation through a parent - an inspection
  belongs to a unit, an override belongs to a decision - filter through a
  subquery on that parent.

The setting is read with the ``missing_ok`` flag, so a connection that has
no organisation set sees no rows rather than raising an error. A query
without an organisation context therefore fails closed.

The ``users`` table is deliberately left out. A user is looked up by email
during login, before the organisation is known, so a policy on it would
make authentication impossible. The users table is not tenant data: it is
the mapping from a person to an organisation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_rls_policies"
down_revision: Union[str, None] = "0004_outcomes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The organisation the current transaction acts for. Read with the
#: ``missing_ok`` flag so an unset setting yields NULL, which matches no
#: rows, rather than raising. The empty string is turned into NULL the
#: same way, because an empty string is how the application says "no
#: organisation", and casting it to uuid would raise.
CURRENT_ORG = "NULLIF(current_setting('app.current_org_id', true), '')::uuid"

#: Tables whose rows carry ``org_id`` directly.
DIRECT_ORG_TABLES = [
    "units",
    "decisions",
    "audit_log",
    "cost_tables",
    "price_observations",
]

#: Tables that belong to an organisation through a parent table. The
#: value is the local column that points at the parent, and the parent's
#: table and organisation column.
JOINED_ORG_TABLES = [
    ("overrides", "decision_id", "decisions"),
    ("outcomes", "unit_id", "units"),
    ("inspections", "unit_id", "units"),
    ("photos", "unit_id", "units"),
]


#: Tables that also hold shared records: a row with no organisation
#: belongs to the whole catalogue rather than to one tenant. The audit log
#: holds one for every change to the shared SKU catalogue, and the
#: catalogue is not tenant data.
SHARED_OK_TABLES = [
    "audit_log",
]


def _enable_rls(table: str) -> None:
    """Turn on row-level security for a table.

    ``FORCE ROW LEVEL SECURITY`` is what makes the policy bind the table's
    owner. Without it, a connection that owns the table - which is what
    the application is, because it runs the migrations - carries the
    table owner exemption and sees every row, which would make the
    policies decorative.

    A superuser still bypasses row-level security, so the application must
    connect as a role that is not one.
    """
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _create_policy(table: str, using: str, with_check: str) -> None:
    """Create the tenant-isolation policy on a table."""
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON {table}
        USING ({using})
        WITH CHECK ({with_check})
        """
    )


def _direct_org_clause(allow_shared: bool = False) -> str:
    """The clause for a table that carries ``org_id``."""
    if allow_shared:
        # A row with no organisation is a shared record. Only the server
        # writes audit rows - there is no endpoint that inserts them - so
        # a tenant cannot forge one.
        return f"(org_id IS NULL OR org_id = {CURRENT_ORG})"
    return f"org_id = {CURRENT_ORG}"


def _joined_org_clause(column: str, parent: str) -> str:
    """The clause for a table that belongs to an org through a parent."""
    return f"""
        {column} IN (
            SELECT id FROM {parent} WHERE org_id = {CURRENT_ORG}
        )
    """


def upgrade() -> None:
    """Create the RLS policies for every tenant-scoped table."""
    for table in DIRECT_ORG_TABLES:
        _enable_rls(table)
        clause = _direct_org_clause(allow_shared=table in SHARED_OK_TABLES)
        _create_policy(table, clause, clause)

    for table, column, parent in JOINED_ORG_TABLES:
        _enable_rls(table)
        clause = _joined_org_clause(column, parent)
        _create_policy(table, clause, clause)


def downgrade() -> None:
    """Drop the RLS policies."""
    for table in DIRECT_ORG_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    for table, _column, _parent in JOINED_ORG_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
