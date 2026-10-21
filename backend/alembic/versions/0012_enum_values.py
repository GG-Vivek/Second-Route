"""add the enum values the models declare

Revision ID: 0012_enum_values
Revises: 0011_schema_drift
Create Date: 2026-10-21

A native enum on PostgreSQL only holds the values it was created with. The
baseline created the three intake enums with the values it knew about at
the time, and the models have grown since. Every value that the model
declares and the database does not have is a write that fails.

Four return reasons, two order channels and four unit statuses were
missing, and the intake form offers all of them: logging a return for the
wrong item, marking a unit dispatched, and so on, all ended in a five
hundred.

The values that the baseline has and the models do not are left alone.
Nothing uses them, and a value that has been used cannot be taken away
from a native enum in any case.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0012_enum_values"
down_revision: Union[str, None] = "0011_schema_drift"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The values each enum is missing, by the name the model declares.
MISSING_VALUES: dict[str, tuple[str, ...]] = {
    "unit_status_enum": (
        "DISPATCHED",
        "SOLD",
        "RECYCLED",
        "DONATED",
    ),
    "return_reason_code_enum": (
        "WRONG_ITEM",
        "DAMAGED_IN_SHIPPING",
        "CHANGED_MIND",
        "BETTER_PRICE_FOUND",
        # The baseline spelled this one without the second underscore, so
        # the label the model declares has never existed in the database.
        "NO_LONGER_NEEDED",
    ),
    "order_channel_enum": (
        "B2B",
        "OTHER",
    ),
}


def upgrade() -> None:
    """Add the values the models declare and the database does not have."""
    # A new value cannot be used in the same transaction that adds it, so
    # this runs outside one.
    with op.get_context().autocommit_block():
        for name, values in MISSING_VALUES.items():
            for value in values:
                op.execute(f"ALTER TYPE {name} ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """The values stay.

    A native enum cannot lose a value: PostgreSQL has no way to remove one
    that a row might be using. Reverting this migration would break the
    rows that use the values it added.
    """
