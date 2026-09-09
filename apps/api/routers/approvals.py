"""Approval API router for Human-in-the-loop (HITL) authorization."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.schemas.common import APIResponse
from packages.core.schemas.task import ApprovalRead, ApprovalDecisionRequest
from packages.core.db.models import Approval, User
from packages.core.policy.approvals import resolve_approval
from apps.api.deps import get_db, get_current_user
from apps.worker.main import execute_task_job

router = APIRouter()


@router.get("/pending", response_model=APIResponse)
async def get_pending_approvals(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all pending approvals requiring human review."""
    result = await db.execute(
        select(Approval).where(
            Approval.user_id == current_user.id,
            Approval.status == "pending",
        ).order_by(Approval.created_at.desc())
    )
    approvals = result.scalars().all()

    data = [
        ApprovalRead(
            id=a.id,
            task_id=a.task_id,
            step_id=a.step_id,
            summary=a.summary,
            status=a.status,
            expires_at=a.expires_at,
            created_at=a.created_at,
        )
        for a in approvals
    ]

    return APIResponse(
        ok=True,
        data=data,
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/{approval_id}/decision", response_model=APIResponse)
async def decide_approval(
    approval_id: UUID,
    payload: ApprovalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve or reject a pending action."""
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'approved' or 'rejected'",
        )

    # Check ownership
    appr_res = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = appr_res.scalar_one_or_none()
    if not approval or approval.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    resolved = await resolve_approval(db, approval_id, payload.decision, decided_via="web_api")
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval is not in pending status",
        )

    await db.commit()

    # If approved, resume the task execution!
    if payload.decision == "approved":
        await execute_task_job({"worker_id": "approval-resume"}, str(approval.task_id), session=db)
        await db.commit()

    return APIResponse(
        ok=True,
        data={"approval_id": str(approval_id), "status": payload.decision},
        trace_id=getattr(request.state, "trace_id", None),
    )
