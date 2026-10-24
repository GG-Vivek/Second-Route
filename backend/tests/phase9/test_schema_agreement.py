"""
The schema and the models have to agree (F9.4).

A native enum on PostgreSQL only holds the values it was created with. The
baseline migration created the three intake enums with the values it knew
about at the time, and the models have grown since. Every value the model
declares and the database does not have is a write that fails.

Four return reasons, two order channels and four unit statuses were
missing, and the intake form offers all of them: logging a return for the
wrong item, marking a unit dispatched, and so on, all ended in a five
hundred.

These tests read the migrations and compare them with the models, so that
the drift cannot come back without somebody being told about it.
"""

from __future__ import annotations

import enum
import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

from secondroute.intake.models import OrderChannel, ReturnReasonCode, Unit, UnitStatus

VERSIONS = Path(__file__).parent.parent.parent / "alembic" / "versions"

#: The enums the models declare, by the name the database knows them by.
MODEL_ENUMS: dict[str, type[enum.Enum]] = {
    "unit_status_enum": UnitStatus,
    "return_reason_code_enum": ReturnReasonCode,
    "order_channel_enum": OrderChannel,
}


def _load_migration(path: Path) -> ModuleType:
    """Import a migration so that its data can be read."""
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _values_in_the_migrations(enum_name: str) -> set[str]:
    """Return every value the migrations give an enum."""
    values: set[str] = set()

    # The baseline creates the enums with a list of their values.
    create = re.compile(
        r"sa\.Enum\(\s*(?P<values>(?:\"[A-Z_]+\"\s*,?\s*)+)name=\"" + enum_name + r"\"",
        re.M,
    )
    baseline = (VERSIONS / "0001_baseline.py").read_text()
    for match in create.finditer(baseline):
        values.update(re.findall(r"\"([A-Z_]+)\"", match.group("values")))

    # A later migration adds values, and says which ones in its data.
    for path in sorted(VERSIONS.glob("*.py")):
        if path.name == "0001_baseline.py":
            continue
        try:
            module = _load_migration(path)
        except Exception:  # pragma: no cover - a migration that will not import
            continue
        added = getattr(module, "MISSING_VALUES", None)
        if isinstance(added, dict):
            values.update(added.get(enum_name, ()))

    return values


class TestTheEnumsAgree:
    """Every value the model declares exists in the database."""

    @pytest.mark.parametrize("enum_name", sorted(MODEL_ENUMS))
    def test_every_value_the_model_declares_is_in_the_database(self, enum_name: str) -> None:
        """A value the model has and the database does not is a broken write."""
        declared = {member.name for member in MODEL_ENUMS[enum_name]}
        in_the_database = _values_in_the_migrations(enum_name)

        missing = declared - in_the_database
        assert not missing, (
            f"{enum_name} is missing {sorted(missing)} in the database. "
            "A write with one of those values fails. Add a migration."
        )

    @pytest.mark.parametrize("enum_name", sorted(MODEL_ENUMS))
    def test_every_value_the_model_declares_is_written_as_a_name(self, enum_name: str) -> None:
        """The database stores the name of the value, not its value.

        SQLAlchemy writes the name of a Python enum member by default, so
        the label in the database has to be the name and not the value.
        """
        for member in MODEL_ENUMS[enum_name]:
            assert member.name == member.name.upper()
            assert member.name.replace("_", "") != member.value.replace("_", "")


class TestTheRelationshipsAreEager:
    """A unit is always loaded with what it needs.

    A lazy relationship in an asynchronous session raises when it is
    touched outside a greenlet. That turns into a five hundred in the
    middle of a request, and the test suite cannot see it, because SQLite
    loads a relationship synchronously.
    """

    @pytest.mark.parametrize("name", ["sku", "inspections", "photos"])
    def test_the_relationship_is_loaded_with_the_unit(self, name: str) -> None:
        """Serialising a unit must never need a lazy load."""
        relationship = getattr(Unit, name)
        assert relationship.property.lazy == "selectin", (
            f"Unit.{name} is lazy. Reading it outside a greenlet raises, "
            "which becomes a five hundred in the middle of a request."
        )
