"""
The public storefront endpoints (Phase 10).

These are the only endpoints in the application that are meant to be read
by anybody at all. There is no sign-in: a browser on a train can call
them.

Two things are deliberate here. The tenant is fixed by the deployment
rather than by the caller, because a shop window does not take the
customer's word for whose stock it is showing. And the answers carry
nothing about the business: no serial, no return reason, no notes, no
cost, no confidence.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.db import current_org_uuid, get_session, set_session_org_id
from secondroute.storefront.schemas import ListingDetailRead, ListingListRead
from secondroute.storefront.service import get_listing, list_listings

router = APIRouter(prefix="/public", tags=["Public"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def public_org() -> uuid.UUID:
    """The organisation whose stock the storefront shows.

    The storefront is configured with the organisation it belongs to. A
    caller cannot choose: the shop window shows one shop's stock.

    Outside production the organisation can also be named with the
    development header, which is how a developer points a storefront at
    their own data.

    Returns:
        The organisation's id.

    Raises:
        HTTPException: When the storefront has no organisation to show.
    """
    configured = str(settings.PUBLIC_ORG_ID or "").strip()
    if configured:
        try:
            return uuid.UUID(configured)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The configured storefront organisation is not an identifier.",
            ) from exc

    current = current_org_uuid()
    if current is not None:
        return current

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="The storefront has nothing to show.",
    )


PublicOrgDep = Annotated[uuid.UUID, Depends(public_org)]


async def act_as(session: AsyncSession, org_id: uuid.UUID) -> AsyncSession:
    """Make the session act for the storefront's organisation.

    The tenant-isolation policies read the organisation from the
    connection, so the session has to be told which organisation the
    request is for before the query runs.

    This is called from the route rather than from a dependency, and that
    matters. A generator dependency that sits underneath another
    dependency is torn down as soon as the outer one returns, and
    ``get_session`` clears the organisation when it is torn down. The
    outer dependency would therefore hand the route a session with no
    organisation on it, and the policies would refuse every row.

    Args:
        session: The session.
        org_id: The organisation.

    Returns:
        The session, set to the organisation.
    """
    await set_session_org_id(session, org_id)
    return session


@router.get(
    "/listings",
    response_model=ListingListRead,
    summary="The devices that are for sale",
)
async def public_listings(  # noqa: PLR0913, PLR0917
    session: SessionDep,
    org_id: PublicOrgDep,
    family: Annotated[str | None, Query(description="Restrict to one family")] = None,
    search: Annotated[str | None, Query(description="Restrict to matching models")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="How many to return")] = 24,
    offset: Annotated[int, Query(ge=0, description="How many to skip")] = 0,
) -> ListingListRead:
    """The devices that are on sale.

    Args:
        session: The database session.
        org_id: The organisation the storefront shows.
        family: Restrict to one family.
        search: Restrict to the models that match.
        limit: How many to return.
        offset: How many to skip.

    Returns:
        A page of listings.
    """
    await act_as(session, org_id)
    return await list_listings(
        session,
        org_id,
        family=family,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/listings/{listing_id}",
    response_model=ListingDetailRead,
    summary="One device, in full",
)
async def public_listing(
    listing_id: uuid.UUID,
    session: SessionDep,
    org_id: PublicOrgDep,
) -> ListingDetailRead:
    """One device, with its photographs and its test results.

    Args:
        listing_id: The identifier of the listing.
        session: The database session.
        org_id: The organisation the storefront shows.

    Returns:
        The listing.

    Raises:
        HTTPException: When there is no such listing.
    """
    await act_as(session, org_id)
    listing = await get_listing(session, org_id, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There is no such device on sale.",
        )
    return listing
