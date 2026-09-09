"""Workflows and Automations API Router for OmniBrain.

Provides REST endpoints to list, create, execute, inspect, and delete multi-step workflows.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.deps import get_db, get_current_user
from packages.core.db.models import User, Workflow, WorkflowRun
from packages.core.schemas.common import APIResponse
from packages.core.workflows.engine import WorkflowEngine, BUILTIN_TEMPLATES

router = APIRouter()
engine = WorkflowEngine()


# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------

class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    trigger_type: str = Field(default="manual", description="Trigger type: manual | cron | event")
    cron_expression: Optional[str] = Field(default=None, description="Cron expression if trigger_type is cron")
    definition: Dict[str, Any] = Field(description="Workflow definition containing steps list")


class WorkflowRunRequest(BaseModel):
    custom_inputs: Optional[Dict[str, Any]] = Field(default=None, description="Optional overrides for step inputs")


class WorkflowOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    trigger_type: str
    cron_expression: Optional[str] = None
    is_active: bool
    definition: Dict[str, Any]
    created_at: str
    updated_at: Optional[str] = None


class WorkflowRunOut(BaseModel):
    id: str
    workflow_id: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.get("/workflows", response_model=APIResponse)
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workflows for user. Auto-seeds default templates if none exist."""
    res = await db.execute(
        select(Workflow)
        .where(Workflow.user_id == current_user.id)
        .order_by(Workflow.created_at.asc())
    )
    workflows = res.scalars().all()

    if not workflows:
        workflows = await engine.seed_default_workflows(db, current_user.id)
        await db.commit()

    items = [
        WorkflowOut(
            id=str(w.id),
            name=w.name,
            description=w.description,
            trigger_type=w.trigger_type,
            cron_expression=w.cron_expression,
            is_active=w.is_active,
            definition=w.definition,
            created_at=w.created_at.isoformat() if w.created_at else "",
            updated_at=w.updated_at.isoformat() if w.updated_at else None,
        ).model_dump()
        for w in workflows
    ]

    return APIResponse(
        ok=True,
        data={
            "workflows": items,
            "templates": BUILTIN_TEMPLATES,
        },
    )


@router.post("/workflows", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom workflow."""
    if "steps" not in payload.definition or not isinstance(payload.definition["steps"], list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow definition must contain a 'steps' list.",
        )

    workflow = Workflow(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        cron_expression=payload.cron_expression,
        is_active=True,
        definition=payload.definition,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)

    return APIResponse(
        ok=True,
        data=WorkflowOut(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            trigger_type=workflow.trigger_type,
            cron_expression=workflow.cron_expression,
            is_active=workflow.is_active,
            definition=workflow.definition,
            created_at=workflow.created_at.isoformat() if workflow.created_at else "",
            updated_at=workflow.updated_at.isoformat() if workflow.updated_at else None,
        ).model_dump(),
    )


@router.get("/workflows/{workflow_id}", response_model=APIResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single workflow by ID."""
    res = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    return APIResponse(
        ok=True,
        data=WorkflowOut(
            id=str(workflow.id),
            name=workflow.name,
            description=workflow.description,
            trigger_type=workflow.trigger_type,
            cron_expression=workflow.cron_expression,
            is_active=workflow.is_active,
            definition=workflow.definition,
            created_at=workflow.created_at.isoformat() if workflow.created_at else "",
            updated_at=workflow.updated_at.isoformat() if workflow.updated_at else None,
        ).model_dump(),
    )


@router.post("/workflows/{workflow_id}/run", response_model=APIResponse)
async def run_workflow(
    workflow_id: UUID,
    payload: Optional[WorkflowRunRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a workflow immediately."""
    res = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    custom_inputs = payload.custom_inputs if payload else None
    run = await engine.run_workflow(db, workflow, custom_inputs=custom_inputs)
    await db.commit()
    await db.refresh(run)

    return APIResponse(
        ok=True,
        data=WorkflowRunOut(
            id=str(run.id),
            workflow_id=str(run.workflow_id),
            status=run.status,
            started_at=run.started_at.isoformat() if run.started_at else "",
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
            result=run.result,
            error=run.error,
        ).model_dump(),
    )


@router.get("/workflows/{workflow_id}/runs", response_model=APIResponse)
async def list_workflow_runs(
    workflow_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List runs for a specific workflow."""
    res = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id, WorkflowRun.user_id == current_user.id)
        .order_by(WorkflowRun.started_at.desc())
        .limit(limit)
    )
    runs = res.scalars().all()

    items = [
        WorkflowRunOut(
            id=str(r.id),
            workflow_id=str(r.workflow_id),
            status=r.status,
            started_at=r.started_at.isoformat() if r.started_at else "",
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
            result=r.result,
            error=r.error,
        ).model_dump()
        for r in runs
    ]

    return APIResponse(ok=True, data={"runs": items})


@router.delete("/workflows/{workflow_id}", response_model=APIResponse)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workflow."""
    res = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.user_id == current_user.id)
    )
    workflow = res.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    await db.delete(workflow)
    await db.commit()

    return APIResponse(ok=True, data={"deleted_id": str(workflow_id)})

