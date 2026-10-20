"""phase3: market, component and demand intelligence

Revision ID: 0002_phase3_market_intelligence
Revises: 0001_baseline
Create Date: 2026-10-20

Creates the Phase 3 tables:

* import_files - the record of a partner sales import (F3.2)
* component_prices - the price of a recoverable component (F3.5)
* teardown_yields - how much of a component survives a teardown (F3.6)
* demand_signals - a demand observation for a SKU family (F3.7)
* launch_events - a known product launch (F3.8)
* decay_params - the fitted price rate for a family and grade (F3.8)
* source_health - the freshness and error count of a source (F3.9)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase3_market_intelligence"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Create the Phase 3 tables."""
    # ------------------------------------------------------------------
    # Partner imports (F3.2)
    # ------------------------------------------------------------------
    op.create_table(
        "import_files",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("rows_rejected", sa.Integer(), nullable=False),
        sa.Column("import_kind", sa.String(length=40), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "import_kind", "file_hash", name="uq_import_file_hash"
        ),
    )
    op.create_index("ix_import_files_file_hash", "import_files", ["file_hash"])
    op.create_index("ix_import_files_imported_at", "import_files", ["imported_at"])
    op.create_index("ix_import_files_org_id", "import_files", ["org_id"])
    op.create_index("ix_import_files_source", "import_files", ["source"])

    # ------------------------------------------------------------------
    # Component prices and teardown yields (F3.5, F3.6)
    # ------------------------------------------------------------------
    op.create_table(
        "component_prices",
        sa.Column("id", UUID, nullable=False),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column("component_type", sa.String(length=60), nullable=False),
        sa.Column("price_per_unit", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("confidence_weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "component_type", "source", "as_of", name="uq_component_price"
        ),
    )
    op.create_index("ix_component_prices_as_of", "component_prices", ["as_of"])
    op.create_index("ix_component_prices_component_type", "component_prices", ["component_type"])
    op.create_index("ix_component_prices_org_id", "component_prices", ["org_id"])

    op.create_table(
        "teardown_yields",
        sa.Column("id", UUID, nullable=False),
        sa.Column("component_type", sa.String(length=60), nullable=False),
        sa.Column("sku_family", sa.String(length=100), nullable=False),
        sa.Column("yield_ratio", sa.Float(), nullable=False),
        sa.Column("labor_hours", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "component_type",
            "sku_family",
            "source",
            "as_of",
            name="uq_teardown_yield",
        ),
    )
    op.create_index("ix_teardown_yields_component_type", "teardown_yields", ["component_type"])
    op.create_index("ix_teardown_yields_sku_family", "teardown_yields", ["sku_family"])

    # ------------------------------------------------------------------
    # Demand signals (F3.7)
    # ------------------------------------------------------------------
    op.create_table(
        "demand_signals",
        sa.Column("id", UUID, nullable=False),
        sa.Column("sku_family", sa.String(length=100), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("query_params", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sku_family",
            "period_start",
            "period_end",
            "source",
            name="uq_demand_signal",
        ),
    )
    op.create_index("ix_demand_signals_sku_family", "demand_signals", ["sku_family"])
    op.create_index(
        "ix_demand_signals_family_period", "demand_signals", ["sku_family", "period_start"]
    )

    # ------------------------------------------------------------------
    # Launch calendar and price decay (F3.8)
    # ------------------------------------------------------------------
    op.create_table(
        "launch_events",
        sa.Column("id", UUID, nullable=False),
        sa.Column("sku_family", sa.String(length=100), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sku_family", "event_date", "event_type", name="uq_launch_event"
        ),
    )
    op.create_index("ix_launch_events_event_date", "launch_events", ["event_date"])
    op.create_index("ix_launch_events_sku_family", "launch_events", ["sku_family"])

    op.create_table(
        "decay_params",
        sa.Column("id", UUID, nullable=False),
        sa.Column("sku_family", sa.String(length=100), nullable=False),
        sa.Column("grade", sa.String(length=4), nullable=False),
        sa.Column("rate_per_day", sa.Float(), nullable=False),
        sa.Column("fitted_at", sa.DateTime(), nullable=False),
        sa.Column("model_version", sa.String(length=60), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku_family", "grade", name="uq_decay_param"),
    )
    op.create_index("ix_decay_params_grade", "decay_params", ["grade"])
    op.create_index("ix_decay_params_sku_family", "decay_params", ["sku_family"])

    # ------------------------------------------------------------------
    # Source health (F3.9)
    # ------------------------------------------------------------------
    op.create_table(
        "source_health",
        sa.Column("id", UUID, nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", name="uq_source_health"),
    )
    op.create_index("ix_source_health_source", "source_health", ["source"])


def downgrade() -> None:
    """Drop the Phase 3 tables."""
    op.drop_table("source_health")
    op.drop_table("decay_params")
    op.drop_table("launch_events")
    op.drop_table("demand_signals")
    op.drop_table("teardown_yields")
    op.drop_table("component_prices")
    op.drop_table("import_files")
