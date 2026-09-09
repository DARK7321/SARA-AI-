"""Approval management for Human-in-the-Loop (HITL) workflows."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import Approval, Task, TaskStep, TaskEvent


async def create_approval_request(
    session: AsyncSession,
    task_id: UUID,
    step_id: UUID,
    user_id: UUID,
    summary: Dict[str, Any],
    scope: Optional[str] = None,
    expiry_hours: int = 24,
) -> Approval:
    """Create a new approval request and set step/task state to WAITING_APPROVAL."""
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

    approval = Approval(
        task_id=task_id,
        step_id=step_id,
        user_id=user_id,
        summary=summary,
        status="pending",
        scope=scope,
        expires_at=expires_at,
    )
    session.add(approval)

    # Update Task and Step status to WAITING_APPROVAL
    step_result = await session.execute(select(TaskStep).where(TaskStep.id == step_id))
    step = step_result.scalar_one_or_none()
    if step:
        step.status = "WAITING_APPROVAL"

    task_result = await session.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if task:
        task.status = "WAITING_APPROVAL"

    # Emit transition event
    event = TaskEvent(
        task_id=task_id,
        step_id=step_id,
        from_state="PLANNED",
        to_state="WAITING_APPROVAL",
        actor="policy",
        reason=summary.get("why", "Action requires human approval by policy."),
    )
    session.add(event)

    await session.flush()
    return approval


async def resolve_approval(
    session: AsyncSession,
    approval_id: UUID,
    decision: str,  # "approved", "rejected"
    decided_via: str = "web_ui",
) -> Optional[Approval]:
    """Resolve an approval request and update associated step."""
    result = await session.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()

    if not approval or approval.status != "pending":
        return None

    approval.status = decision
    approval.decided_at = datetime.now(timezone.utc)
    approval.decided_via = decided_via

    # If step exists, update its status
    if approval.step_id:
        step_result = await session.execute(
            select(TaskStep).where(TaskStep.id == approval.step_id)
        )
        step = step_result.scalar_one_or_none()
        if step:
            new_status = "AUTHORIZED" if decision == "approved" else "CANCELLED"
            step.status = new_status

            event = TaskEvent(
                task_id=approval.task_id,
                step_id=approval.step_id,
                from_state="WAITING_APPROVAL",
                to_state=new_status,
                actor="user",
                reason=f"Human decision: {decision}",
            )
            session.add(event)

    await session.flush()
    return approval
