"""bring the schema in line with the models

Revision ID: 0011_schema_drift
Revises: 0010_decision_explanations
Create Date: 2026-10-20

Some columns were created as TEXT in the baseline migration, while the
models have always declared them as JSON. On SQLite the difference is
invisible - the type is only a hint and the driver hands the value back
the way it was stored. On PostgreSQL the difference is the whole
behaviour: a JSON column comes back as a dictionary and a TEXT column
comes back as a string.

Three columns were affected, and each of them broke an endpoint:

- inspections.functional_tests_json and inspections.accessories_json:
  creating an inspection wrote the row and then failed to read it back,
  because the API promises a dictionary and the database returned a
  string.
- audit_log.payload_json: the audit log returned its payload as a
  string, so the audit endpoints failed to serialise.

The other changes here are the ones the models already expected and the
baseline did not have: a longer actor, a longer entity, an entity id
that may be empty, and a creation time that is never missing.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_schema_drift"
down_revision: Union[str, None] = "0010_decision_explanations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bring the columns in line with the models."""
    # The JSON columns. The USING clause is what tells PostgreSQL how to
    # read the existing text as JSON.
    op.alter_column(
        "inspections",
        "functional_tests_json",
        type_=sa.JSON(),
        postgresql_using="functional_tests_json::json",
    )
    op.alter_column(
        "inspections",
        "accessories_json",
        type_=sa.JSON(),
        postgresql_using="accessories_json::json",
    )
    op.alter_column(
        "audit_log",
        "payload_json",
        type_=sa.JSON(),
        postgresql_using="payload_json::json",
    )

    # The EXIF flag is written as the string "true" or "false", which is
    # what the model declares and what the API sends. The baseline made
    # the column a boolean, so the two disagreed about the type.
    op.alter_column(
        "photos",
        "exif_stripped",
        type_=sa.String(length=10),
        existing_type=sa.Boolean(),
        postgresql_using="CASE WHEN exif_stripped THEN 'true' ELSE 'false' END",
    )

    # The audit log holds who did what. The actor is an email address and
    # the entity is a table name, so the columns the baseline gave them
    # were too short.
    op.alter_column("audit_log", "actor", type_=sa.String(length=255))
    op.alter_column("audit_log", "entity", type_=sa.String(length=100))
    op.alter_column("audit_log", "entity_id", existing_type=sa.String(length=100), nullable=True)

    # A user always has a creation time.
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.func.now(),
    )


def downgrade() -> None:
    """Put the columns back the way the baseline had them."""
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(),
        nullable=True,
        server_default=None,
    )
    op.alter_column("audit_log", "entity_id", existing_type=sa.String(length=100), nullable=False)
    op.alter_column("audit_log", "entity", type_=sa.String(length=60))
    op.alter_column(
        "photos",
        "exif_stripped",
        type_=sa.Boolean(),
        existing_type=sa.String(length=10),
        postgresql_using="exif_stripped = 'true'",
    )
    op.alter_column("audit_log", "actor", type_=sa.String(length=200))

    op.alter_column(
        "audit_log",
        "payload_json",
        type_=sa.Text(),
        postgresql_using="payload_json::text",
    )
    op.alter_column(
        "inspections",
        "accessories_json",
        type_=sa.Text(),
        postgresql_using="accessories_json::text",
    )
    op.alter_column(
        "inspections",
        "functional_tests_json",
        type_=sa.Text(),
        postgresql_using="functional_tests_json::text",
    )
