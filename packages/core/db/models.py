import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric, Index, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default='owner', nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default='UTC', nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="user", cascade="all, delete-orphan")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    connections: Mapped[List["Connection"]] = relationship("Connection", back_populates="user", cascade="all, delete-orphan")
    memories: Mapped[List["Memory"]] = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    workflows: Mapped[List["Workflow"]] = relationship("Workflow", back_populates="user", cascade="all, delete-orphan")
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="user", cascade="all, delete-orphan")
    aliases: Mapped[List["Alias"]] = relationship("Alias", back_populates="user", cascade="all, delete-orphan")

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    source: Mapped[str] = mapped_column(String, index=True, nullable=False) # chat|event|schedule
    intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False) # FAST|SMART|DEEP
    status: Mapped[str] = mapped_column(String, index=True, default="RECEIVED", nullable=False) 
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    estimate: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal('0.000000'), nullable=False)
    trace_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="tasks")
    steps: Mapped[List["TaskStep"]] = relationship("TaskStep", back_populates="task", cascade="all, delete-orphan")
    events: Mapped[List["TaskEvent"]] = relationship("TaskEvent", back_populates="task", cascade="all, delete-orphan")
    runs: Mapped[List["TaskRun"]] = relationship("TaskRun", back_populates="task", cascade="all, delete-orphan")
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="task", cascade="all, delete-orphan")

class TaskStep(Base, TimestampMixin):
    __tablename__ = "task_steps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True, nullable=False)
    step_key: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False) # tool|llm|code|approval|wait
    agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    capability: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tool_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    depends_on: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    outputs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default="PENDING", nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    locked_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="steps")
    events: Mapped[List["TaskEvent"]] = relationship("TaskEvent", back_populates="step")
    tool_calls: Mapped[List["ToolCall"]] = relationship("ToolCall", back_populates="task_step")
    approvals: Mapped[List["Approval"]] = relationship("Approval", back_populates="step")
    policy_decisions: Mapped[List["PolicyDecision"]] = relationship("PolicyDecision", back_populates="task_step")
    prompt_runs: Mapped[List["PromptRun"]] = relationship("PromptRun", back_populates="task_step")

class TaskEvent(Base, TimestampMixin):
    __tablename__ = "task_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True, nullable=False)
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("task_steps.id"), index=True, nullable=True)
    from_state: Mapped[str] = mapped_column(String, nullable=False)
    to_state: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False) # system|user|policy
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="events")
    step: Mapped[Optional["TaskStep"]] = relationship("TaskStep", back_populates="events")

class TaskRun(Base, TimestampMixin):
    __tablename__ = "task_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True, nullable=False)
    run_no: Mapped[int] = mapped_column(Integer, nullable=False)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="runs")

class ToolCall(Base, TimestampMixin):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_steps.id"), index=True, nullable=False)
    tool_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal('0.000000'), nullable=False)
    error_class: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    task_step: Mapped["TaskStep"] = relationship("TaskStep", back_populates="tool_calls")

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    tool: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False) # IN_PROGRESS|COMPLETED|FAILED
    response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    fingerprint: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), index=True, nullable=False)
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("task_steps.id"), index=True, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, default="pending", nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    decided_via: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="approvals")
    step: Mapped[Optional["TaskStep"]] = relationship("TaskStep", back_populates="approvals")
    user: Mapped["User"] = relationship("User", back_populates="approvals")

class PolicyDecision(Base, TimestampMixin):
    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_steps.id"), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String, nullable=False)
    effect: Mapped[str] = mapped_column(String, nullable=False) # ALLOW|CONFIRM|DENY
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task_step: Mapped["TaskStep"] = relationship("TaskStep", back_populates="policy_decisions")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    target: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prev_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hash: Mapped[str] = mapped_column(String, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)

class Prompt(Base, TimestampMixin):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String, index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    model_tier: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    schema_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint('key', 'version', name='uix_prompt_key_version'),
    )

class PromptRun(Base, TimestampMixin):
    __tablename__ = "prompt_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_key: Mapped[str] = mapped_column(String, index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=Decimal('0.000000'), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    task_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("task_steps.id"), index=True, nullable=True)
    valid_output: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    task_step: Mapped[Optional["TaskStep"]] = relationship("TaskStep", back_populates="prompt_runs")

class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String, nullable=False) # daily|monthly|task
    limit_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    spent_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal('0.0000'), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="budgets")

class FeatureFlag(Base, TimestampMixin):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rollout: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class Connection(Base, TimestampMixin):
    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String, index=True, nullable=False)  # google, slack, etc.
    account_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scopes: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="ONLINE", nullable=False)  # ONLINE, EXPIRED, REVOKED, AUTH_FAILURE
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="connections")


class Memory(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String, index=True, nullable=False)  # preference | fact | episodic | procedural
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(768), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String, default="user_stated", nullable=False)  # user_stated | inferred | system
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="memories")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String, index=True, nullable=False)  # BRIEFING | REMINDER | INBOX_ALERT | TASK_ALERT
    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    spoken_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_base64: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default="UNREAD", nullable=False)  # UNREAD | READ | DISMISSED
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String, index=True, default="manual", nullable=False)  # manual | cron | event
    cron_expression: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # steps, inputs, dependencies

    user: Mapped["User"] = relationship("User", back_populates="workflows")
    runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id"), index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String, index=True, default="RUNNING", nullable=False)  # RUNNING | COMPLETED | FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")
    user: Mapped["User"] = relationship("User", back_populates="workflow_runs")


class Alias(Base, TimestampMixin):
    __tablename__ = "aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)  # Trigger command / keyword
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # "workflow" | "quick_action" | "direct_task"
    target_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Workflow ID or action name
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="aliases")



