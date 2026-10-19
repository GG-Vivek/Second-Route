"""
Tenancy and actor models.

The ``organizations`` and ``users`` tables are the primitives that every other
table references. Their behaviour - authentication, roles, row-level security
- arrives in Phase 5, but the tables themselves must exist from the start
because the Phase 1 and Phase 2 tables carry foreign keys to them.

The definitions live here (rather than in ``identity.models``) so the Phase 2
work does not collide with the Phase 1 work in that package.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secondroute.core.db import Base

#: The roles the Phase 5 authentication layer recognises.
ROLE_INSPECTOR = "inspector"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"
ROLE_ANALYST = "analyst"

ROLES = (ROLE_INSPECTOR, ROLE_MANAGER, ROLE_ADMIN, ROLE_ANALYST)


class Organization(Base):
    """A tenant. Every operational table is scoped to one."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    risk_profile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name})>"


class User(Base):
    """An actor inside an organisation.

    The role column is a plain string until Phase 5 replaces it with the
    Keycloak role mapping.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default=ROLE_INSPECTOR)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
