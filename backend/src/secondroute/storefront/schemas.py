"""
The shapes the storefront reads (Phase 10).

Every field here is something a buyer can be told. There is no field for
the serial number, the return reason, the operator's notes, the cost
breakdown or the engine's confidence, because a buyer can be told none of
those things and should not be able to read them either.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ListingPriceRead(BaseModel):
    """What the device is being offered at.

    The amount is the expected sale price from the decision, not the net:
    the net is what the business keeps, and the difference between the
    two is the business's margin.
    """

    amount: float = Field(..., description="The asking price, in the currency below.")
    currency: str = Field(default="USD", description="The currency of the price.")
    source: str = Field(
        ...,
        description="Where the price came from. ``synthetic`` means the price was modelled.",
    )
    as_of: str | None = Field(
        default=None,
        description="When the price was current, as an ISO timestamp.",
    )
    is_estimate: bool = Field(
        default=True,
        description=(
            "True when the price is a modelled expectation rather than an "
            "asking price somebody has set."
        ),
    )


class ListingPhotoRead(BaseModel):
    """One photograph of the device."""

    url: str = Field(..., description="The path the photograph is served from.")
    alt: str = Field(..., description="What the photograph shows.")


class ListingCheckRead(BaseModel):
    """One functional test."""

    name: str = Field(..., description="What was tested.")
    passed: bool = Field(..., description="Whether it passed.")


class ListingRead(BaseModel):
    """One device, for sale."""

    id: UUID = Field(..., description="The identifier of the listing.")
    title: str = Field(..., description="The name of the device, in the shop's words.")
    category: str = Field(
        default="laptop", description="The kind of device: phone, tv, refrigerator and so on."
    )
    category_label: str = Field(default="Laptops", description="The category, for a person.")
    summary: str = Field(
        default="", description="One line about the device, in the words a buyer uses."
    )
    family: str = Field(..., description="The family the device belongs to.")
    model_name: str = Field(..., description="The model of the device.")
    year: str = Field(..., description="The year of the model.")
    storage_gb: str = Field(..., description="How much storage the device has.")
    ram_gb: str = Field(..., description="How much memory the device has.")
    color: str = Field(..., description="The colour of the device.")
    grade: str = Field(..., description="The cosmetic grade, A to D.")
    condition: str = Field(..., description="The grade in words a buyer understands.")
    battery_health_pct: str | None = Field(
        default=None, description="The battery health, as a percentage."
    )
    price: ListingPriceRead = Field(..., description="What it is being offered at.")
    photo: ListingPhotoRead | None = Field(default=None, description="The photograph on the card.")
    photo_count: int = Field(default=0, description="How many photographs there are.")
    listed_at: datetime = Field(..., description="When the device was listed.")
    in_stock: bool = Field(default=True, description="Whether the device is still available.")


class ListingDetailRead(ListingRead):
    """One device, in full."""

    photos: list[ListingPhotoRead] = Field(
        default_factory=list, description="Every photograph of the device."
    )
    accessories: list[str] = Field(default_factory=list, description="What is in the box.")
    checks: list[ListingCheckRead] = Field(
        default_factory=list, description="What was tested, and what the test said."
    )
    highlights: list[str] = Field(
        default_factory=list, description="The things worth saying about the device."
    )


class ListingCategoryRead(BaseModel):
    """One kind of device on sale, for the category filter."""

    key: str = Field(..., description="The category's identifier.")
    label: str = Field(..., description="The category, in the shop's words.")
    count: int = Field(default=0, description="How many devices of this kind are on sale.")


class ListingListRead(BaseModel):
    """A page of devices."""

    items: list[ListingRead] = Field(default_factory=list, description="The devices.")
    total: int = Field(default=0, description="How many there are altogether.")
    limit: int = Field(default=24, description="How many were asked for.")
    offset: int = Field(default=0, description="How many were skipped.")
    families: list[str] = Field(
        default_factory=list, description="The families on sale, for the filter."
    )
    categories: list[ListingCategoryRead] = Field(
        default_factory=list, description="The kinds of device on sale, for the filter."
    )
    synthetic: bool = Field(
        default=False,
        description=(
            "True when the prices on this page are modelled rather than "
            "observed. The page has to say so."
        ),
    )
