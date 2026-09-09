"""Multi-Agent Frameworks API Router for OmniBrain.

Enables listing, configuring, and executing multi-agent squads across
CrewAI, LangGraph, and AutoGen with deterministic policy guards.
"""
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from apps.api.deps import get_current_user
from packages.core.db.models import User
from packages.core.schemas.common import APIResponse
from packages.core.agents.frameworks import (
    get_framework_adapter,
    list_all_frameworks,
    FrameworkExecutionResult,
)
from packages.core.safety.kill_switch import get_kill_switch

router = APIRouter()

# In-memory store for recent framework execution runs
_RUNS_CACHE: Dict[str, Dict[str, Any]] = {}


class FrameworkRunRequest(BaseModel):
    task: str = Field(min_length=1, description="Goal or instruction for the agent team")
    template: Optional[str] = Field(default=None, description="Pre-configured squad/graph/team name")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional parameters e.g. max_turns")


class FrameworkRunResponse(BaseModel):
    run_id: str
    framework: str
    template: str
    status: str
    task: str
    agent_dialogue: List[Dict[str, Any]]
    final_output: str
    execution_time_ms: int
    metadata: Dict[str, Any]


@router.get("", response_model=APIResponse)
async def list_frameworks(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """List all integrated multi-agent frameworks, install status, and templates."""
    trace_id = getattr(request.state, "trace_id", None)
    data = list_all_frameworks()
    return APIResponse(ok=True, data={"frameworks": data}, trace_id=trace_id)


@router.post("/{framework}/run", response_model=APIResponse)
async def run_framework(
    framework: str,
    payload: FrameworkRunRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Execute a task on a multi-agent framework (crewai, langgraph, autogen)."""
    trace_id = getattr(request.state, "trace_id", None)

    # 1. Emergency Kill Switch Check
    kill_switch = get_kill_switch()
    if await kill_switch.is_active():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Autonomous agent execution is blocked: Emergency Kill Switch is ACTIVE.",
        )

    # 2. Get Framework Adapter
    try:
        adapter = get_framework_adapter(framework)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 3. Execute Multi-Agent Squad
    try:
        res: FrameworkExecutionResult = await adapter.execute(
            task=payload.task,
            crew_or_graph_name=payload.template,
            config=payload.config,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent team execution encountered an error: {str(e)}",
        )

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    run_record = {
        "run_id": run_id,
        "framework": res.framework,
        "template": res.crew_or_graph_name,
        "status": res.status,
        "task": res.task,
        "agent_dialogue": [msg.model_dump() for msg in res.agent_dialogue],
        "final_output": res.final_output,
        "execution_time_ms": res.execution_time_ms,
        "metadata": res.metadata,
        "user_id": str(current_user.id),
    }

    _RUNS_CACHE[run_id] = run_record

    return APIResponse(ok=True, data=run_record, trace_id=trace_id)


@router.get("/runs/{run_id}", response_model=APIResponse)
async def get_framework_run(
    run_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Retrieve details and agent dialogue of a previous multi-agent execution."""
    trace_id = getattr(request.state, "trace_id", None)
    if run_id not in _RUNS_CACHE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found.")

    return APIResponse(ok=True, data=_RUNS_CACHE[run_id], trace_id=trace_id)

