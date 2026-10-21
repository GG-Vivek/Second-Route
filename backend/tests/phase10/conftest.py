"""
Isolated test setup for Phase 10 (the public storefront).
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from secondroute.api.main import app
from secondroute.core.db import Base, get_session

# Register the tables with the metadata before any table is created.
import secondroute.condition.models  # noqa: F401
import secondroute.costs.models  # noqa: F401
import secondroute.decision.models  # noqa: F401
import secondroute.identity.models  # noqa: F401
import secondroute.intake.models  # noqa: F401
import secondroute.pricing.models  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
async def test_engine() -> AsyncGenerator[Any, None]:
    """Create a test database engine with every table."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def db_session(test_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for ``test_session``."""
    yield test_session


@pytest.fixture(scope="function")
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with the database session overridden."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


#: The candidates a decision carries. The breakdown holds the business's
#: costs, which must never reach a shop window.
CANDIDATES: list[dict[str, Any]] = [
    {
        "channel": "RESELL_OPEN_BOX",
        "eligible": True,
        "exclusion_reason": None,
        "mean": 612.0,
        "stddev": 133.75,
        "p10": 503.81,
        "p50": 556.77,
        "p90": 799.69,
        "grade_probabilities": {"A": 0.9, "B": 0.1},
        "price_sources": {"A": "synthetic", "B": "synthetic"},
        "price_as_of": {"A": "2026-01-01T00:00:00", "B": "2026-01-01T00:00:00"},
        "breakdown": {
            "sale_price": 790.84,
            "fees": 119.87,
            "logistics": 28.07,
            "handling": 18.03,
            "repair": 11.37,
            "holding": 1.35,
            "total_cost": 178.68,
            "net": 612.16,
        },
        "probability_best": 0.84,
        "certainty_equivalent": 545.12,
    },
    {
        "channel": "RESELL_REFURB",
        "eligible": True,
        "exclusion_reason": None,
        "mean": 421.35,
        "stddev": 153.32,
        "p10": 242.89,
        "p50": 425.5,
        "p90": 676.32,
        "grade_probabilities": {"A": 0.9, "B": 0.1},
        "price_sources": {"A": "synthetic"},
        "price_as_of": {"A": "2026-01-01T00:00:00"},
        "breakdown": {
            "sale_price": 620.0,
            "fees": 90.0,
            "logistics": 28.07,
            "handling": 18.03,
            "repair": 40.0,
            "holding": 1.35,
            "total_cost": 177.45,
            "net": 442.55,
        },
        "probability_best": 0.1,
        "certainty_equivalent": 400.0,
    },
    {
        "channel": "RECYCLE",
        "eligible": True,
        "mean": 40.0,
        "stddev": 5.0,
        "p10": 33.0,
        "p50": 40.0,
        "p90": 47.0,
        "grade_probabilities": {},
        "price_sources": {},
        "price_as_of": {},
        "breakdown": {
            "sale_price": 0.0,
            "fees": 0.0,
            "logistics": 0.0,
            "handling": 40.0,
            "repair": 0.0,
            "holding": 0.0,
            "total_cost": 40.0,
            "net": 0.0,
        },
        "probability_best": 0.05,
        "certainty_equivalent": 35.0,
    },
]


async def make_sku(  # noqa: PLR0913
    session: AsyncSession,
    *,
    family: str = "MacBook Pro",
    model_name: str = "M3 Pro",
    storage_gb: str = "512",
    color: str = "Space Gray",
) -> Any:
    """Create a catalogue model.

    The catalogue is shared: a model belongs to nobody, and the tenant
    is on the unit.
    """
    from datetime import date

    from secondroute.identity.models import SKU

    sku = SKU(
        family=family,
        model_name=model_name,
        year="2023",
        storage_gb=storage_gb,
        ram_gb="18",
        color=color,
        region="US",
        specs_json={"display": "14 inch"},
        source="seed",
        as_of=date(2025, 1, 1),
    )
    session.add(sku)
    await session.flush()
    return sku


async def make_unit(  # noqa: PLR0913
    session: AsyncSession,
    org_id: Any,
    sku: Any,
    *,
    status: str = "decided",
    serial: str = "SERIAL-SECRET",
    notes: str = "The customer said it was slow.",
) -> Any:
    """Create a returned unit."""
    from secondroute.intake.models import ReturnReasonCode, Unit, UnitStatus

    unit = Unit(
        org_id=org_id,
        sku_id=sku.id,
        serial=serial,
        return_reason_code=ReturnReasonCode.DEFECTIVE,
        order_channel="online",
        notes=notes,
        status=UnitStatus(status),
    )
    session.add(unit)
    await session.flush()
    return unit


async def make_inspection(
    session: AsyncSession,
    unit: Any,
    *,
    grade: str = "A",
    battery: str = "95",
) -> Any:
    """Create an inspection."""
    from secondroute.intake.models import Inspection

    inspection = Inspection(
        unit_id=unit.id,
        battery_health_pct=battery,
        battery_cycles="120",
        cosmetic_grade=grade,
        functional_tests_json={"display": True, "battery": False},
        activation_lock="none",
        accessories_json={"charger": True, "box": False},
        notes="A scratch on the lid.",
    )
    session.add(inspection)
    await session.flush()
    return inspection


async def make_photo(session: AsyncSession, unit: Any, inspection: Any) -> Any:
    """Create a photograph."""
    from secondroute.intake.models import Photo

    photo = Photo(
        unit_id=unit.id,
        inspection_id=inspection.id,
        storage_path=f"/uploads/{uuid4().hex}.jpg",
        exif_stripped="true",
    )
    session.add(photo)
    await session.flush()
    return photo


async def make_decision(
    session: AsyncSession,
    org_id: Any,
    unit: Any,
    *,
    recommended: str = "RESELL_OPEN_BOX",
    minutes: int = 0,
) -> Any:
    """Create a decision."""
    from datetime import datetime, timedelta

    from secondroute.decision.models import Decision

    decision = Decision(
        org_id=org_id,
        unit_id=unit.id,
        created_at=datetime.utcnow() + timedelta(minutes=minutes),
        model_version="decision-v1",
        risk_profile="balanced",
        recommended_channel=recommended,
        confidence=0.85,
        fallback_used=False,
        candidates_json=json.dumps(CANDIDATES),
        reasons_json="[]",
        flip_conditions_json="[]",
        data_freshness_json="{}",
        action_steps_json="[]",
        input_snapshot_hash="abc123",
        input_snapshot_json="{}",
    )
    session.add(decision)
    await session.flush()
    return decision
