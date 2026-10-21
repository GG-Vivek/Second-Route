#!/usr/bin/env python
"""
Seed the demonstration data (F9.3).

The application is not worth looking at with nothing in it. This creates a
workload: units that came back, inspections of them, photographs of them,
the decisions the engine made, and what actually happened to some of them.

Everything it creates is seeded, so running it twice gives the same data.
The decisions are made by the real engine rather than written down, so
what the dashboard shows is what the engine would have said.

    python scripts/seed_demo_data.py --units 40
    python scripts/seed_demo_data.py --units 40 --reset
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from secondroute.core.db import close_db, init_db, set_session_org_id  # noqa: E402
from secondroute.core.logging import get_logger  # noqa: E402
from secondroute.decision.engine import decide_unit  # noqa: E402
from secondroute.feedback.models import Outcome, Override  # noqa: E402
from secondroute.identity.organizations import Organization  # noqa: E402
from secondroute.identity.models import SKU  # noqa: E402
from secondroute.intake.images import store_photo  # noqa: E402
from secondroute.intake.models import (  # noqa: E402
    Inspection,
    OrderChannel,
    Photo,
    ReturnReasonCode,
    Unit,
    UnitStatus,
)
from secondroute.pricing.composite import FallbackPriceSource  # noqa: E402
from secondroute.pricing.sources import (  # noqa: E402
    DatabasePriceSource,
    SyntheticPriceSource,
)
from device_photos import ANGLES, body_colour_for, make_device_photo  # noqa: E402

logger = get_logger(__name__)

#: The organisation the demonstration data belongs to.
ORG_NAME = "SecondRoute Development"

#: The reasons a unit comes back, and how often.
REASONS = [
    (ReturnReasonCode.BUYER_REMORSE, 26),
    (ReturnReasonCode.NOT_AS_DESCRIBED, 14),
    (ReturnReasonCode.DEFECTIVE, 12),
    (ReturnReasonCode.WRONG_ITEM, 8),
    (ReturnReasonCode.NO_LONGER_NEEDED, 18),
    (ReturnReasonCode.BETTER_PRICE_FOUND, 12),
    (ReturnReasonCode.DAMAGED_IN_SHIPPING, 6),
    (ReturnReasonCode.OTHER, 4),
]

#: Where the unit was bought.
CHANNELS = [
    (OrderChannel.ONLINE, 62),
    (OrderChannel.RETAIL, 24),
    (OrderChannel.MARKETPLACE, 9),
    (OrderChannel.B2B, 5),
]

#: The tests an inspector runs.
TESTS = [
    "display",
    "keyboard",
    "ports",
    "camera",
    "audio",
    "wifi",
    "battery",
    "boot",
]

#: The accessories that come back with the device.
ACCESSORIES = ["charger", "cable", "box", "manual"]

#: The reasons a person gives for going against the engine.
OVERRIDE_REASONS = [
    "Too risky for the customer",
    "The customer insisted",
    "The parts were worth more than the unit",
    "The inspection was wrong",
    "We already have stock of this model",
    "A liquid damaged sign was not picked up",
]

#: What the notes say.
NOTES = [
    "Screen is clean, no scratches.",
    "Two scuffs on the lid, one on the corner.",
    "Small dent on the back, near the hinge.",
    "Charger missing. Everything else is in the box.",
    "The battery was below eighty percent on arrival.",
    "Keyboard is fine, the trackpad is not.",
    "A sticker was left on the underside.",
    "The box has been opened and resealed.",
    "",
    "",
]

#: The final states a unit can reach.
FINAL_STATES = ["sold", "sold", "sold", "sold", "recycled", "donated", "scrapped"]


def _weighted(rng: random.Random, options: list[tuple[object, int]]) -> object:
    """Choose one of the options, in proportion to its weight."""
    total = sum(weight for _, weight in options)
    pick = rng.uniform(0, total)
    running = 0.0
    for value, weight in options:
        running += weight
        if pick <= running:
            return value
    return options[-1][0]


def _serial(rng: random.Random, index: int) -> str:
    """Return a serial number that looks like one."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
    body = "".join(rng.choice(alphabet) for _ in range(8))
    return f"C02{body}{index:03d}"


def _battery(rng: random.Random, grade: str) -> tuple[str, str]:
    """Return the battery health and the cycle count for a grade."""
    centres = {"A": (95, 60), "B": (88, 210), "C": (78, 420), "D": (66, 610)}
    health, cycles = centres[grade]
    return str(max(40, min(100, int(rng.gauss(health, 6))))), str(
        max(10, int(rng.gauss(cycles, 90)))
    )


def _functional_tests(rng: random.Random, grade: str) -> dict[str, bool]:
    """Return the functional tests, with the failures a grade implies."""
    failure_chance = {"A": 0.02, "B": 0.10, "C": 0.26, "D": 0.45}[grade]
    results: dict[str, bool] = {}
    for test in TESTS:
        results[test] = rng.random() > failure_chance
    return results


def _accessories(rng: random.Random, grade: str) -> dict[str, bool]:
    """Return the accessories that came back."""
    missing_chance = {"A": 0.12, "B": 0.24, "C": 0.42, "D": 0.6}[grade]
    return {name: rng.random() > missing_chance for name in ACCESSORIES}


async def _reset(session: AsyncSession, org_id: uuid.UUID) -> None:
    """Remove the demonstration data so that it can be made again."""
    from secondroute.decision.models import Decision

    # The organisation has to be set before anything is deleted. The
    # row-level security policies read it, and without it the delete
    # matches nothing and the old data stays exactly where it was.
    await set_session_org_id(session, str(org_id))

    decisions = (
        (await session.execute(select(Decision.id).where(Decision.org_id == org_id)))
        .scalars()
        .all()
    )
    if decisions:
        await session.execute(delete(Override).where(Override.decision_id.in_(decisions)))
        await session.execute(delete(Outcome).where(Outcome.decision_id.in_(decisions)))
        await session.execute(
            delete(Photo).where(
                Photo.unit_id.in_(
                    (await session.execute(select(Unit.id).where(Unit.org_id == org_id)))
                    .scalars()
                    .all()
                )
            )
        )
        await session.execute(
            delete(Inspection).where(
                Inspection.unit_id.in_(
                    (await session.execute(select(Unit.id).where(Unit.org_id == org_id)))
                    .scalars()
                    .all()
                )
            )
        )
        await session.execute(delete(Decision).where(Decision.id.in_(decisions)))
    await session.execute(delete(Unit).where(Unit.org_id == org_id))
    await session.flush()
    logger.info("demo_data_reset", org_id=str(org_id))


async def seed(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    count: int,
    seed_value: int,
) -> dict[str, int]:
    """Create the demonstration data.

    Args:
        session: The database session.
        org_id: The organisation the data belongs to.
        count: How many units to create.
        seed_value: The seed, so the same data is made every time.

    Returns:
        What was created.
    """
    rng = random.Random(seed_value)

    skus = (await session.execute(select(SKU).order_by(SKU.family, SKU.model_name))).scalars().all()
    if not skus:
        raise SystemExit("The catalogue is empty. Run `python scripts/load_skus.py` before this.")

    # The row-level security policies read the organisation from the
    # database, so the session has to be told which one it is acting for.
    await set_session_org_id(session, str(org_id))
    price_source = FallbackPriceSource(
        DatabasePriceSource(session, source_tag="synthetic"),
        SyntheticPriceSource(),
    )

    made = {
        "units": 0,
        "inspections": 0,
        "photos": 0,
        "decisions": 0,
        "overrides": 0,
        "outcomes": 0,
    }
    now = datetime.utcnow()

    for index in range(count):
        sku = skus[index % len(skus)]
        grade = rng.choices(["A", "B", "C", "D"], weights=[42, 32, 18, 8])[0]
        received = now - timedelta(days=rng.randint(0, 75), hours=rng.randint(0, 23))

        unit = Unit(
            org_id=org_id,
            sku_id=sku.id,
            serial=_serial(rng, index),
            return_reason_code=_weighted(rng, REASONS),
            order_channel=_weighted(rng, CHANNELS),
            # What the person who took the return in wants the next person
            # to know.
            notes=rng.choice(NOTES) or None,
            status=UnitStatus.RECEIVED,
            received_at=received,
        )
        session.add(unit)
        await session.flush()
        made["units"] += 1

        battery_health, battery_cycles = _battery(rng, grade)
        inspection = Inspection(
            unit_id=unit.id,
            battery_health_pct=battery_health,
            battery_cycles=battery_cycles,
            cosmetic_grade=grade,
            functional_tests_json=_functional_tests(rng, grade),
            activation_lock="none" if rng.random() > 0.06 else "present",
            accessories_json=_accessories(rng, grade),
            notes=rng.choice(NOTES),
            created_at=received + timedelta(hours=rng.randint(1, 20)),
        )
        session.add(inspection)
        await session.flush()
        made["inspections"] += 1

        # The photographs, taken through the same path a real one takes.
        body = body_colour_for(sku.color or "")
        for angle in ANGLES:
            content = make_device_photo(
                serial=unit.serial or str(unit.id),
                body_colour=body,
                angle=angle,
                seed=seed_value + index,
            )
            stored = store_photo(content, content_type="image/jpeg")
            session.add(
                Photo(
                    unit_id=unit.id,
                    inspection_id=inspection.id,
                    storage_path=stored.storage_path,
                    exif_stripped=str(stored.exif_stripped).lower(),
                    created_at=inspection.created_at + timedelta(minutes=rng.randint(1, 90)),
                )
            )
            made["photos"] += 1
        await session.flush()

        # The decision, made by the engine rather than written down.
        try:
            decision = await decide_unit(
                session,
                unit.id,
                price_source,
                risk_profile=rng.choice(["conservative", "balanced", "balanced", "aggressive"]),
            )
        except ValueError:
            continue
        made["decisions"] += 1

        # Some of them are overridden, with a reason.
        if rng.random() < 0.2:
            alternatives = [
                candidate
                for candidate in decision.candidates
                if candidate.get("eligible")
                and candidate.get("channel") != decision.recommended_channel
            ]
            if alternatives:
                chosen = rng.choice(alternatives)["channel"]
                session.add(
                    Override(
                        decision_id=decision.id,
                        user_id=None,
                        chosen_channel=chosen,
                        reason_text=rng.choice(OVERRIDE_REASONS),
                        created_at=decision.created_at + timedelta(hours=rng.randint(1, 30)),
                    )
                )
                made["overrides"] += 1

        # And some of them are sold, so that the analytics have something
        # to measure.
        if rng.random() < 0.72:
            candidates = {candidate["channel"]: candidate for candidate in decision.candidates}
            channel = decision.recommended_channel
            expected = candidates.get(channel, {}).get("p50", 0.0)
            sale_price = max(0.0, rng.gauss(expected, max(40.0, abs(expected) * 0.12)))
            session.add(
                Outcome(
                    unit_id=unit.id,
                    decision_id=decision.id,
                    channel_taken=channel,
                    sale_price=round(sale_price, 2),
                    fees_actual=round(rng.gauss(190, 30), 2),
                    repair_cost_actual=round(abs(rng.gauss(35, 30)), 2),
                    logistics_actual=round(abs(rng.gauss(28, 10)), 2),
                    days_to_disposition=max(1, int(rng.gauss(16, 9))),
                    final_status=rng.choice(FINAL_STATES),
                    recorded_at=decision.created_at + timedelta(days=rng.randint(2, 40)),
                )
            )
            made["outcomes"] += 1

        unit.status = UnitStatus.SOLD if made["outcomes"] else UnitStatus.INSPECTED
        await session.flush()

    await session.commit()
    return made


async def main() -> None:
    """Seed the demonstration data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--units", type=int, default=40, help="How many units to create.")
    parser.add_argument("--seed", type=int, default=20261021, help="The seed.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove the demonstration data first.",
    )
    args = parser.parse_args()

    await init_db()
    try:
        from secondroute.core.db import get_session_context

        async with get_session_context() as session:
            result = await session.execute(
                select(Organization).where(Organization.name == ORG_NAME)
            )
            org = result.scalars().first()
            if org is None:
                org = Organization(name=ORG_NAME, risk_profile="balanced")
                session.add(org)
                await session.flush()
                await session.refresh(org)

            if args.reset:
                await _reset(session, org.id)
                await session.commit()

            made = await seed(session, org.id, count=args.units, seed_value=args.seed)

        print("The demonstration data is in.")
        print(f"  organisation  {org.id}")
        for key, value in made.items():
            print(f"  {key:<12} {value}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
