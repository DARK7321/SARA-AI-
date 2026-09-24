"""Google OAuth 2.0 authorization and token management for OmniBrain."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.settings import get_settings
from packages.core.db.models import Connection
from packages.core.security.crypto import encrypt_token, decrypt_token

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

DEFAULT_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GoogleAuthManager:
    """Manages Google OAuth2 authorization, token exchange, and automatic refresh."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = "http://localhost:8000/v1/connectors/google/callback",
    ):
        settings = get_settings()
        self.client_id = client_id or getattr(settings, "GOOGLE_CLIENT_ID", "") or "mock-google-client-id"
        self.client_secret = client_secret or getattr(settings, "GOOGLE_CLIENT_SECRET", "") or "mock-google-secret"
        self.redirect_uri = redirect_uri
        self.owner_email = getattr(settings, "OWNER_EMAIL", "") or "you@example.com"

    def get_authorization_url(
        self,
        state: str,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """Generate Google OAuth 2.0 consent screen URL."""
        scope_str = " ".join(scopes or DEFAULT_GOOGLE_SCOPES)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope_str,
            "access_type": "offline",
            "prompt": "select_account consent",
            "login_hint": self.owner_email,
            "state": state,
        }
        return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        # Check if running in mock/offline test mode
        if self.client_id.startswith("mock-") or code.startswith("mock-code"):
            return {
                "access_token": "mock-google-access-token",
                "refresh_token": "mock-google-refresh-token",
                "expires_in": 3600,
                "scope": " ".join(DEFAULT_GOOGLE_SCOPES),
                "account_email": self.owner_email,
            }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Fetch account email using access token
            email = "unknown@gmail.com"
            try:
                userinfo_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {data['access_token']}"},
                )
                if userinfo_resp.status_code == 200:
                    email = userinfo_resp.json().get("email", email)
            except Exception:
                pass

            data["account_email"] = email
            return data

    async def get_valid_access_token(
        self,
        connection: Connection,
        session: AsyncSession,
    ) -> str:
        """Return a valid, decrypted access token, automatically refreshing if expired."""
        now = datetime.now(timezone.utc)

        # If token has > 2 minutes remaining, return active token
        if connection.expires_at and connection.expires_at > (now + timedelta(minutes=2)):
            if connection.access_token_encrypted:
                return decrypt_token(connection.access_token_encrypted)

        # Otherwise refresh token
        refresh_token = decrypt_token(connection.refresh_token_encrypted or "")
        if not refresh_token:
            connection.status = "AUTH_FAILURE"
            await session.flush()
            raise ValueError("Refresh token missing; re-authentication required.")

        # If in mock mode
        if self.client_id.startswith("mock-") or refresh_token.startswith("mock-"):
            new_access_token = f"mock-refreshed-token-{int(now.timestamp())}"
            connection.access_token_encrypted = encrypt_token(new_access_token)
            connection.expires_at = now + timedelta(seconds=3600)
            connection.status = "ONLINE"
            await session.flush()
            return new_access_token

        # Live Google token refresh
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            if resp.status_code != 200:
                connection.status = "AUTH_FAILURE"
                await session.flush()
                raise ValueError("Failed to refresh Google token; re-auth required.")

            data = resp.json()
            new_access_token = data["access_token"]
            expires_in = data.get("expires_in", 3600)

            connection.access_token_encrypted = encrypt_token(new_access_token)
            connection.expires_at = now + timedelta(seconds=expires_in)
            connection.status = "ONLINE"
            await session.flush()
            return new_access_token

