#!/usr/bin/env python
"""
End-to-end smoke test for the Phase 2 decision engine.

Creates a unit, inspects it, runs the decision, and checks the card payload.
Runs entirely offline against a local SQLite database.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./.smoke.db")
os.environ.setdefault("SECRET_KEY", "smoke-test-secret-key-at-least-32-characters")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from secondroute.api.main import app  # noqa: E402
from secondroute.core.db import Base, get_session  # noqa: E402
from secondroute.identity.models import SKU  # noqa: E402
from secondroute.intake.models import (  # noqa: E402
    Inspection,
    OrderChannel,
    ReturnReasonCode,
    Unit,
)


async def main() -> int:
    """Run the smoke test."""
    db_path = Path("./.smoke.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        print(f"  [{status}] {label}{(' - ' + detail) if detail else ''}")
        if not condition:
            failures.append(label)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://smoke") as client:
        print("\n1. Health")
        response = await client.get("/health")
        check("GET /health returns 200", response.status_code == 200)
        check(
            "health payload has a status",
            "status" in response.json(),
            json.dumps(response.json().get("checks", {})),
        )

        print("\n2. Intake")
        sku_response = await client.post(
            "/api/v1/skus",
            json={
                "family": "MacBook Pro",
                "model_name": "M3 Pro",
                "year": "2023",
                "storage_gb": "512",
                "ram_gb": "18",
                "color": "Space Gray",
                "region": "US",
                "specs_json": {"cpu": "Apple M3 Pro"},
                "source": "smoke_test",
                "as_of": "2025-01-15",
            },
        )
        check(
            "POST /api/v1/skus returns 201",
            sku_response.status_code == 201,
            str(sku_response.status_code),
        )
        sku_id = sku_response.json()["id"]

        unit_response = await client.post(
            "/api/v1/units",
            json={
                "sku_id": sku_id,
                "serial": "C02SMOKETEST001",
                "return_reason_code": "buyer_remorse",
                "order_channel": "online",
            },
        )
        check(
            "POST /api/v1/units returns 201",
            unit_response.status_code == 201,
            str(unit_response.status_code),
        )
        unit_id = unit_response.json()["id"]

        inspection_response = await client.post(
            f"/api/v1/units/{unit_id}/inspections",
            json={
                "battery_health_pct": "94",
                "battery_cycles": "110",
                "cosmetic_grade": "A",
                "functional_tests_json": {
                    "display": True,
                    "keyboard": True,
                    "ports": True,
                    "audio": True,
                    "camera": True,
                },
                "activation_lock": "none",
                "accessories_json": {"charger": True, "box": True},
                "notes": "Smoke test unit",
            },
        )
        check(
            "POST /api/v1/units/{id}/inspections returns 201",
            inspection_response.status_code == 201,
            str(inspection_response.status_code),
        )

        print("\n3. Decision")
        decision_response = await client.post(
            f"/api/v1/units/{unit_id}/decide",
            json={"risk_profile": "balanced", "as_of": "2025-06-01T00:00:00"},
        )
        check(
            "POST /api/v1/units/{id}/decide returns 201",
            decision_response.status_code == 201,
            decision_response.text[:200],
        )
        if decision_response.status_code != 201:
            await engine.dispose()
            return 1

        decision = decision_response.json()
        decision_id = decision["id"]

        check(
            "a channel is recommended",
            bool(decision["recommended_channel"]),
            decision["recommended_channel"],
        )
        check(
            "confidence is in range",
            0.0 <= decision["confidence"] <= 1.0,
            str(decision["confidence"]),
        )
        check(
            "candidates are present",
            len(decision["candidates"]) == 6,  # 4 resale + parts harvest + hold
            str(len(decision["candidates"])),
        )
        check("reasons are present", len(decision["reasons"]) > 0)
        check("action steps are present", len(decision["action_steps"]) > 0)
        check("the prototype badge is set", decision["is_prototype"] is True)
        check("a snapshot hash is stored", len(decision["input_snapshot_hash"]) == 64)
        check(
            "the net range is ordered",
            all(
                c["p10"] <= c["p50"] + 0.01 and c["p50"] <= c["p90"] + 0.01
                for c in decision["candidates"]
                if c["eligible"]
            ),
        )
        check(
            "the probabilities of being best sum to one",
            abs(sum(c["probability_best"] for c in decision["candidates"] if c["eligible"]) - 1.0)
            < 0.01,
        )

        print("\n4. Reproducibility")
        second_response = await client.post(
            f"/api/v1/units/{unit_id}/decide",
            json={"risk_profile": "balanced", "as_of": "2025-06-01T00:00:00"},
        )
        second = second_response.json()
        check(
            "the same inputs give the same hash",
            second["input_snapshot_hash"] == decision["input_snapshot_hash"],
        )
        check(
            "the same inputs give the same recommendation",
            second["recommended_channel"] == decision["recommended_channel"],
        )

        reproduce = await client.get(f"/api/v1/decisions/{decision_id}/reproduce")
        check("GET /decisions/{id}/reproduce returns 200", reproduce.status_code == 200)
        check("the replay matches", reproduce.json()["matches"] is True)

        print("\n5. Costs")
        costs = await client.get("/api/v1/costs")
        check("GET /api/v1/costs returns 200", costs.status_code == 200)
        check(
            "every cost has a source",
            all(item["source"] for item in costs.json()["items"]),
        )
        bad_cost = await client.post(
            "/api/v1/costs",
            json={
                "kind": "fixed_fee",
                "key": "NO_SOURCE",
                "value": 1.0,
                "as_of": "2025-06-01",
            },
        )
        check("a cost without a source is rejected", bad_cost.status_code == 422)

        print("\n6. Decision history")
        history = await client.get(f"/api/v1/units/{unit_id}/decisions")
        check("GET /units/{id}/decisions returns 200", history.status_code == 200)
        check(
            "two decisions are recorded", history.json()["total"] == 2, str(history.json()["total"])
        )

    await engine.dispose()
    if db_path.exists():
        db_path.unlink()

    print(f"\n{'=' * 60}")
    if failures:
        print(f"FAILED: {len(failures)} check(s) failed: {failures}")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
