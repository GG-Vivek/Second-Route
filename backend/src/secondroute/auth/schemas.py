"""
Pydantic schemas for the authentication module (Phase 5).
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    scopes_supported: list[str]
    response_types_supported: list[str]
    subject_types_supported: list[str]
    id_token_signing_alg_values_supported: list[str]


class JWKSResponse(BaseModel):
    """JWKS response."""

    keys: list[dict]


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


# Role constants.
#
# These are defined once, with the user model they belong to, and
# re-exported here so that the auth module has a single place to import
# them from. Two copies of the same constants is two places for a role
# name to drift.
from secondroute.identity.organizations import (  # noqa: F401
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_INSPECTOR,
    ROLE_MANAGER,
    ROLES,
)

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


# ========================================================================
# Sign-up and sign-in (accounts the application keeps itself)
# ========================================================================

#: The shortest password an account may have.
PASSWORD_MIN_LENGTH = 10
#: The longest, which keeps a hashing request from being a denial of service.
PASSWORD_MAX_LENGTH = 128


def _check_password_strength(value: str) -> str:
    """A password needs a letter and a digit, and to be long enough.

    Raises:
        ValueError: When the password is not strong enough. The message is
            the one the person sees, so it says what to change.
    """
    if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
        raise ValueError("The password needs at least one letter and one number.")
    return value


class RetailerSignUp(BaseModel):
    """A retailer creates its organisation, with an administrator account."""

    organisation_name: str = Field(
        ..., min_length=2, max_length=200, description="The name of the retailer."
    )
    display_name: str = Field(
        ..., min_length=1, max_length=120, description="The administrator's name."
    )
    email: EmailStr = Field(..., description="The administrator's email address.")
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description="The password. At least ten characters, with a letter and a number.",
    )
    risk_profile: str = Field(
        default="balanced",
        pattern="^(conservative|balanced|aggressive)$",
        description="How much risk the decision engine takes on the retailer's behalf.",
    )

    @field_validator("password")
    @classmethod
    def _password_is_strong(cls, value: str) -> str:
        return _check_password_strength(value)


class UserSignUp(BaseModel):
    """A person joins an existing retailer as an inspector."""

    invite_code: UUID = Field(
        ..., description="The retailer's code, which the retailer gives its staff."
    )
    display_name: str = Field(..., min_length=1, max_length=120, description="The person's name.")
    email: EmailStr = Field(..., description="The person's email address.")
    password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        description="The password. At least ten characters, with a letter and a number.",
    )

    @field_validator("password")
    @classmethod
    def _password_is_strong(cls, value: str) -> str:
        return _check_password_strength(value)


class SignIn(BaseModel):
    """An email address and the password for it."""

    email: EmailStr = Field(..., description="The email address the account was made with.")
    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)


class AccountRead(BaseModel):
    """The account a person has just made, or has signed in to."""

    id: UUID
    email: str
    display_name: str
    role: str
    org_id: UUID | None = None
    organisation_name: str | None = None
