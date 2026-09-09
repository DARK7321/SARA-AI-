"""Mobile Automation Companion API Router for OmniBrain.

Dedicated lightweight endpoints for smartphone integrations via MacroDroid, Tasker,
Apple Shortcuts, and home-screen widgets.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db, get_current_user
from apps.worker.proactive import ProactiveEngine
from packages.core.db.models import User, Notification, Approval, Workflow
from packages.core.events.bus import EventBus
from packages.core.schemas.common import APIResponse
from packages.core.workflows.engine import WorkflowEngine

router = APIRouter()
logger = logging.getLogger("omnibrain.mobile")
event_bus = EventBus()
proactive_engine = ProactiveEngine()
workflow_engine = WorkflowEngine()


# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------

class MobileWebhookPayload(BaseModel):
    event_type: str = Field(description="Type of mobile event: sms_received | battery_alert | location_beacon | quick_tap")
    sender: Optional[str] = Field(default=None, description="SMS sender number or app package")
    text: Optional[str] = Field(default=None, description="Message text or notification body")
    battery_level: Optional[int] = Field(default=None, description="Device battery percentage 0-100")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional device telemetry")


class MobileQuickActionRequest(BaseModel):
    action: str = Field(description="Action key: morning_briefing | trigger_workflow | voice_query")
    workflow_id: Optional[str] = Field(default=None, description="Workflow UUID if triggering workflow")
    prompt: Optional[str] = Field(default=None, description="Prompt query if voice_query")


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.post("/mobile/webhook", response_model=APIResponse)
async def receive_mobile_webhook(
    payload: MobileWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """Ingest phone events from MacroDroid, Tasker, or Apple Shortcuts."""
    # 1. Publish to EventBus
    event = await event_bus.publish_event(
        topic="events.mobile.webhook",
        data=payload.model_dump(),
        source="smartphone_companion",
    )

    # 2. Identify owner user for notification creation
    user_res = await db.execute(select(User).limit(1))
    owner = user_res.scalar_one_or_none()

    created_notification = False
    if owner:
        # If SMS received with OTP or urgent verification keywords
        if payload.event_type == "sms_received" and payload.text:
            text_lower = payload.text.lower()
            is_urgent = any(kw in text_lower for kw in ["otp", "code", "bank", "urgent", "security", "alert"])

            notif = Notification(
                user_id=owner.id,
                type="INBOX_ALERT",
                title=f"📱 Phone SMS: {payload.sender or 'Unknown'}",
                message=payload.text,
                spoken_text=f"Aapke phone par {payload.sender or 'kisi'} se SMS aaya hai." if is_urgent else None,
                status="UNREAD",
                metadata_json={"source": "mobile_companion", "urgent": is_urgent},
            )
            db.add(notif)
            created_notification = True

        elif payload.event_type == "battery_alert" and payload.battery_level is not None and payload.battery_level <= 15:
            notif = Notification(
                user_id=owner.id,
                type="TASK_ALERT",
                title="⚠️ Phone Battery Low",
                message=f"Phone battery level is at {payload.battery_level}%. Please connect to charger.",
                spoken_text=f"Dhyan dein sir, aapke phone ki battery {payload.battery_level} pratishat bachi hai.",
                status="UNREAD",
                metadata_json={"source": "mobile_battery", "level": payload.battery_level},
            )
            db.add(notif)
            created_notification = True

        await db.commit()

    return APIResponse(
        ok=True,
        data={
            "received": True,
            "event_id": event.event_id,
            "event_type": payload.event_type,
            "notification_created": created_notification,
        },
    )


@router.post("/mobile/quick-action", response_model=APIResponse)
async def mobile_quick_action(
    payload: MobileQuickActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute fast action triggered from phone lock-screen widget or shortcut."""
    user_res = await db.execute(select(User).limit(1))
    owner = user_res.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner user not found")

    action_result: Dict[str, Any] = {"action": payload.action}

    if payload.action == "morning_briefing":
        notifs = await proactive_engine.run_proactive_cycle(
            session=db,
            user_id=owner.id,
            force_briefing=True,
            generate_audio=True,
        )
        await db.commit()
        action_result["briefing_generated"] = len(notifs) > 0
        if notifs:
            action_result["title"] = notifs[0].title
            action_result["spoken_text"] = notifs[0].spoken_text

    elif payload.action == "trigger_workflow" and payload.workflow_id:
        try:
            wf_uuid = UUID(payload.workflow_id)
            wf_res = await db.execute(select(Workflow).where(Workflow.id == wf_uuid))
            wf = wf_res.scalar_one_or_none()
            if wf:
                run = await workflow_engine.run_workflow(db, wf)
                await db.commit()
                action_result["workflow_name"] = wf.name
                action_result["run_status"] = run.status
            else:
                action_result["error"] = "Workflow not found"
        except Exception as e:
            action_result["error"] = str(e)

    else:
        action_result["message"] = f"Action '{payload.action}' accepted and processed."

    return APIResponse(ok=True, data=action_result)


@router.get("/mobile/summary", response_model=APIResponse)
async def get_mobile_summary(
    db: AsyncSession = Depends(get_db),
):
    """Ultra-lightweight JSON payload for phone widgets and smart watch complications."""
    user_res = await db.execute(select(User).limit(1))
    owner = user_res.scalar_one_or_none()
    if not owner:
        return APIResponse(ok=False, data={"error": "User not found"})

    # Unread notifications
    unread_res = await db.execute(
        select(Notification)
        .where(Notification.user_id == owner.id, Notification.status == "UNREAD")
        .order_by(Notification.created_at.desc())
        .limit(5)
    )
    unread_notifs = unread_res.scalars().all()

    # Pending approvals
    appr_res = await db.execute(
        select(Approval).where(Approval.user_id == owner.id, Approval.status == "PENDING")
    )
    pending_approvals = len(appr_res.scalars().all())

    latest_headline = unread_notifs[0].title if unread_notifs else "All systems operating optimally"

    return APIResponse(
        ok=True,
        data={
            "system_status": "ONLINE",
            "unread_notifications": len(unread_notifs),
            "pending_approvals": pending_approvals,
            "latest_headline": latest_headline,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

