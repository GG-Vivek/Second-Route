"""
Authentication API routes for Phase 5.

Provides OIDC authentication via Keycloak, session management, and user/org management.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from secondroute.core.config import settings
from secondroute.core.db import get_session
from secondroute.identity.organizations import Organization, User, ROLE_INSPECTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_ANALYST, ROLES
from secondroute.auth.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationRead,
    UserCreate,
    UserUpdate,
    UserRead,
    TokenResponse,
    LoginRequest,
    TokenRefreshRequest,
    ROLE_INSPECTOR,
    ROLE_MANAGER,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLES,
    has_permission,
    can_access,
)
from secondroute.auth.service import get_keycloak_service, KeycloakService, SessionManager

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
    keycloak: KeycloakService = Depends(get_keycloak_service),
) -> User:
    """Get current authenticated user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = keycloak.verify_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await session.execute(
        select(User).where(User.email == token_data.email)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
    keycloak: KeycloakService = Depends(get_keycloak_service),
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None

    try:
        token_data = keycloak.verify_token(credentials.credentials)
        result = await session.execute(
            select(User).where(User.email == token_data.email)
        )
        return result.scalar_one_or_none()
    except Exception:
        return None


# ========================================================================
# Keycloak OIDC Endpoints
# ========================================================================

@router.get(
    "/login",
    summary="Initiate Keycloak login",
)
async def login(
    request: Request,
    redirect_uri: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    keycloak: KeycloakService = Depends(get_keycloak_service),
) -> RedirectResponse:
    """
    Initiate Keycloak OIDC login flow.

    Redirects user to Keycloak authorization endpoint.
    """
    redirect = redirect_uri or f"{settings.FRONTEND_URL}/callback"
    auth_url = keycloak.get_authorization_url(redirect, state)
    return RedirectResponse(url=auth_url)


@router.get(
    "/callback",
    summary="OIDC callback - exchange code for tokens",
)
async def callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    keycloak: KeycloakService = Depends(get_keycloak_service),
) -> Response:
    """
    Handle OIDC callback - exchange authorization code for tokens.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error} - {error_description}",
        )

    redirect_uri = f"{settings.FRONTEND_URL}/callback"
    tokens = await keycloak.exchange_code_for_tokens(code, redirect_uri)

    # Get user info
    userinfo = await keycloak.get_userinfo(tokens["access_token"])

    # Create or get user in database (would need DB session here)
    # For now, just set cookies and redirect to frontend
    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")

    # Set secure cookies
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=1800,  # 30 minutes
    )
    if "refresh_token" in tokens:
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
            max_age=604800,  # 7 days
        )

    return response


@router.post(
    "/logout",
    summary="Logout and revoke session",
)
async def logout(
    request: Request,
    response: Response,
    keycloak: KeycloakService = Depends(get_keycloak_service),
) -> Response:
    """
    Logout user and revoke session.
    """
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")

    # Revoke tokens in Keycloak
    if refresh_token:
        await keycloak.logout(refresh_token)

    # Clear cookies
    response = Response(content='{"message": "Logged out"}', media_type="application/json")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("session")

    return response


@router.get(
    "/.well-known/openid-configuration",
    summary="OIDC Discovery Document",
)
async def oidc_discovery(keycloak: KeycloakService = Depends(get_keycloak_service)) -> dict:
    """
    OIDC Discovery Document.
    """
    return await keycloak.get_discovery_document()


@router.get(
    "/.well-known/jwks.json",
    summary="JWKS Endpoint",
)
async def jwks(keycloak: KeycloakService = Depends(get_keycloak_service)) -> dict:
    """
    JSON Web Key Set endpoint.
    """
    return await keycloak.get_jwks()


# ========================================================================
# Organization Management
# ========================================================================

org_router = APIRouter(prefix="/orgs", tags=["Organizations"])


@org_router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
)
async def create_organization(
    org_data: OrganizationCreate,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    """Create a new organization."""
    org = Organization(
        name=org_data.name,
        risk_profile=org_data.risk_profile,
    )
    session.add(org)
    await session.flush()
    await session.refresh(org)
    return OrganizationRead.model_validate(org)


@org_router.get(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Get organization by ID",
)
async def get_organization(
    org_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    """Get organization by ID."""
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return OrganizationRead.model_validate(org)


@org_router.get(
    "",
    response_model=List[OrganizationRead],
    summary="List organizations",
)
async def list_organizations(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> List[OrganizationRead]:
    """List all organizations."""
    result = await session.execute(
        select(Organization).order_by(Organization.created_at.desc()).limit(limit).offset(offset)
    )
    orgs = result.scalars().all()
    return [OrganizationRead.model_validate(org) for org in orgs]


@org_router.patch(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Update organization",
)
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    session: AsyncSession = Depends(get_session),
) -> OrganizationRead:
    """Update organization."""
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if org_data.name is not None:
        org.name = org_data.name
    if org_data.risk_profile is not None:
        org.risk_profile = org_data.risk_profile

    await session.flush()
    await session.refresh(org)
    return OrganizationRead.model_validate(org)


# ========================================================================
# User Management
# ========================================================================

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Get user by ID."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return UserRead.model_validate(user)


@user_router.get(
    "",
    response_model=List[UserRead],
    summary="List users",
)
async def list_users(
    org_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> List[UserRead]:
    """List users, optionally filtered by organization."""
    query = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if org_id:
        query = query.where(User.org_id == org_id)

    result = await session.execute(query)
    users = result.scalars().all()
    return [UserRead.model_validate(user) for user in users]


# Organization-scoped user management
org_user_router = APIRouter(prefix="/orgs/{org_id}/users", tags=["Organization Users"])


@org_user_router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create user in organization",
)
async def create_user(
    org_id: UUID,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Create a user in an organization."""
    # Verify org exists
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Validate role
    if user_data.role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(ROLES)}",
        )

    # Check for duplicate email
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        org_id=org_id,
        email=user_data.email,
        role=user_data.role,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return UserRead.model_validate(user)


@org_user_router.get(
    "",
    response_model=List[UserRead],
    summary="List users in organization",
)
async def list_org_users(
    org_id: UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> List[UserRead]:
    """List users in an organization."""
    # Verify org exists
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    result = await session.execute(
        select(User)
        .where(User.org_id == org_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    users = result.scalars().all()
    return [UserRead.model_validate(user) for user in users]


@org_user_router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update user in organization",
)
async def update_org_user(
    org_id: UUID,
    user_id: UUID,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Update a user in an organization."""
    # Verify org exists
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    user = await session.get(User, user_id)
    if not user or user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    # Validate role if provided
    if user_data.role and user_data.role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(ROLES)}",
        )

    # Check for duplicate email if changing
    if user_data.email and user_data.email != user.email:
        result = await session.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        user.email = user_data.email

    if user_data.role:
        user.role = user_data.role

    await session.flush()
    await session.refresh(user)
    return UserRead.model_validate(user)


@org_user_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user from organization",
)
async def delete_user(
    org_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a user from an organization."""
    user = await session.get(User, user_id)
    if not user or user.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this organization",
        )

    await session.delete(user)
    await session.flush()


# Sub-routers are registered directly in main.py with API_PREFIX
# router.include_router(org_router)
# router.include_router(user_router)
# router.include_router(org_user_router)
