"""merge the phase 3 and overrides migration lines

Revision ID: 0003_merge_phase3_overrides
Revises: 0002_phase3_market_intelligence, 0002_overrides
Create Date: 2026-10-20

Phase 5 integration: the Phase 3 market-intelligence line and the Phase 4
overrides line were both forked from ``0001_baseline`` while they were
being built in parallel, so the tree had two heads. This revision joins
them into one line.

It is a merge revision: it creates no tables and changes no columns. It
exists so that ``alembic upgrade head`` has a single, unambiguous
destination and ``alembic downgrade base`` has a single, unambiguous
reverse path.

The two heads are:

- ``0002_phase3_market_intelligence`` - the Phase 3 market, cost and
  component tables, on ``main``.
- ``0002_overrides`` - the Phase 4 override table, on
  ``feat/F4.1-override-with-reason``.

``0003_rls_policies`` follows this revision.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003_merge_phase3_overrides"
down_revision: Union[str, Sequence[str], None] = (
    "0002_phase3_market_intelligence",
    "0002_overrides",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join the two migration lines. Nothing to do."""
    pass


def downgrade() -> None:
    """Split the migration lines again. Nothing to do."""
    pass
