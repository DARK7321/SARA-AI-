"""Natural Language Aliases REST API router for OmniBrain."""
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.schemas.common import APIResponse
from packages.core.db.models import User, Alias, Workflow
from apps.api.deps import get_db, get_current_user

router = APIRouter()

DEFAULT_ALIASES = [
    {
        "id": "builtin-morning",
        "name": "morning",
        "target_type": "workflow",
        "target_id": "Morning Standup Briefing",
        "description": "Runs daily morning inbox & calendar briefing",
        "is_builtin": True,
        "is_active": True,
    },
    {
        "id": "builtin-triage",
        "name": "triage",
        "target_type": "workflow",
        "target_id": "GitHub Issue & PR Triage",
        "description": "Triages open GitHub issues and posts to Slack",
        "is_builtin": True,
        "is_active": True,
    },
    {
        "id": "builtin-digest",
        "name": "digest",
        "target_type": "workflow",
        "target_id": "Web Intelligence Digest",
        "description": "Extracts latest tech articles and appends to Sheets",
        "is_builtin": True,
        "is_active": True,
    },
    {
        "id": "builtin-status",
        "name": "status",
        "target_type": "quick_action",
        "target_id": "system_status",
        "description": "Instant telemetry and connectivity report",
        "is_builtin": True,
        "is_active": True,
    },
]


class CreateAliasPayload(BaseModel):
    name: str = Field(min_length=2, max_length=50, description="Trigger command or alias keyword")
    target_type: str = Field(description="Target type: 'workflow' or 'quick_action'")
    target_id: str = Field(description="Target workflow name/ID or action identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Optional default parameters")


@router.get("", response_model=APIResponse)
async def list_aliases(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available aliases including built-in and user-defined shortcuts."""
    res = await db.execute(
        select(Alias).where(Alias.user_id == current_user.id).order_by(Alias.created_at.desc())
    )
    user_aliases = res.scalars().all()

    formatted_user_aliases = [
        {
            "id": str(a.id),
            "name": a.name,
            "target_type": a.target_type,
            "target_id": a.target_id,
            "parameters": a.parameters,
            "is_active": a.is_active,
            "is_builtin": False,
            "created_at": a.created_at.isoformat(),
        }
        for a in user_aliases
    ]

    return APIResponse(
        ok=True,
        data={
            "aliases": DEFAULT_ALIASES + formatted_user_aliases,
            "count": len(DEFAULT_ALIASES) + len(formatted_user_aliases),
        },
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("", response_model=APIResponse)
async def create_alias(
    payload: CreateAliasPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new natural language alias shortcut."""
    clean_name = payload.name.strip().lower()

    # Check for duplicate
    res = await db.execute(
        select(Alias).where(Alias.user_id == current_user.id, Alias.name == clean_name)
    )
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Alias '{clean_name}' already exists for this user.",
        )

    alias = Alias(
        user_id=current_user.id,
        name=clean_name,
        target_type=payload.target_type,
        target_id=payload.target_id,
        parameters=payload.parameters,
        is_active=True,
    )
    db.add(alias)
    await db.commit()
    await db.refresh(alias)

    return APIResponse(
        ok=True,
        data={
            "id": str(alias.id),
            "name": alias.name,
            "target_type": alias.target_type,
            "target_id": alias.target_id,
            "is_active": alias.is_active,
            "message": f"Alias '{clean_name}' created successfully.",
        },
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.delete("/{alias_id}", response_model=APIResponse)
async def delete_alias(
    alias_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom alias."""
    try:
        alias_uuid = uuid.UUID(alias_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid alias ID format.")

    res = await db.execute(
        select(Alias).where(Alias.id == alias_uuid, Alias.user_id == current_user.id)
    )
    alias = res.scalar_one_or_none()
    if not alias:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alias not found.")

    await db.delete(alias)
    await db.commit()

    return APIResponse(
        ok=True,
        data={"deleted_id": alias_id, "message": f"Alias '{alias.name}' deleted successfully."},
        trace_id=getattr(request.state, "trace_id", None),
    )
