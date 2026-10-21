"""
Reading the listings for the storefront (Phase 10).

A listing is a device that is being sold. Not every device is: the engine
recommends a channel for each one, and only the resale channels put a
price on the window. A device that was recommended for recycling is not
for sale, and a device whose latest decision says something else than
resale is not for sale either, whatever an earlier decision said.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import Select, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.decision.models import Decision
from secondroute.identity.models import SKU
from secondroute.intake.models import Inspection, Photo, Unit, UnitStatus
from secondroute.storefront.schemas import (
    ListingCheckRead,
    ListingDetailRead,
    ListingListRead,
    ListingPhotoRead,
    ListingPriceRead,
    ListingRead,
)

#: The channels that put a device on sale.
RESALE_CHANNELS: tuple[str, ...] = ("RESELL_OPEN_BOX", "RESELL_REFURB")

#: The statuses a device is not in any more. A device that has been sold,
#: recycled or given away is not on the window.
GONE_STATUSES: tuple[UnitStatus, ...] = (
    UnitStatus.SOLD,
    UnitStatus.RECYCLED,
    UnitStatus.DONATED,
)

#: The grade in the words a buyer would use.
CONDITION_LABELS: dict[str, str] = {
    "A": "Like new",
    "B": "Good",
    "C": "Fair",
    "D": "For parts",
}

#: What the grade means, for the card.
CONDITION_NOTES: dict[str, str] = {
    "A": "Barely marked. It looks like it was not used.",
    "B": "Light signs of use. Nothing that catches the eye.",
    "C": "Visible marks from use. It works, and it shows.",
    "D": "Well used. It works, and it is not pretty.",
}


def _title(sku: SKU) -> str:
    """The name of a device, in the shop's words.

    Args:
        sku: The catalogue model.

    Returns:
        The title of the listing.
    """
    parts = [f"{sku.model_name} {sku.year}".strip()]
    if sku.storage_gb:
        parts.append(sku.storage_gb)
    return " ".join(parts)


def _photo_alt(sku: SKU, index: int) -> str:
    """What a photograph shows.

    Args:
        sku: The catalogue model.
        index: Which photograph this is.

    Returns:
        The text alternative for the photograph.
    """
    if index == 0:
        return f"{sku.model_name}, {sku.year}"
    return f"{sku.model_name}, {sku.year}, photograph {index + 1}"


async def _latest_decisions(session: AsyncSession, org_id: uuid.UUID) -> dict[uuid.UUID, Decision]:
    """The latest decision for every unit.

    Only the latest one counts. A unit whose first decision said to sell
    it and whose second said to recycle it is being recycled.

    Args:
        session: The database session.
        org_id: The organisation.

    Returns:
        The latest decision for each unit, by unit id.
    """
    ranked = _ranked(org_id)
    result = await session.execute(select(ranked).where(ranked.c.rn == 1))
    latest: dict[uuid.UUID, Decision] = {}
    for row in result.all():
        latest[row.unit_id] = Decision(
            id=row.id,
            unit_id=row.unit_id,
            recommended_channel=row.recommended_channel,
            candidates_json=row.candidates_json,
            created_at=row.created_at,
        )
    return latest


def _price_for(decision: Decision, currency: str = "USD") -> ListingPriceRead | None:
    """The asking price of a decision.

    The price is the expected sale price, which is what the buyer pays.
    The net is what the business keeps, and it is not on a shop window.

    Args:
        decision: The decision.
        currency: The currency to quote in.

    Returns:
        The price, or None when the decision has no sale price to offer.
    """
    try:
        candidates = json.loads(decision.candidates_json or "[]")
    except (TypeError, ValueError):
        return None
    if not isinstance(candidates, list):
        return None

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("channel") != decision.recommended_channel:
            continue
        breakdown = candidate.get("breakdown")
        if not isinstance(breakdown, dict):
            return None
        amount = breakdown.get("sale_price")
        if amount is None:
            return None

        # Where the price came from, and how fresh it is. The price
        # sources are keyed by grade, so the freshest of them is the one
        # to quote.
        sources = candidate.get("price_sources") or {}
        as_ofs = candidate.get("price_as_of") or {}
        source = "unknown"
        if isinstance(sources, dict) and sources:
            source = sorted(str(value) for value in sources.values())[0]
        as_of: str | None = None
        if isinstance(as_ofs, dict) and as_ofs:
            as_of = sorted(str(value) for value in as_ofs.values())[-1]

        return ListingPriceRead(
            amount=round(float(amount), 2),
            currency=currency,
            source=source,
            as_of=as_of,
            is_estimate=True,
        )
    return None


def _published_photos(unit: Unit) -> list[Photo]:
    """The photographs of a unit that may be shown on the window.

    One of the four angles the inspection form takes is a photograph of
    the label on the bottom of the device, and the label carries the
    serial number. The serial is not on the shop window, so that
    photograph is not either.

    Args:
        unit: The unit.

    Returns:
        The photographs, oldest first.
    """
    return sorted(
        (photo for photo in unit.photos if photo.published),
        key=lambda photo: photo.created_at,
    )


def _latest_inspection(unit: Unit) -> Inspection | None:
    """The most recent inspection of a unit.

    Args:
        unit: The unit.

    Returns:
        The inspection, or None when the unit has never been inspected.
    """
    if not unit.inspections:
        return None
    return max(unit.inspections, key=lambda inspection: inspection.created_at)


def _accessories(inspection: Inspection | None) -> list[str]:
    """What is in the box.

    Args:
        inspection: The inspection.

    Returns:
        The accessories that are there.
    """
    if inspection is None:
        return []
    raw = inspection.accessories_json or {}
    if not isinstance(raw, dict):
        return []
    return [name for name, present in raw.items() if present]


def _checks(inspection: Inspection | None) -> list[ListingCheckRead]:
    """What was tested, and what the test said.

    Args:
        inspection: The inspection.

    Returns:
        The tests.
    """
    if inspection is None:
        return []
    raw = inspection.functional_tests_json or {}
    if not isinstance(raw, dict):
        return []
    checks: list[ListingCheckRead] = []
    for name, result in raw.items():
        if isinstance(result, bool):
            checks.append(ListingCheckRead(name=str(name).replace("_", " "), passed=result))
        elif isinstance(result, dict) and "passed" in result:
            checks.append(
                ListingCheckRead(name=str(name).replace("_", " "), passed=bool(result["passed"]))
            )
    return checks


def _highlights(
    sku: SKU,
    inspection: Inspection | None,
    grade: str,
) -> list[str]:
    """The things worth saying about a device.

    Args:
        sku: The catalogue model.
        inspection: The inspection.
        grade: The cosmetic grade.

    Returns:
        The lines for the card.
    """
    lines: list[str] = []
    if sku.ram_gb:
        lines.append(f"{sku.ram_gb} GB memory")
    if sku.storage_gb:
        lines.append(f"{sku.storage_gb} storage")
    if sku.year:
        lines.append(f"{sku.year} model")
    if inspection is not None and inspection.battery_health_pct:
        lines.append(f"Battery at {inspection.battery_health_pct}% health")
    if grade in CONDITION_NOTES:
        lines.append(CONDITION_NOTES[grade])
    return lines


def _listing(
    unit: Unit,
    decision: Decision,
    price: ListingPriceRead,
) -> ListingRead:
    """Build one listing.

    Args:
        unit: The unit.
        decision: The latest decision for the unit.
        price: The asking price.

    Returns:
        The listing.
    """
    sku = unit.sku
    inspection = _latest_inspection(unit)
    grade = inspection.cosmetic_grade if inspection is not None else "C"
    photos = _published_photos(unit)
    return ListingRead(
        id=unit.id,
        title=_title(sku),
        family=sku.family,
        model_name=sku.model_name,
        year=sku.year,
        storage_gb=sku.storage_gb,
        ram_gb=sku.ram_gb,
        color=sku.color,
        grade=grade,
        condition=CONDITION_LABELS.get(grade, "Fair"),
        battery_health_pct=inspection.battery_health_pct if inspection is not None else None,
        price=price,
        photo=(
            ListingPhotoRead(url=photos[0].storage_path, alt=_photo_alt(sku, 0)) if photos else None
        ),
        photo_count=len(photos),
        listed_at=decision.created_at,
        in_stock=unit.status not in GONE_STATUSES,
    )


def _ranked(org_id: uuid.UUID) -> Any:
    """The latest decision for every unit, ranked.

    The window function reads the columns of an inner query rather than
    the table itself. A window function written over the table drags the
    table into the outer query as well, and a table with no join
    condition in the outer query multiplies every row by the number of
    rows in the table.

    Args:
        org_id: The organisation.

    Returns:
        The subquery, with a rank in the ``rn`` column.
    """
    inner = (
        select(
            Decision.id.label("id"),
            Decision.unit_id.label("unit_id"),
            Decision.recommended_channel.label("recommended_channel"),
            Decision.candidates_json.label("candidates_json"),
            Decision.created_at.label("created_at"),
        )
        .where(Decision.org_id == org_id)
        .subquery()
    )
    return (
        select(
            inner.c.id,
            inner.c.unit_id,
            inner.c.recommended_channel,
            inner.c.candidates_json,
            inner.c.created_at,
            func.row_number()
            .over(
                partition_by=inner.c.unit_id,
                order_by=(inner.c.created_at.desc(), inner.c.id.desc()),
            )
            .label("rn"),
        )
    ).subquery()


def _mentions_its_channel(ranked: Any) -> Any:
    """Whether a decision's candidates mention the channel it recommends.

    The candidates are stored as text, so this is a text question: the
    recommended channel has to appear in the candidates. A decision that
    recommends a channel it did not evaluate is malformed, and a
    malformed decision is not a listing.

    Asking the question in the query rather than in Python is what keeps
    the count of the listings and the listings themselves the same
    number.

    Args:
        ranked: The ranked decisions.

    Returns:
        The expression, which is greater than zero when the channel is
        mentioned.
    """
    return func.char_length(ranked.c.candidates_json) - func.char_length(
        func.replace(
            ranked.c.candidates_json,
            literal_column('\'"channel": "\'')
            + ranked.c.recommended_channel
            + literal_column("'\"'"),
            "",
        )
    )


def _base_query(org_id: uuid.UUID) -> Select[Any]:
    """The query for the units that are on sale.

    Args:
        org_id: The organisation.

    Returns:
        The query.
    """
    ranked = _ranked(org_id)
    return (
        select(Unit)
        .join(
            ranked,
            (ranked.c.rn == 1) & (ranked.c.unit_id == Unit.id),
        )
        .where(
            Unit.org_id == org_id,
            ranked.c.recommended_channel.in_(RESALE_CHANNELS),
            Unit.status.notin_(GONE_STATUSES),
            _mentions_its_channel(ranked) > 0,
        )
    )


async def list_listings(  # noqa: PLR0913
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    family: str | None = None,
    search: str | None = None,
    limit: int = 24,
    offset: int = 0,
) -> ListingListRead:
    """The devices that are on sale.

    Args:
        session: The database session.
        org_id: The organisation.
        family: Restrict to one family.
        search: Restrict to the models that match.
        limit: How many to return.
        offset: How many to skip.

    Returns:
        A page of listings.
    """
    query = _base_query(org_id).join(SKU, SKU.id == Unit.sku_id)

    if family:
        query = query.where(SKU.family == family)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                SKU.family.ilike(pattern),
                SKU.model_name.ilike(pattern),
                SKU.color.ilike(pattern),
                SKU.storage_gb.ilike(pattern),
            )
        )

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = int((await session.execute(count_query)).scalar_one())

    rows = (
        (
            await session.execute(
                query.order_by(Unit.received_at.desc(), Unit.id).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )

    decisions = await _latest_decisions(session, org_id)

    items: list[ListingRead] = []
    synthetic = False
    for unit in rows:
        decision = decisions.get(unit.id)
        if decision is None:
            continue
        price = _price_for(decision)
        if price is None:
            continue
        if price.source.startswith("synthetic"):
            synthetic = True
        items.append(_listing(unit, decision, price))

    families = await _families(session, org_id)

    return ListingListRead(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        families=families,
        synthetic=synthetic,
    )


async def _families(session: AsyncSession, org_id: uuid.UUID) -> list[str]:
    """The families that are on sale, for the filter.

    Args:
        session: The database session.
        org_id: The organisation.

    Returns:
        The family names, in order.
    """
    query = (
        _base_query(org_id)
        .join(SKU, SKU.id == Unit.sku_id)
        .with_only_columns(SKU.family)
        .distinct()
    )
    result = await session.execute(query)
    return sorted(row for row in result.scalars().all() if row)


async def get_listing(
    session: AsyncSession,
    org_id: uuid.UUID,
    listing_id: uuid.UUID,
) -> ListingDetailRead | None:
    """One device, in full.

    Args:
        session: The database session.
        org_id: The organisation.
        listing_id: The identifier of the listing.

    Returns:
        The listing, or None when there is no such listing.
    """
    query = _base_query(org_id).where(Unit.id == listing_id)
    unit = (await session.execute(query)).scalars().first()
    if unit is None:
        return None

    decisions = await _latest_decisions(session, org_id)
    decision = decisions.get(unit.id)
    if decision is None:
        return None
    price = _price_for(decision)
    if price is None:
        return None

    listing = _listing(unit, decision, price)
    sku = unit.sku
    inspection = _latest_inspection(unit)
    photos = _published_photos(unit)

    return ListingDetailRead(
        **listing.model_dump(),
        photos=[
            ListingPhotoRead(url=photo.storage_path, alt=_photo_alt(sku, index))
            for index, photo in enumerate(photos)
        ],
        accessories=_accessories(inspection),
        checks=_checks(inspection),
        highlights=_highlights(sku, inspection, listing.grade),
    )


__all__ = [
    "CONDITION_LABELS",
    "CONDITION_NOTES",
    "GONE_STATUSES",
    "RESALE_CHANNELS",
    "get_listing",
    "list_listings",
]
