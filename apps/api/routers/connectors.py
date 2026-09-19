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
    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    callback_url = f"{base_url}/v1/connectors/google/callback"

    auth_mgr = GoogleAuthManager(redirect_uri=callback_url)
    state = f"user_{current_user.id}_{uuid4().hex[:8]}"
    auth_url = auth_mgr.get_authorization_url(state=state)

    return APIResponse(
        ok=True,
        data={"auth_url": auth_url, "state": state},
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.api_route("/google/callback", methods=["GET", "POST"], response_model=APIResponse)
async def google_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    payload: Optional[CallbackPayload] = None,
):
    """Handle Google OAuth callback requests from either the browser or the API client."""
    query_params = dict(request.query_params)
    code = query_params.get("code") or (payload.code if payload else None)
    state = query_params.get("state") or (payload.state if payload else None)

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    try:
        user_id_str = state.split("_")[1]
        user_id = UUID(user_id_str)
    except (IndexError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    base_url = str(request.base_url).rstrip("/")
    if "onrender.com" in base_url and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://", 1)
    callback_url = f"{base_url}/v1/connectors/google/callback"

    auth_mgr = GoogleAuthManager(redirect_uri=callback_url)
    tokens = await auth_mgr.exchange_code(code)

    now = datetime.now(timezone.utc)
    expires_in = tokens.get("expires_in", 3600)
    expires_at = now + timedelta(seconds=expires_in)

    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user_id,
            Connection.provider == "google",
        )
    )
    conn = result.scalar_one_or_none()

    if not conn:
        conn = Connection(
            user_id=user_id,
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

    if request.method == "GET":
        from fastapi.responses import HTMLResponse
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sara - Google Connected</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #030712;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            max-width: 440px;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.7);
        }}
        .icon {{ font-size: 52px; margin-bottom: 12px; }}
        h1 {{ font-size: 22px; margin: 0 0 10px; color: #38bdf8; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin: 8px 0; }}
        .badge {{
            display: inline-block;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 9999px;
            padding: 6px 16px;
            font-size: 13px;
            font-weight: 600;
            margin: 16px 0;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✨</div>
        <h1>Google Workspace Connected!</h1>
        <p>Aapka Gmail account Sara AI assistant ke sath successfully connect ho gaya hai.</p>
        <div class="badge">✅ {conn.account_email}</div>
        <p style="font-size: 12px; color: #64748b; margin-top: 20px;">
            Aap is browser tab ko band kar sakte hain aur <b>Sara Desktop App</b> par wapas ja sakte hain.
        </p>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_content)

    return APIResponse(
        ok=True,
        data={
            "status": "connected",
            "provider": "google",
            "user_id": str(user_id),
            "account_email": conn.account_email,
        },
        trace_id=getattr(request.state, "trace_id", None),
    )

