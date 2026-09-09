"""Connectors API router — OAuth connection flow, connector listing, and health."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.schemas.common import APIResponse
from packages.core.db.models import Connection, User
from packages.core.security.crypto import encrypt_token
from packages.connectors.google_auth import GoogleAuthManager, DEFAULT_GOOGLE_SCOPES
from packages.connectors.gmail.client import GmailConnector
from packages.connectors.gdrive.client import GDriveConnector
from packages.connectors.gcal.client import GCalConnector
from packages.connectors.gsheets.client import GSheetsConnector
from apps.api.deps import get_db, get_current_user

router = APIRouter()


class CallbackPayload(BaseModel):
    code: str
    state: Optional[str] = None


@router.get("", response_model=APIResponse)
async def list_connectors(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all installed connectors and their connection statuses."""
    # Query user's connections
    result = await db.execute(
        select(Connection).where(Connection.user_id == current_user.id)
    )
    user_conns = {c.provider: c for c in result.scalars().all()}

    # Probe connectors
    connectors_registry = [
        GmailConnector(),
        GDriveConnector(),
        GCalConnector(),
        GSheetsConnector(),
    ]

    items = []
    for c in connectors_registry:
        user_conn = user_conns.get("google")
        status_val = user_conn.status if user_conn else "DISCONNECTED"
        account_email = user_conn.account_email if user_conn else None

        items.append({
            "connector_id": c.connector_id,
            "name": c.name,
            "version": c.version,
            "status": status_val,
            "account_email": account_email,
            "capabilities": c.get_capabilities(),
        })

    return APIResponse(
        ok=True,
        data={"connectors": items},
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.get("/google/auth-url", response_model=APIResponse)
async def get_google_auth_url(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Generate Google OAuth 2.0 consent screen URL."""
    auth_mgr = GoogleAuthManager()
    state = f"user_{current_user.id}_{uuid4().hex[:8]}"
    auth_url = auth_mgr.get_authorization_url(state=state)

    return APIResponse(
        ok=True,
        data={"auth_url": auth_url, "state": state},
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/google/callback", response_model=APIResponse)
async def google_oauth_callback(
    payload: CallbackPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Handle OAuth callback, exchange authorization code, and store encrypted tokens."""
    auth_mgr = GoogleAuthManager()
    tokens = await auth_mgr.exchange_code(payload.code)

    now = datetime.now(timezone.utc)
    expires_in = tokens.get("expires_in", 3600)
    expires_at = now + timedelta(seconds=expires_in)

    # Check existing connection
    result = await db.execute(
        select(Connection).where(
            Connection.user_id == current_user.id,
            Connection.provider == "google",
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        conn = Connection(
            user_id=current_user.id,
            provider="google",
            account_email=tokens.get("account_email", "unknown@gmail.com"),
            scopes=DEFAULT_GOOGLE_SCOPES,
            access_token_encrypted=encrypt_token(tokens["access_token"]),
            refresh_token_encrypted=encrypt_token(tokens.get("refresh_token", "")),
            expires_at=expires_at,
            status="ONLINE",
            metadata_json={"connected_at": now.isoformat()},
        )
        db.add(conn)
    else:
        conn.account_email = tokens.get("account_email", conn.account_email)
        conn.access_token_encrypted = encrypt_token(tokens["access_token"])
        if tokens.get("refresh_token"):
            conn.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
        conn.expires_at = expires_at
        conn.status = "ONLINE"

    await db.commit()

    return APIResponse(
        ok=True,
        data={
            "status": "connected",
            "provider": "google",
            "account_email": conn.account_email,
        },
        trace_id=getattr(request.state, "trace_id", None),
    )

