"""Safety, Progressive Autonomy, and Circuit Breaker REST API router."""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from packages.core.schemas.common import APIResponse
from packages.core.db.models import User, Notification
from packages.core.safety.kill_switch import emergency_kill_switch
from packages.core.safety.anomaly import anomaly_detector
from apps.api.deps import get_db, get_current_user

router = APIRouter()

AUTONOMY_LEVEL_INFO = {
    0: {
        "title": "Level 0: Strict Manual",
        "description": "Zero-trust mode. Explicit human confirmation is required for EVERY single action, including read-only operations.",
        "badge": "Strict Manual",
        "color": "amber",
    },
    1: {
        "title": "Level 1: Assisted / Suggest",
        "description": "Read-only actions execute automatically. All mutations, drafts, writes, and external calls require human confirmation.",
        "badge": "Assisted",
        "color": "blue",
    },
    2: {
        "title": "Level 2: Balanced / Guarded (Recommended)",
        "description": "Read-only and safe internal operations execute autonomously. External sends, deletions, and high-risk actions require confirmation.",
        "badge": "Guarded",
        "color": "indigo",
    },
    3: {
        "title": "Level 3: Auto-Low-Risk",
        "description": "Safe writes and routine external actions execute autonomously. Only destructive and critical-risk actions require confirmation.",
        "badge": "Auto-Low-Risk",
        "color": "cyan",
    },
    4: {
        "title": "Level 4: Full Autonomous",
        "description": "All verified operations execute autonomously within spend guards. The Emergency Kill Switch remains the ultimate fail-safe.",
        "badge": "Full Autonomous",
        "color": "emerald",
    },
}


class UpdateAutonomyPayload(BaseModel):
    autonomy_level: int = Field(ge=0, le=4, description="Autonomy level between 0 and 4")


class KillSwitchPayload(BaseModel):
    active: bool = Field(description="Set True to lock down system, False to resume")
    reason: Optional[str] = Field(default=None, description="Reason for emergency stop or resume")


class ResetCircuitBreakerPayload(BaseModel):
    connector: Optional[str] = Field(default=None, description="Specific connector name, or None for all")


@router.get("/policies/autonomy", response_model=APIResponse)
async def get_autonomy_level(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current user's progressive autonomy level and tier descriptions."""
    user_level = int(current_user.settings.get("autonomy_level", 2))
    return APIResponse(
        ok=True,
        data={
            "current_level": user_level,
            "current_info": AUTONOMY_LEVEL_INFO.get(user_level, AUTONOMY_LEVEL_INFO[2]),
            "tiers": AUTONOMY_LEVEL_INFO,
        },
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/policies/autonomy", response_model=APIResponse)
async def update_autonomy_level(
    payload: UpdateAutonomyPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await db.get(User, current_user.id)
    target_user = user if user is not None else current_user
    settings = dict(target_user.settings or {})
    settings["autonomy_level"] = payload.autonomy_level
    target_user.settings = settings
    flag_modified(target_user, "settings")
    await db.commit()

    return APIResponse(
        ok=True,
        data={
            "updated_level": payload.autonomy_level,
            "info": AUTONOMY_LEVEL_INFO.get(payload.autonomy_level),
            "message": f"Autonomy level updated to Level {payload.autonomy_level}.",
        },
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.get("/safety/kill-switch", response_model=APIResponse)
async def get_kill_switch_status(request: Request):
    """Get the current state of the system-wide Emergency Kill Switch."""
    status_data = await emergency_kill_switch.get_status()
    return APIResponse(
        ok=True,
        data=status_data,
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/safety/kill-switch", response_model=APIResponse)
async def toggle_kill_switch(
    payload: KillSwitchPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate or deactivate the emergency kill switch."""
    if payload.active:
        reason = payload.reason or f"Emergency Stop activated by {current_user.email}"
        result = await emergency_kill_switch.activate(reason=reason, triggered_by=current_user.email)

        # Emit high priority notification
        notif = Notification(
            user_id=current_user.id,
            type="TASK_ALERT",
            title="⚠️ EMERGENCY STOP ACTIVATED",
            message=f"All autonomous tool executions have been halted immediately: {reason}",
            spoken_text="Emergency Stop has been activated. All autonomous actions are now locked down.",
            status="UNREAD",
            metadata_json={"kill_switch": True, "reason": reason},
        )
        db.add(notif)
        await db.commit()
    else:
        result = await emergency_kill_switch.deactivate(actor=current_user.email)
        notif = Notification(
            user_id=current_user.id,
            type="TASK_ALERT",
            title="✅ SYSTEM OPERATIONS RESUMED",
            message="Emergency Stop has been deactivated. Autonomous workflows and tool actions are restored.",
            spoken_text="System operations have been resumed. Autonomous actions are back online.",
            status="UNREAD",
            metadata_json={"kill_switch": False},
        )
        db.add(notif)
        await db.commit()

    return APIResponse(
        ok=True,
        data=result,
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.get("/safety/status", response_model=APIResponse)
async def get_safety_status(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get full safety telemetry: circuit breakers, kill switch, and autonomy level."""
    circuit_data = await anomaly_detector.get_all_status()
    kill_switch_data = await emergency_kill_switch.get_status()
    user_level = int(current_user.settings.get("autonomy_level", 2))

    return APIResponse(
        ok=True,
        data={
            "kill_switch": kill_switch_data,
            "circuit_breakers": circuit_data,
            "autonomy_level": {
                "level": user_level,
                "info": AUTONOMY_LEVEL_INFO.get(user_level),
            },
        },
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/safety/circuit-breaker/reset", response_model=APIResponse)
async def reset_circuit_breaker(
    payload: ResetCircuitBreakerPayload,
    request: Request,
):
    """Manually reset tripped circuit breakers."""
    results = await anomaly_detector.reset(payload.connector)
    return APIResponse(
        ok=True,
        data={"reset_connectors": results, "message": "Circuit breaker(s) reset successfully."},
        trace_id=getattr(request.state, "trace_id", None),
    )
