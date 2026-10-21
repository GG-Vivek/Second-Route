"""let the price observations be shared

Revision ID: 0015_shared_prices
Revises: 0014_unit_notes
Create Date: 2026-10-21

A price observation is what a market said about a model on a day. It is
not one organisation's data: the price of a laptop is the price of a
laptop, and every tenant that sells the same model gets the same
observation.

The policy treated them as tenant data, so a row with no organisation
was refused. That left two things wrong. The observations could only
ever be written for one organisation, and the price source, which reads
the cell for a model without asking whose observation it is, could only
ever see that one organisation's rows.

The policy now allows a row with no organisation, the way the audit log
already does. A tenant's own observations are still its own, and a
tenant cannot write a shared one: the shared rows are written by the
seeder, and the column is not something a request can name.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0015_shared_prices"
down_revision: Union[str, None] = "0014_unit_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The setting the policies read, the same way the first migration reads
#: it: with the flag, so that a connection with no organisation set sees
#: no rows rather than raising.
CURRENT_ORG = "NULLIF(current_setting('app.current_org_id', true), '')::uuid"

#: A row with no organisation is a shared record.
SHARED = "(org_id IS NULL OR org_id = {org})".format(org=CURRENT_ORG)


def upgrade() -> None:
    """Let a price observation belong to no organisation."""
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON price_observations")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON price_observations
        USING ({SHARED})
        WITH CHECK ({SHARED})
        """
    )


def downgrade() -> None:
    """Put the policy back the way it was.

    The shared observations are still there afterwards; they would simply
    be invisible to every organisation, because the policy would refuse
    them.
    """
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON price_observations")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation ON price_observations
        USING (org_id = {CURRENT_ORG})
        WITH CHECK (org_id = {CURRENT_ORG})
        """
    )
