"""Task management API router — submit goals, inspect DAG execution progress."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.schemas.common import APIResponse
from packages.core.schemas.task import TaskCreate, TaskRead, TaskStepRead
from packages.core.db.models import Task, TaskStep, User
from apps.api.deps import get_db, get_current_user
from apps.worker.main import execute_task_job

router = APIRouter()


@router.post("", response_model=APIResponse)
async def create_task(
    payload: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new task and initiate step execution."""
    trace_id = getattr(request.state, "trace_id", None)

    task = Task(
        user_id=current_user.id,
        source=payload.source,
        intent={"goal": payload.goal, "raw_input": payload.initial_inputs},
        path=payload.path,
        status="PLANNED",
        trace_id=trace_id,
    )
    db.add(task)
    await db.flush()

    # Create initial DAG step
    initial_step = TaskStep(
        task_id=task.id,
        step_key="initial_action",
        kind="tool",
        capability="fake.write",
        status="PLANNED",
        inputs={"goal": payload.goal, **payload.initial_inputs},
    )
    db.add(initial_step)
    await db.commit()

    # Run execution directly or asynchronously
    job_result = await execute_task_job({"worker_id": "api-worker"}, str(task.id), session=db)
    await db.commit()

    # Reload with steps
    result = await db.execute(
        select(Task).where(Task.id == task.id).options(selectinload(Task.steps))
    )
    reloaded_task = result.scalar_one()

    return APIResponse(
        ok=True,
        data={
            "task_id": str(reloaded_task.id),
            "status": reloaded_task.status,
            "result": reloaded_task.result,
        },
        trace_id=trace_id,
    )


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(
    task_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full task status, DAG steps, and result summary."""
    result = await db.execute(
        select(Task).where(Task.id == task_id).options(selectinload(Task.steps))
    )
    task = result.scalar_one_or_none()

    if not task or task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    task_read = TaskRead(
        id=task.id,
        user_id=task.user_id,
        source=task.source,
        path=task.path,
        status=task.status,
        intent=task.intent,
        result=task.result,
        cost_usd=task.cost_usd,
        trace_id=task.trace_id,
        created_at=task.created_at,
        steps=[
            TaskStepRead(
                id=s.id,
                step_key=s.step_key,
                kind=s.kind,
                capability=s.capability,
                status=s.status,
                inputs=s.inputs,
                outputs=s.outputs,
                error=s.error,
            )
            for s in task.steps
        ],
    )

    return APIResponse(
        ok=True,
        data=task_read,
        trace_id=getattr(request.state, "trace_id", None),
    )
