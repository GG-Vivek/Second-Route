"""
The mixed catalogue, the category helpers, and the handling of devices with
no battery (F11.2 to F11.4).
"""

import csv
import io
from pathlib import Path

import pytest

from secondroute.identity.categories import CATEGORIES, category_of, storage_label
from secondroute.condition.grades import NO_BATTERY_SCORE, InspectionSignals, condition_score
from secondroute.intake.schemas import InspectionBase

SEED = Path(__file__).resolve().parents[2] / "data" / "seeds" / "skus.csv"


def test_every_seeded_device_names_a_known_category() -> None:
    rows = list(csv.DictReader(SEED.read_text(encoding="utf-8").splitlines()))
    assert rows, "the catalogue is empty"
    for row in rows:
        import json

        specs = json.loads(row["specs_json"])
        assert specs["category"] in CATEGORIES, row["model_name"]
        assert specs.get("summary"), f"{row['model_name']} has no summary for the card"
        assert row["source"] and row["as_of"], "every row carries its source and date"


def test_the_catalogue_is_not_laptops_only() -> None:
    rows = list(csv.DictReader(SEED.read_text(encoding="utf-8").splitlines()))
    import json

    kinds = {json.loads(row["specs_json"])["category"] for row in rows}
    for expected in (
        "phone",
        "tv",
        "refrigerator",
        "console",
        "mixer",
        "ac",
        "purifier",
        "hairdryer",
    ):
        assert expected in kinds


def test_a_missing_or_unknown_category_is_a_laptop() -> None:
    # Rows loaded before categories existed were all laptops.
    assert category_of(None).key == "laptop"
    assert category_of({}).key == "laptop"
    assert category_of({"category": "toaster"}).key == "laptop"
    assert category_of({"category": "tv"}).key == "tv"


def test_storage_is_read_as_a_buyer_reads_it() -> None:
    assert storage_label("256") == "256 GB"
    assert storage_label("1TB") == "1TB"
    assert storage_label("") == ""
    assert storage_label(None) == ""


def test_devices_without_a_battery_are_not_expected_to_have_one() -> None:
    assert not CATEGORIES["refrigerator"].has_battery
    assert not CATEGORIES["tv"].has_battery
    assert CATEGORIES["phone"].has_battery


def test_a_device_with_no_battery_scores_as_neutral_not_as_dead() -> None:
    with_none = InspectionSignals(battery_health_pct=None, cosmetic_grade="B")
    at_middle = InspectionSignals(battery_health_pct=50.0 + 0.5 * 50.0, cosmetic_grade="B")
    # The middle of the battery scale is the score a device with no battery gets.
    assert condition_score(with_none) == pytest.approx(condition_score(at_middle))
    assert NO_BATTERY_SCORE == 0.5


def test_an_inspection_may_omit_the_battery_reading() -> None:
    inspection = InspectionBase(cosmetic_grade="B")
    assert inspection.battery_health_pct is None


def test_a_battery_reading_is_still_checked_when_given() -> None:
    with pytest.raises(ValueError):
        InspectionBase(cosmetic_grade="B", battery_health_pct="140")


def test_every_category_draws_a_photograph_from_every_angle() -> None:
    from PIL import Image

    from scripts.device_photos import ANGLES, make_device_photo

    for category in CATEGORIES:
        for angle in ANGLES:
            data = make_device_photo(
                serial="C02TEST", body_colour=(40, 40, 44), angle=angle, seed=1, category=category
            )
            image = Image.open(io.BytesIO(data))
            assert image.format == "JPEG"
            assert image.size == (1200, 900)
