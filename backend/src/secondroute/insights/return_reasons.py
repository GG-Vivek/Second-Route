"""
Upstream return-reason insights (Phase 7 - F7.4).

Report of return reasons and rates by SKU family, for product and listing teams.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, UTC
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict

from secondroute.core.db import Base
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_

logger = structlog.get_logger(__name__)


@dataclass
class ReturnReasonSummary:
    """Summary of return reasons for a SKU family.

    Attributes:
        sku_family: The SKU family.
        total_returns: Total number of returns.
        reason_counts: Dictionary of reason -> count.
        reason_rates: Dictionary of reason -> rate (percentage).
        top_reason: The most common return reason.
        top_reason_rate: Rate of the top reason.
    """

    sku_family: str
    total_returns: int
    reason_counts: dict[str, int] = field(default_factory=dict)
    reason_rates: dict[str, float] = field(default_factory=dict)
    top_reason: str = ""
    top_reason_rate: float = 0.0


@dataclass
class ReturnReasonReport:
    """Complete return reason report.

    Attributes:
        generated_at: Timestamp of report generation.
        total_units: Total number of units analyzed.
        total_returns: Total number of returns.
        overall_return_rate: Overall return rate.
        by_family: Dictionary of family -> ReturnReasonSummary.
        by_reason: Dictionary of reason -> total count.
        top_families: List of families with highest return rates.
    """

    generated_at: datetime
    total_units: int
    total_returns: int
    overall_return_rate: float
    by_family: dict[str, ReturnReasonSummary] = field(default_factory=dict)
    by_reason: dict[str, int] = field(default_factory=dict)
    top_families: list[tuple[str, float]] = field(default_factory=list)


class ReturnReasonInsights:
    """Service for generating return-reason insights.

    Provides reports of return reasons and rates by SKU family,
    for product and listing teams.
    """

    def __init__(self) -> None:
        pass

    async def generate_report(
        self,
        session: AsyncSession,
        sku_families: list[str] | None = None,
    ) -> ReturnReasonReport:
        """Generate a return reason report.

        Args:
            session: Database session.
            sku_families: Optional list of families to include. If None, include all.

        Returns:
            ReturnReasonReport with insights.
        """
        from secondroute.identity.models import SKU
        from secondroute.intake.models import Unit

        # Get all units with their SKUs
        query: Any = select(Unit, SKU).join(SKU, Unit.sku_id == SKU.id)

        if sku_families:
            query = query.where(SKU.family.in_(sku_families))

        result = await session.execute(query)
        rows = result.all()

        # Aggregate by family
        family_data: dict[str, dict[str, int]] = {}
        reason_totals: dict[str, int] = {}
        total_units = 0
        total_returns = 0

        for unit, sku in rows:
            family = str(sku.family)
            reason = (
                unit.return_reason_code.value
                if hasattr(unit.return_reason_code, "value")
                else str(unit.return_reason_code)
            )

            if family not in family_data:
                family_data[family] = {}

            family_data[family][reason] = family_data[family].get(reason, 0) + 1
            reason_totals[reason] = reason_totals.get(reason, 0) + 1

            total_units += 1
            total_returns += 1

        # Build summaries
        by_family = {}
        for raw_family, reasons in family_data.items():
            family = str(raw_family)
            total = sum(reasons.values())
            reason_rates = {r: count / total for r, count in reasons.items()} if total > 0 else {}
            top_reason = max(reasons, key=lambda r: reasons[r]) if reasons else ""
            top_reason_rate = reason_rates.get(top_reason, 0.0)

            by_family[family] = ReturnReasonSummary(
                sku_family=family,
                total_returns=total,
                reason_counts=reasons,
                reason_rates=reason_rates,
                top_reason=top_reason,
                top_reason_rate=top_reason_rate,
            )

        # Top families by return rate (simplified - by total returns)
        top_families: list[tuple[str, float]] = sorted(
            [(f, float(s.total_returns)) for f, s in by_family.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Overall return rate (simplified)
        overall_return_rate = total_returns / total_units if total_units > 0 else 0.0

        return ReturnReasonReport(
            generated_at=datetime.now(UTC),
            total_units=total_units,
            total_returns=total_returns,
            overall_return_rate=overall_return_rate,
            by_family=by_family,
            by_reason=reason_totals,
            top_families=top_families,
        )

    async def get_top_return_reasons(
        self,
        session: AsyncSession,
        sku_family: str,
        limit: int = 5,
    ) -> list[tuple[str, int, float]]:
        """Get top return reasons for a SKU family.

        Args:
            session: Database session.
            sku_family: The SKU family.
            limit: Maximum number of reasons to return.

        Returns:
            List of (reason, count, rate) tuples.
        """
        from secondroute.identity.models import SKU
        from secondroute.intake.models import Unit

        query: Any = (
            select(Unit.return_reason_code, func.count(Unit.id))
            .join(SKU, Unit.sku_id == SKU.id)
            .where(SKU.family == sku_family)
            .group_by(Unit.return_reason_code)
            .order_by(func.count(Unit.id).desc())
            .limit(limit)
        )

        result = await session.execute(query)
        rows = result.all()

        total = sum(count for _, count in rows)
        return [(str(reason), count, count / total if total > 0 else 0.0) for reason, count in rows]

    async def get_return_rate_by_family(
        self,
        session: AsyncSession,
    ) -> dict[str, float]:
        """Get return rate by SKU family.

        Args:
            session: Database session.

        Returns:
            Dictionary of family -> return rate.
        """
        from secondroute.identity.models import SKU
        from secondroute.intake.models import Unit

        # Get total units per family
        total_query: Any = (
            select(SKU.family, func.count(Unit.id))
            .join(SKU, Unit.sku_id == SKU.id)
            .group_by(SKU.family)
        )
        total_result = await session.execute(total_query)
        total_by_family = dict(total_result.all())

        # For now, return rate is just count (simplified)
        return {family: float(count) for family, count in total_by_family.items()}
