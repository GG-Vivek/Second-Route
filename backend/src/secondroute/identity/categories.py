"""
Product categories: the kinds of device the shop sells.

A category is what a device is, in the words a buyer uses: a phone, a TV, a
refrigerator. The category decides which functional tests an inspector runs,
which accessories are expected in the box, and whether the device has a
battery worth reporting. It is stored in the SKU's ``specs_json`` under the
``category`` key, so adding a category is a data change and not a schema
migration.

Rows loaded before categories existed carry no category. Every one of them
was a laptop, so a missing category means ``laptop``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

__all__ = [
    "CATEGORIES",
    "DEFAULT_CATEGORY",
    "Category",
    "category_of",
    "storage_label",
]


@dataclass(frozen=True, slots=True)
class Category:
    """One kind of device.

    Attributes:
        key: The stable identifier stored in ``specs_json``.
        label: The plural name shown on the shop's filters.
        singular: The name of one device of this kind.
        has_battery: Whether a battery health reading means anything.
        tests: The functional tests an inspector runs on this kind of device.
        accessories: What is expected to come back in the box.
    """

    key: str
    label: str
    singular: str
    has_battery: bool
    tests: tuple[str, ...]
    accessories: tuple[str, ...]


_ELECTRONICS_ACCESSORIES: Final[tuple[str, ...]] = ("charger", "cable", "box", "manual")
_APPLIANCE_ACCESSORIES: Final[tuple[str, ...]] = ("manual", "box", "accessory kit", "warranty card")

CATEGORIES: Final[dict[str, Category]] = {
    category.key: category
    for category in (
        Category(
            key="laptop",
            label="Laptops",
            singular="laptop",
            has_battery=True,
            tests=("display", "keyboard", "ports", "camera", "audio", "wifi", "battery", "boot"),
            accessories=_ELECTRONICS_ACCESSORIES,
        ),
        Category(
            key="phone",
            label="Phones",
            singular="phone",
            has_battery=True,
            tests=("display", "touch", "ports", "camera", "audio", "wifi", "battery", "boot"),
            accessories=_ELECTRONICS_ACCESSORIES,
        ),
        Category(
            key="tablet",
            label="Tablets",
            singular="tablet",
            has_battery=True,
            tests=("display", "touch", "ports", "camera", "audio", "wifi", "battery", "boot"),
            accessories=_ELECTRONICS_ACCESSORIES,
        ),
        Category(
            key="tv",
            label="TVs",
            singular="TV",
            has_battery=False,
            tests=("picture", "sound", "ports", "wifi", "remote", "boot"),
            accessories=("remote", "power cable", "stand", "manual"),
        ),
        Category(
            key="refrigerator",
            label="Refrigerators",
            singular="refrigerator",
            has_battery=False,
            tests=("cooling", "freezing", "door seal", "fans", "controls"),
            accessories=_APPLIANCE_ACCESSORIES,
        ),
        Category(
            key="washer",
            label="Washers",
            singular="washing machine",
            has_battery=False,
            tests=("drum", "spin", "drain", "door lock", "controls"),
            accessories=_APPLIANCE_ACCESSORIES,
        ),
        Category(
            key="mixer",
            label="Mixer grinders",
            singular="mixer grinder",
            has_battery=False,
            tests=("motor", "speed control", "jar seal", "safety lock", "noise"),
            accessories=("jar", "blades", "lid", "manual"),
        ),
        Category(
            key="ac",
            label="Air conditioners",
            singular="air conditioner",
            has_battery=False,
            tests=("cooling", "airflow", "filter", "remote", "drainage", "controls"),
            accessories=("remote", "filter", "installation kit", "manual"),
        ),
        Category(
            key="purifier",
            label="Air purifiers",
            singular="air purifier",
            has_battery=False,
            tests=("airflow", "filter", "sensor", "noise", "controls"),
            accessories=("filter", "power cable", "manual"),
        ),
        Category(
            key="hairdryer",
            label="Hair dryers",
            singular="hair dryer",
            has_battery=False,
            tests=("heat settings", "airflow", "attachments", "cord", "controls"),
            accessories=("diffuser", "concentrator", "pouch", "manual"),
        ),
        Category(
            key="console",
            label="Game consoles",
            singular="game console",
            has_battery=False,
            tests=("boot", "controller", "ports", "wifi", "fan"),
            accessories=("controller", "power cable", "hdmi cable", "box"),
        ),
        Category(
            key="audio",
            label="Headphones",
            singular="pair of headphones",
            has_battery=True,
            tests=(
                "left driver",
                "right driver",
                "microphone",
                "noise cancelling",
                "bluetooth",
                "battery",
            ),
            accessories=("case", "cable", "box"),
        ),
        Category(
            key="camera",
            label="Cameras",
            singular="camera",
            has_battery=True,
            tests=("shutter", "sensor", "lens mount", "display", "battery"),
            accessories=("battery", "charger", "strap", "box"),
        ),
    )
}

#: The category a row has when it does not name one. Every row loaded before
#: categories existed was a laptop.
DEFAULT_CATEGORY: Final[str] = "laptop"


def category_of(specs: Mapping[str, Any] | None) -> Category:
    """Return the category a device's specifications name.

    An unknown or missing category falls back to the default, so that a
    typo in the catalogue produces a sensible device and not a crash.

    Args:
        specs: The SKU's ``specs_json``, or None.

    Returns:
        The category.
    """
    key = specs.get("category") if isinstance(specs, Mapping) else None
    if isinstance(key, str) and key in CATEGORIES:
        return CATEGORIES[key]
    return CATEGORIES[DEFAULT_CATEGORY]


def storage_label(value: str | None) -> str:
    """Return a storage capacity as a buyer reads it.

    The catalogue stores capacity as text. A bare number is a count of
    gigabytes, so ``"256"`` reads as ``"256 GB"``. Anything else, such as
    ``"1TB"``, is already a label and is returned as it is.

    Args:
        value: The capacity as stored.

    Returns:
        The label, or an empty string when there is no capacity.
    """
    text = (value or "").strip()
    if not text:
        return ""
    if text.isdigit():
        return f"{text} GB"
    return text
