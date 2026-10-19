"""baseline: initial schema for Phase 0-2

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-20

Creates the full schema the walking skeleton needs:

* identity: organizations, users, skus, serial_prefixes
* intake: units, inspections, photos
* feedback: audit_log
* condition: condition_estimates
* pricing: price_observations
* costs: cost_tables
* decision: decisions

The ``organizations`` and ``users`` tables are created here because the
Phase 1 and Phase 2 tables reference them through foreign keys. Their
behaviour (authentication, roles, row-level security) arrives in Phase 5.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create the baseline schema."""
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("risk_profile", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "skus",
        sa.Column("id", UUID, nullable=False),
        sa.Column("family", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("year", sa.String(length=10), nullable=False),
        sa.Column("storage_gb", sa.String(length=50), nullable=False),
        sa.Column("ram_gb", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=50), nullable=False),
        sa.Column("region", sa.String(length=10), nullable=False),
        sa.Column("specs_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family",
            "model_name",
            "year",
            "storage_gb",
            "ram_gb",
            "color",
            "region",
            name="uq_sku_variant",
        ),
    )
    op.create_index("ix_skus_family", "skus", ["family"])
    op.create_index("ix_skus_family_model", "skus", ["family", "model_name"])

    op.create_table(
        "serial_prefixes",
        sa.Column("id", UUID, nullable=False),
        sa.Column("prefix", sa.String(length=50), nullable=False),
        sa.Column("sku_id", UUID, nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_serial_prefixes_prefix", "serial_prefixes", ["prefix"], unique=True)

    # ------------------------------------------------------------------
    # Intake
    # ------------------------------------------------------------------
    op.create_table(
        "units",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("sku_id", UUID, nullable=False),
        sa.Column("serial", sa.String(length=100), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column(
            "return_reason_code",
            sa.Enum(
                "BUYER_REMORSE",
                "DEFECTIVE",
                "NOT_AS_DESCRIBED",
                "NOLONGER_NEEDED",
                "DAMAGED_IN_TRANSIT",
                "IDENTIFICATION_ERROR",
                "OTHER",
                name="return_reason_code_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "order_channel",
            sa.Enum(
                "ONLINE",
                "RETAIL",
                "MARKETPLACE",
                name="order_channel_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "RECEIVED",
                "INSPECTED",
                "DECIDED",
                "DISPOSITIONED",
                name="unit_status_enum",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_units_org_status", "units", ["org_id", "status"])
    op.create_index("ix_units_received_at", "units", ["received_at"])
    op.create_index("ix_units_serial", "units", ["serial"])
    op.create_index("ix_units_sku_id", "units", ["sku_id"])
    op.create_index("ix_units_status", "units", ["status"])

    op.create_table(
        "inspections",
        sa.Column("id", UUID, nullable=False),
        sa.Column("unit_id", UUID, nullable=False),
        sa.Column("inspector_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("battery_health_pct", sa.String(length=10), nullable=False),
        sa.Column("battery_cycles", sa.String(length=20), nullable=True),
        sa.Column("cosmetic_grade", sa.String(length=20), nullable=False),
        sa.Column("functional_tests_json", sa.Text(), nullable=False),
        sa.Column("activation_lock", sa.String(length=20), nullable=False),
        sa.Column("accessories_json", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inspections_unit_id", "inspections", ["unit_id"])

    op.create_table(
        "photos",
        sa.Column("id", UUID, nullable=False),
        sa.Column("unit_id", UUID, nullable=False),
        sa.Column("inspection_id", UUID, nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("exif_stripped", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_photos_unit_id", "photos", ["unit_id"])
    op.create_index("ix_photos_inspection_id", "photos", ["inspection_id"])

    # ------------------------------------------------------------------
    # Feedback / audit
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("actor", sa.String(length=200), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # ------------------------------------------------------------------
    # Condition (Phase 2)
    # ------------------------------------------------------------------
    op.create_table(
        "condition_estimates",
        sa.Column("id", UUID, nullable=False),
        sa.Column("unit_id", UUID, nullable=False),
        sa.Column("grade_dist_json", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=60), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_condition_estimates_unit_created", "condition_estimates", ["unit_id", "created_at"]
    )

    # ------------------------------------------------------------------
    # Pricing (Phase 2)
    # ------------------------------------------------------------------
    op.create_table(
        "price_observations",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("sku_id", UUID, nullable=False),
        sa.Column("grade", sa.String(length=4), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sku_id",
            "grade",
            "channel",
            "price",
            "source",
            "observed_at",
            name="uq_price_observation_cell",
        ),
    )
    op.create_index(
        "ix_price_observations_cell", "price_observations", ["sku_id", "grade", "channel"]
    )
    op.create_index(
        "ix_price_observations_source_time", "price_observations", ["source", "observed_at"]
    )
    op.create_index("ix_price_observations_grade", "price_observations", ["grade"])
    op.create_index("ix_price_observations_channel", "price_observations", ["channel"])
    op.create_index("ix_price_observations_observed_at", "price_observations", ["observed_at"])
    op.create_index("ix_price_observations_is_synthetic", "price_observations", ["is_synthetic"])
    op.create_index("ix_price_observations_sku_id", "price_observations", ["sku_id"])
    op.create_index("ix_price_observations_org_id", "price_observations", ["org_id"])

    # ------------------------------------------------------------------
    # Costs (Phase 2)
    # ------------------------------------------------------------------
    op.create_table(
        "cost_tables",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "kind", "key", name="uq_cost_table_scope"),
    )
    op.create_index("ix_cost_tables_kind_key", "cost_tables", ["kind", "key"])
    op.create_index("ix_cost_tables_kind", "cost_tables", ["kind"])
    op.create_index("ix_cost_tables_key", "cost_tables", ["key"])
    op.create_index("ix_cost_tables_org_id", "cost_tables", ["org_id"])

    # ------------------------------------------------------------------
    # Decisions (Phase 2)
    # ------------------------------------------------------------------
    op.create_table(
        "decisions",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("unit_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("model_version", sa.String(length=60), nullable=False),
        sa.Column("risk_profile", sa.String(length=30), nullable=False),
        sa.Column("recommended_channel", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("fallback_channel", sa.String(length=40), nullable=True),
        sa.Column("candidates_json", sa.Text(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("flip_conditions_json", sa.Text(), nullable=False),
        sa.Column("data_freshness_json", sa.Text(), nullable=False),
        sa.Column("action_steps_json", sa.Text(), nullable=False),
        sa.Column("input_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot_json", sa.Text(), nullable=False),
        sa.Column("exploration_propensity", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decisions_unit_created", "decisions", ["unit_id", "created_at"])
    op.create_index("ix_decisions_recommended", "decisions", ["recommended_channel"])
    op.create_index("ix_decisions_unit_id", "decisions", ["unit_id"])
    op.create_index("ix_decisions_created_at", "decisions", ["created_at"])
    op.create_index("ix_decisions_input_snapshot_hash", "decisions", ["input_snapshot_hash"])
    op.create_index("ix_decisions_org_id", "decisions", ["org_id"])


def downgrade() -> None:
    """Drop the baseline schema."""
    op.drop_table("decisions")
    op.drop_table("cost_tables")
    op.drop_table("price_observations")
    op.drop_table("condition_estimates")
    op.drop_table("audit_log")
    op.drop_table("photos")
    op.drop_table("inspections")
    op.drop_table("units")
    op.drop_table("serial_prefixes")
    op.drop_table("skus")
    op.drop_table("users")
    op.drop_table("organizations")

    sa.Enum(name="unit_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="order_channel_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="return_reason_code_enum").drop(op.get_bind(), checkfirst=True)
