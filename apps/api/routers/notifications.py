"""Notifications and Proactive API Router for OmniBrain.

Provides endpoints to list notifications, mark them read, trigger proactive scan cycles,
and manage long-term memories.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db, get_current_user
from apps.worker.proactive import ProactiveEngine
from packages.core.db.models import User, Notification, Memory
from packages.core.memory.store import get_memory_store
from packages.core.schemas.common import APIResponse

router = APIRouter()


# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------

class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    spoken_text: Optional[str] = None
    audio_base64: Optional[str] = None
    status: str
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TriggerProactiveRequest(BaseModel):
    force_briefing: bool = Field(default=True, description="Force generate daily briefing even if already sent today")
    include_audio: bool = Field(default=True, description="Generate Lady voice audio narration")


class MemoryCreateRequest(BaseModel):
    content: str = Field(description="The memory statement or user preference")
    category: str = Field(default="fact", description="Category: preference | fact | episodic | procedural")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = Field(default="user_stated")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryOut(BaseModel):
    id: str
    category: str
    content: str
    confidence: float
    source: str
    similarity: Optional[float] = None
    created_at: str


# -------------------------------------------------------------
# Notifications Endpoints
# -------------------------------------------------------------

@router.get("/notifications", response_model=APIResponse)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notifications for the authenticated user."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.status == "UNREAD")

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    items = [
        NotificationOut(
            id=str(n.id),
            type=n.type,
            title=n.title,
            message=n.message,
            spoken_text=n.spoken_text,
            audio_base64=n.audio_base64,
            status=n.status,
            created_at=n.created_at.isoformat() if n.created_at else "",
            metadata=n.metadata_json or {},
        ).model_dump()
        for n in notifications
    ]

    unread_count_stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.status == "UNREAD",
    )
    unread_res = await db.execute(unread_count_stmt)
    unread_total = len(unread_res.scalars().all())

    return APIResponse(
        ok=True,
        data={"notifications": items, "unread_count": unread_total},
    )


@router.post("/notifications/{notification_id}/read", response_model=APIResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as READ."""
    stmt = (
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .values(status="READ", updated_at=datetime.now(timezone.utc))
    )
    res = await db.execute(stmt)
    await db.commit()

    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Notification not found")

    return APIResponse(ok=True, data={"id": str(notification_id), "status": "READ"})


@router.post("/notifications/read-all", response_model=APIResponse)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all unread notifications as READ."""
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status == "UNREAD",
        )
        .values(status="READ", updated_at=datetime.now(timezone.utc))
    )
    res = await db.execute(stmt)
    await db.commit()
    return APIResponse(ok=True, data={"marked_read": res.rowcount})


@router.post("/proactive/trigger", response_model=APIResponse)
async def trigger_proactive_cycle(
    payload: TriggerProactiveRequest = TriggerProactiveRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Immediately execute an autonomous proactive scan for briefing, meeting reminders, and urgent emails."""
    engine = ProactiveEngine()
    new_notifs = await engine.run_proactive_cycle(
        session=db,
        user_id=current_user.id,
        force_briefing=payload.force_briefing,
        generate_audio=payload.include_audio,
    )
    await db.commit()

    serialized = [
        NotificationOut(
            id=str(n.id),
            type=n.type,
            title=n.title,
            message=n.message,
            spoken_text=n.spoken_text,
            audio_base64=n.audio_base64,
            status=n.status,
            created_at=n.created_at.isoformat() if n.created_at else "",
            metadata=n.metadata_json or {},
        ).model_dump()
        for n in new_notifs
    ]

    return APIResponse(
        ok=True,
        data={
            "generated_count": len(new_notifs),
            "notifications": serialized,
        },
    )


# -------------------------------------------------------------
# Memory Endpoints
# -------------------------------------------------------------

@router.get("/memory", response_model=APIResponse)
async def list_or_search_memories(
    query: Optional[str] = Query(default=None, description="Semantic search query"),
    category: Optional[str] = Query(default=None, description="Category filter"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve long-term memories using semantic similarity or chronological listing."""
    store = get_memory_store()

    if query and query.strip():
        matches = await store.search_memories(
            session=db,
            user_id=current_user.id,
            query=query,
            category=category,
            top_k=limit,
            min_similarity=0.1,
        )
        memories = [
            MemoryOut(
                id=str(m.id),
                category=m.category,
                content=m.content,
                confidence=m.confidence,
                source=m.source,
                similarity=sim,
                created_at=m.created_at.isoformat() if m.created_at else "",
            ).model_dump()
            for m, sim in matches
        ]
    else:
        raw_mems = await store.list_memories(
            session=db,
            user_id=current_user.id,
            category=category,
            limit=limit,
        )
        memories = [
            MemoryOut(
                id=str(m.id),
                category=m.category,
                content=m.content,
                confidence=m.confidence,
                source=m.source,
                created_at=m.created_at.isoformat() if m.created_at else "",
            ).model_dump()
            for m in raw_mems
        ]

    return APIResponse(ok=True, data={"memories": memories})


@router.post("/memory", response_model=APIResponse)
async def create_memory(
    payload: MemoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store a new long-term memory with automatic embedding generation."""
    store = get_memory_store()
    memory = await store.store_memory(
        session=db,
        user_id=current_user.id,
        content=payload.content,
        category=payload.category,
        confidence=payload.confidence,
        source=payload.source,
        metadata_json=payload.metadata,
    )
    await db.commit()

    return APIResponse(
        ok=True,
        data={
            "id": str(memory.id),
            "category": memory.category,
            "content": memory.content,
            "confidence": memory.confidence,
        },
    )
