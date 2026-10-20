"""
Authentication service for Phase 5.

Provides Keycloak OIDC integration, session management, and token handling.
"""

import json
import time
from typing import Optional, Dict, Any
from uuid import UUID

import httpx
from jose import jwt, JWTError
from pydantic import BaseModel

from secondroute.core.config import settings


class KeycloakConfig(BaseModel):
    """Keycloak configuration."""

    base_url: str
    realm: str
    client_id: str
    client_secret: str

    @property
    def issuer(self) -> str:
        return f"{self.base_url}/realms/{self.realm}"

    @property
    def auth_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/auth"

    @property
    def token_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/userinfo"

    @property
    def logout_endpoint(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/logout"

    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def discovery_uri(self) -> str:
        return f"{self.issuer}/.well-known/openid-configuration"


class TokenData(BaseModel):
    """Decoded token data."""

    sub: str
    email: str
    role: str
    org_id: Optional[str] = None
    exp: int
    iat: int
    aud: Optional[str] = None


class KeycloakService:
    """Keycloak OIDC integration service."""

    def __init__(self):
        self.config = KeycloakConfig(
            base_url=settings.OIDC_BASE_URL or "http://localhost:8080",
            realm=settings.OIDC_REALM or "secondroute",
            client_id=settings.OIDC_CLIENT_ID or "secondroute",
            client_secret=settings.OIDC_CLIENT_SECRET or "dev-secret",
        )
        self._jwks_cache: Optional[dict] = None
        self._jwks_cache_time: float = 0

    async def get_discovery_document(self) -> dict[str, Any]:
        """Get OIDC discovery document."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.discovery_uri)
            response.raise_for_status()
            return response.json()

    async def get_jwks(self) -> dict[str, Any]:
        """Get JWKS with caching."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache_time) < 3600:  # 1 hour cache
            return self._jwks_cache

        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = time.time()
            return self._jwks_cache

    async def get_public_keys(self) -> dict[str, Any]:
        """Get public keys for JWT verification."""
        jwks = await self.get_jwks()
        keys = {}
        for key in jwks.get("keys", []):
            kid = key.get("kid")
            if kid:
                keys[kid] = key
        return keys

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token."""
        try:
            # Get public keys
            import asyncio
            keys = asyncio.run(self.get_public_keys())

            # Get the key ID from the token header
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise JWTError("Token missing key ID")

            key = asyncio.run(self.get_public_keys()).get(kid)
            if not key:
                raise JWTError(f"Key not found for kid: {kid}")

            # Verify and decode
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.OIDC_CLIENT_ID,
                issuer=self.config.issuer,
            )
            return TokenData(**payload)
        except JWTError as e:
            raise ValueError(f"Invalid token: {e}")

    async def exchange_code_for_tokens(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def logout(self, refresh_token: Optional[str] = None) -> None:
        """Logout from Keycloak."""
        if not refresh_token:
            return

        async with httpx.AsyncClient() as client:
            await client.post(
                self.config.logout_endpoint,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate Keycloak authorization URL."""
        from urllib.parse import urlencode

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile email roles",
        }
        if state:
            params["state"] = state

        return f"{self.config.auth_endpoint}?{urlencode(params)}"

    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Get user info from Keycloak."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


class SessionManager:
    """Session management using Redis."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def create_session(
        self,
        user_id: UUID,
        org_id: UUID,
        role: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 1800,  # 30 minutes
    ) -> str:
        """Create a new session."""
        import uuid
        session_id = str(uuid.uuid4())

        session_data = {
            "user_id": str(user_id),
            "org_id": str(org_id),
            "role": role,
            "access_token": access_token,
            "refresh_token": refresh_token or "",
            "created_at": time.time(),
        }

        await self.redis.setex(
            f"session:{session_id}",
            expires_in,
            json.dumps(session_data),
        )

        # Also store mapping from user_id to session_id for revocation
        await self.redis.sadd(f"user_sessions:{user_id}", session_id)

        return session_id

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        data = await self.redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        session_data = await self.get_session(session_id)
        if session_data:
            user_id = session_data.get("user_id")
            if user_id:
                await self.redis.srem(f"user_sessions:{user_id}", session_id)
        await self.redis.delete(f"session:{session_id}")

    async def revoke_user_sessions(self, user_id: UUID) -> int:
        """Revoke all sessions for a user."""
        session_ids = await self.redis.smembers(f"user_sessions:{user_id}")
        count = 0
        for session_id in session_ids:
            await self.delete_session(session_id)
            count += 1
        return count

    async def refresh_session(self, session_id: str, expires_in: int = 1800) -> bool:
        """Extend session expiry."""
        data = await self.get_session(session_id)
        if data:
            await self.redis.setex(
                f"session:{session_id}",
                expires_in,
                json.dumps(data),
            )
            return True
        return False


def get_keycloak_service() -> KeycloakService:
    """Get Keycloak service instance."""
    return KeycloakService()
