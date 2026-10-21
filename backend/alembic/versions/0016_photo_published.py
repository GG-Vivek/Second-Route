"""say which photographs may be published

Revision ID: 0016_photo_published
Revises: 0015_shared_prices
Create Date: 2026-10-21

The shop window shows photographs. The inspector's own photographs are
not all of them: one of the four angles is a photograph of the label on
the bottom of the device, and the label carries the serial number.

The serial number is not on the window. It was not in the response
either, but it was in the picture.

A photograph now says whether it may be published. The default is yes,
because the photographs that already exist are the photographs the
inspection form takes and the operator's own application has always
shown all of them. The seed marks the photograph of the label as not
publishable, because that is the one that carries the serial.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_photo_published"
down_revision: Union[str, None] = "0015_shared_prices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Say which photographs may be published."""
    op.add_column(
        "photos",
        sa.Column(
            "published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    """Every photograph is publishable again."""
    op.drop_column("photos", "published")
