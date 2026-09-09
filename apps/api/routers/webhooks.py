"""Inbound Webhooks API Router for OmniBrain.

Receives external webhooks from GitHub, Slack, Mobile (MacroDroid/Tasker), and custom services,
publishes to the Redis Streams EventBus, and triggers matching event-driven Workflows.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db, get_current_user
from packages.core.db.models import User, Workflow, Notification
from packages.core.events.bus import EventBus
from packages.core.schemas.common import APIResponse
from packages.core.workflows.engine import WorkflowEngine

router = APIRouter()
logger = logging.getLogger("omnibrain.webhooks")
event_bus = EventBus()
workflow_engine = WorkflowEngine()


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.post("/webhooks/{source}", response_model=APIResponse)
async def receive_webhook(
    source: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(default=None, alias="X-Webhook-Secret"),
):
    """Receive an external webhook event and route to EventBus & Workflows."""
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw": (await request.body()).decode("utf-8", errors="ignore")}

    topic = f"events.webhooks.{source.lower()}"

    # 1. Publish to EventBus
    event = await event_bus.publish_event(
        topic=topic,
        data=payload,
        source=source,
    )

    # 2. Check for event-driven workflows
    triggered_workflows: List[str] = []
    res = await db.execute(
        select(Workflow).where(
            Workflow.trigger_type == "event",
            Workflow.is_active == True,
        )
    )
    workflows = res.scalars().all()

    for wf in workflows:
        wf_source = wf.definition.get("event_source", "").lower()
        if not wf_source or wf_source == source.lower() or wf_source == "all":
            try:
                run = await workflow_engine.run_workflow(db, wf, custom_inputs={"webhook": payload})
                triggered_workflows.append(f"{wf.name} (run: {run.id})")
            except Exception as e:
                logger.error(f"Failed to trigger workflow {wf.name} from webhook: {e}")

    await db.commit()

    return APIResponse(
        ok=True,
        data={
            "received": True,
            "event_id": event.event_id,
            "source": source,
            "topic": topic,
            "timestamp": event.timestamp,
            "triggered_workflows": triggered_workflows,
        },
    )


@router.get("/webhooks/events", response_model=APIResponse)
async def list_recent_events(
    limit: int = Query(default=30, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Fetch live event feed from Redis Streams EventBus."""
    events = await event_bus.list_recent_events(limit=limit)
    return APIResponse(
        ok=True,
        data={
            "events": events,
            "total_count": len(events),
        },
    )


@router.get("/webhooks/info", response_model=APIResponse)
async def get_webhooks_info(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Provide copyable webhook URLs and cURL examples for user devices."""
    base_url = str(request.base_url).rstrip("/")
    return APIResponse(
        ok=True,
        data={
            "endpoints": {
                "mobile": f"{base_url}/v1/mobile/webhook",
                "github": f"{base_url}/v1/webhooks/github",
                "slack": f"{base_url}/v1/webhooks/slack",
                "custom": f"{base_url}/v1/webhooks/custom",
            },
            "examples": {
                "macrodroid_sms": {
                    "method": "POST",
                    "url": f"{base_url}/v1/mobile/webhook",
                    "headers": {"Content-Type": "application/json"},
                    "body": {
                        "event_type": "sms_received",
                        "sender": "+919876543210",
                        "text": "Your OTP is 482910 for Bank Login",
                        "timestamp": "2026-09-08T10:00:00Z"
                    },
                },
                "quick_action_curl": f"curl -X POST {base_url}/v1/mobile/quick-action -H 'Content-Type: application/json' -d '{{\"action\": \"morning_briefing\"}}'",
            },
        },
    )

