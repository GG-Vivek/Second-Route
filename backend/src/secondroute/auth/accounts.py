"""
Sign-up and sign-in for the accounts the application keeps itself (F11.1).

A retailer signs up and gets an organisation, with an administrator who
manages it. A person signs up with the retailer's code and joins it as an
inspector. Both then sign in with an email and a password.

The application's own accounts sit beside the identity provider rather than
replacing it. An account made here carries a password hash, and the identity
provider's accounts do not. In production the sign-in is meant to be the
identity provider's, and this is the path for a deployment that has none.

Signing in returns the account, including the organisation it acts for. It does
not issue a token: the operator console names its organisation on each request,
as it always has outside production.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.auth.schemas import AccountRead, RetailerSignUp, SignIn, UserSignUp
from secondroute.core.db import get_session, set_session_org_id
from secondroute.identity.organizations import (
    ROLE_ADMIN,
    ROLE_INSPECTOR,
    Organization,
    User,
)
from secondroute.identity.passwords import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Accounts"])

#: A hash checked when the email is not known, so that an unknown address takes
#: as long to refuse as a wrong password does. Otherwise the timing says which
#: addresses have accounts.
_NO_ACCOUNT_HASH = hash_password("not-a-real-account-0")


def _normal_email(value: str) -> str:
    """Email addresses are compared without regard to case or stray spaces."""
    return str(value).strip().lower()


async def _email_is_free(session: AsyncSession, email: str) -> None:
    """Refuse an address that already has an account.

    Raises:
        HTTPException: 409 when the address is taken.
    """
    existing = await session.execute(select(User.id).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for that email address.",
        )


def _account(user: User, organisation: Organization | None) -> AccountRead:
    """Describe an account, without anything that would let it be signed in to."""
    return AccountRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name or "",
        role=user.role,
        org_id=user.org_id,
        organisation_name=organisation.name if organisation is not None else None,
    )


@router.post(
    "/signup/retailer",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a retailer: its organisation and its administrator",
)
async def sign_up_retailer(
    body: RetailerSignUp,
    session: AsyncSession = Depends(get_session),
) -> AccountRead:
    """Create the organisation, and the administrator who runs it."""
    email = _normal_email(body.email)
    await _email_is_free(session, email)

    # The organisation is created acting as itself, which is what the
    # tenancy policies expect of a tenant creating itself.
    organisation = Organization(
        id=uuid4(),
        name=body.organisation_name.strip(),
        risk_profile=body.risk_profile,
    )
    session.add(organisation)
    await set_session_org_id(session, str(organisation.id))

    user = User(
        org_id=organisation.id,
        email=email,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
        role=ROLE_ADMIN,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for that email address.",
        ) from exc
    await session.refresh(user)
    return _account(user, organisation)


@router.post(
    "/signup/user",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a person as an inspector of an existing retailer",
)
async def sign_up_user(
    body: UserSignUp,
    session: AsyncSession = Depends(get_session),
) -> AccountRead:
    """Join a retailer, with the code it gave you."""
    organisation = await session.get(Organization, body.invite_code)
    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That retailer code is not recognised. Check it with the retailer.",
        )

    email = _normal_email(body.email)
    await _email_is_free(session, email)
    await set_session_org_id(session, str(organisation.id))

    user = User(
        org_id=organisation.id,
        email=email,
        display_name=body.display_name.strip(),
        password_hash=hash_password(body.password),
        role=ROLE_INSPECTOR,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already exists for that email address.",
        ) from exc
    await session.refresh(user)
    return _account(user, organisation)


@router.post(
    "/signin",
    response_model=AccountRead,
    summary="Sign in with an email address and a password",
)
async def sign_in(
    body: SignIn,
    session: AsyncSession = Depends(get_session),
) -> AccountRead:
    """Check the password, and return the account it belongs to."""
    email = _normal_email(body.email)
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if user is None:
        # Spend the same time as a real check, then refuse.
        verify_password(body.password, _NO_ACCOUNT_HASH)
        raise _wrong_credentials()
    if not verify_password(body.password, user.password_hash):
        raise _wrong_credentials()

    organisation = await session.get(Organization, user.org_id) if user.org_id else None
    return _account(user, organisation)


def _wrong_credentials() -> HTTPException:
    """The one answer for a wrong email or a wrong password, so they cannot be told apart."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="The email address or the password is not right.",
        headers={"WWW-Authenticate": "Basic"},
    )
