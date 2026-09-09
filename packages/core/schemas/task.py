"""Task and Approval Pydantic schemas for API requests and responses."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    goal: str = Field(description="Natural language goal or command")
    path: str = Field(default="SMART", description="FAST | SMART | DEEP")
    source: str = Field(default="chat", description="chat | event | schedule")
    initial_inputs: Dict[str, Any] = Field(default_factory=dict)


class TaskStepRead(BaseModel):
    id: UUID
    step_key: str
    kind: str
    capability: Optional[str] = None
    status: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class TaskRead(BaseModel):
    id: UUID
    user_id: UUID
    source: str
    path: str
    status: str
    intent: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    cost_usd: Decimal
    trace_id: Optional[str] = None
    created_at: datetime
    steps: List[TaskStepRead] = Field(default_factory=list)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(description="'approved' or 'rejected'")


class ApprovalRead(BaseModel):
    id: UUID
    task_id: UUID
    step_id: Optional[UUID] = None
    summary: Dict[str, Any]
    status: str
    expires_at: datetime
    created_at: datetime

