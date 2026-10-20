"""
Authentication module for Phase 5.

Provides OIDC authentication via Keycloak, session management, and RBAC.
"""

from secondroute.auth.api import router as auth_router

__all__ = ["auth_router"]
