"""
Pydantic schemas for the authentication module (Phase 5).
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, EmailStr


class OrganizationBase(BaseModel):
    """Base organization fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    risk_profile: str = Field(
        default="balanced",
        pattern="^(conservative|balanced|aggressive)$",
        description="Risk profile for decision engine",
    )


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    risk_profile: Optional[str] = Field(None, pattern="^(conservative|balanced|aggressive)$")


class OrganizationRead(OrganizationBase):
    """Schema for reading an organization."""

    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr = Field(..., description="User email address")
    role: str = Field(
        ...,
        pattern="^(inspector|manager|admin|analyst)$",
        description="User role",
    )


class UserCreate(UserBase):
    """Schema for creating a user."""

    org_id: UUID = Field(..., description="Organization ID")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    role: Optional[str] = Field(None, pattern="^(inspector|manager|admin|analyst)$")
    org_id: Optional[UUID] = None


class UserRead(UserBase):
    """Schema for reading a user."""

    id: UUID
    org_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Decoded token data."""

    sub: str
    email: str
    role: str
    org_id: Optional[UUID] = None
    exp: int


class OIDCDiscoveryResponse(BaseModel):
    """OIDC Discovery document."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: Optional[str] = None
    end_session_endpoint: Optional[str] = None
    scopes_supported: List[str]
    response_types_supported: List[str]
    subject_types_supported: List[str]
    id_token_signing_alg_values_supported: List[str]


class JWKSResponse(BaseModel):
    """JWKS response."""

    keys: List[dict]


class LoginRequest(BaseModel):
    """Login request (for password grant if used)."""

    username: str
    password: str


class LogoutRequest(BaseModel):
    """Logout request."""

    refresh_token: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str
    grant_type: str = "refresh_token"


# Role constants
ROLE_INSPECTOR = "inspector"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"

ROLES = (ROLE_INSPECTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_ANALYST)

ROLE_HIERARCHY = {
    ROLE_INSPECTOR: 1,
    ROLE_MANAGER: 2,
    ROLE_ANALYST: 3,
    ROLE_ADMIN: 4,
}

ROLE_PERMISSIONS = {
    ROLE_INSPECTOR: ["read:units", "read:inspections", "read:decisions", "create:inspections"],
    ROLE_MANAGER: [
        "read:units",
        "read:inspections",
        "read:decisions",
        "create:inspections",
        "read:analytics",
        "read:costs",
        "update:org",
    ],
    ROLE_ANALYST: [
        "read:units",
        "read:inspections",
        "read:decisions",
        "read:analytics",
        "read:calibration",
        "read:regret",
    ],
    ROLE_ADMIN: [
        "read:units",
        "read:inspections",
        "read:decisions",
        "create:inspections",
        "read:analytics",
        "read:calibration",
        "read:regret",
        "read:costs",
        "update:org",
        "manage:users",
        "manage:org",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])


def role_level(role: str) -> int:
    """Get the hierarchy level of a role (higher = more privileges)."""
    return ROLE_HIERARCHY.get(role, 0)


def can_access(role: str, required_role: str) -> bool:
    """Check if a role can access a resource requiring a minimum role."""
    return role_level(role) >= role_level(required_role)
