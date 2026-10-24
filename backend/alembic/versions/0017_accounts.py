"""sign-up accounts, and devices that have no battery

Revision ID: 0017_accounts
Revises: 0016_photo_published
Create Date: 2026-10-24

Two changes that the catalogue of mixed devices needs.

A person can now create an account. The account has a display name and a
password hash, which is never the password itself. Accounts made before this
migration have neither, and they keep signing in through the identity provider.

A refrigerator or a television has no battery, so an inspection of one has no
battery reading. The reading is nullable now. A missing reading is not a
battery at zero per cent: the grade model treats it as neutral.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_accounts"
down_revision: Union[str, None] = "0016_photo_published"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the account columns and allow an inspection with no battery reading."""
    op.add_column("users", sa.Column("display_name", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.alter_column(
        "inspections",
        "battery_health_pct",
        existing_type=sa.String(10),
        nullable=True,
    )


def downgrade() -> None:
    """Remove the account columns.

    Inspections without a battery reading are given a reading of zero first,
    because the column cannot be made non-null while it holds nulls. That is
    lossy, and it is the reason this is only a rollback for a development
    database.
    """
    op.execute("UPDATE inspections SET battery_health_pct = '0' WHERE battery_health_pct IS NULL")
    op.alter_column(
        "inspections",
        "battery_health_pct",
        existing_type=sa.String(10),
        nullable=False,
    )
    op.drop_column("users", "password_hash")
    op.drop_column("users", "display_name")
