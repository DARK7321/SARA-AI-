"""Step Execution Engine for OmniBrain.

Executes individual task steps under the Universal Tool Contract with
policy enforcement, idempotency deduplication, retry logic, and post-condition verification.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import random
import time
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import (
    ToolRequest,
    ToolResponse,
    ToolContext,
    ToolAuthorization,
    ToolMetadata,
    ErrorClass,
    SideEffectType,
    compute_idempotency_key,
)
from packages.core.policy.engine import PolicyEngine, PolicyEffect
from packages.core.policy.approvals import create_approval_request
from packages.core.execution.idempotency import IdempotencyEngine
from packages.core.execution.verification import VerificationEngine, VerificationStatus
from packages.core.execution.recovery import RecoveryEngine, RecoveryStrategy
from packages.core.db.models import TaskStep, ToolCall, TaskEvent


class StepExecutionResult:
    def __init__(
        self,
        success: bool,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        verification_status: Optional[str] = None,
        error: Optional[str] = None,
        cached: bool = False,
    ):
        self.success = success
        self.status = status
        self.data = data or {}
        self.verification_status = verification_status
        self.error = error
        self.cached = cached


class StepExecutionEngine:
    """Executes a single step within a task DAG."""

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        idempotency_engine: Optional[IdempotencyEngine] = None,
        verification_engine: Optional[VerificationEngine] = None,
        recovery_engine: Optional[RecoveryEngine] = None,
        max_retries: int = 3,
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.idempotency_engine = idempotency_engine or IdempotencyEngine()
        self.verification_engine = verification_engine or VerificationEngine()
        self.recovery_engine = recovery_engine or RecoveryEngine(max_l1_retries=max_retries)
        self.max_retries = max_retries

    async def execute_step(
        self,
        session: AsyncSession,
        step: TaskStep,
        connector: BaseConnector,
        action: str,
        inputs: Dict[str, Any],
        user_id: UUID,
        side_effect: SideEffectType = SideEffectType.WRITE,
        risk_level: str = "LOW",
        autonomy_level: int = 2,
        dry_run: bool = False,
    ) -> StepExecutionResult:
        """Execute task step with full governance, idempotency, and verification."""
        now = datetime.now(timezone.utc)
        step.started_at = now
        step.attempt += 1

        # 0. Emergency Kill Switch Check
        from packages.core.safety.kill_switch import emergency_kill_switch
        from packages.core.safety.anomaly import anomaly_detector
        
        is_killed = await emergency_kill_switch.is_active()
        if is_killed:
            step.status = "FAILED"
            step.finished_at = datetime.now(timezone.utc)
            err_msg = "Execution denied: EMERGENCY KILL SWITCH IS ACTIVE. All autonomous operations are halted."
            step.error = {"reason": err_msg}
            session.add(
                TaskEvent(
                    task_id=step.task_id,
                    step_id=step.id,
                    from_state="PLANNED",
                    to_state="FAILED",
                    actor="policy",
                    reason=err_msg,
                )
            )
            await session.flush()
            return StepExecutionResult(success=False, status="FAILED", error=err_msg)

        # Circuit Breaker Check
        conn_name = connector.connector_id if hasattr(connector, "connector_id") else connector.name.lower()
        if not await anomaly_detector.is_available(conn_name):
            step.status = "FAILED"
            step.finished_at = datetime.now(timezone.utc)
            err_msg = f"Circuit breaker OPEN for connector '{conn_name}'. Calls temporarily blocked due to repeated failures."
            step.error = {"reason": err_msg}
            session.add(
                TaskEvent(
                    task_id=step.task_id,
                    step_id=step.id,
                    from_state="PLANNED",
                    to_state="FAILED",
                    actor="system",
                    reason=err_msg,
                )
            )
            await session.flush()
            return StepExecutionResult(success=False, status="FAILED", error=err_msg)

        # 1. Policy Evaluation (if not already human-authorized)
        if step.status != "AUTHORIZED":
            policy_decision = self.policy_engine.evaluate(
                action=action,
                side_effect=side_effect,
                risk_level=risk_level,
                autonomy_level=autonomy_level,
                kill_switch_active=is_killed,
            )

            if policy_decision.effect == PolicyEffect.DENY:
                step.status = "FAILED"
                step.finished_at = datetime.now(timezone.utc)
                step.error = {"reason": policy_decision.reason, "rule_id": policy_decision.rule_id}
                session.add(
                    TaskEvent(
                        task_id=step.task_id,
                        step_id=step.id,
                        from_state="PLANNED",
                        to_state="FAILED",
                        actor="policy",
                        reason=policy_decision.reason,
                    )
                )
                await session.flush()
                return StepExecutionResult(
                    success=False,
                    status="FAILED",
                    error=policy_decision.reason,
                )

            if policy_decision.effect == PolicyEffect.CONFIRM:
                summary = {
                    "what": f"Execute action '{action}' on {connector.name}",
                    "why": f"Action is {side_effect.value} with risk {risk_level}",
                    "target": inputs,
                    "risk": risk_level,
                    "next": "Resume execution after confirmation",
                }
                await create_approval_request(
                    session=session,
                    task_id=step.task_id,
                    step_id=step.id,
                    user_id=user_id,
                    summary=summary,
                )
                return StepExecutionResult(
                    success=True,
                    status="WAITING_APPROVAL",
                    data={"approval_required": True, "summary": summary},
                )

        # Transition to RUNNING
        step.status = "RUNNING"
        session.add(
            TaskEvent(
                task_id=step.task_id,
                step_id=step.id,
                from_state="PLANNED",
                to_state="RUNNING",
                actor="system",
                reason="Policy approved, commencing execution",
            )
        )
        await session.flush()

        # 2. Idempotency Check
        idempotency_key = compute_idempotency_key(
            task_id=str(step.task_id),
            step_id=str(step.id),
            canonical_input=inputs,
        )

        should_execute, cached_data = await self.idempotency_engine.acquire_or_get_cached(
            session=session,
            idempotency_key=idempotency_key,
            tool=connector.connector_id,
            action=action,
        )

        if not should_execute and cached_data:
            step.status = "SUCCEEDED"
            step.outputs = cached_data
            step.finished_at = datetime.now(timezone.utc)
            await session.flush()
            return StepExecutionResult(
                success=True,
                status="SUCCEEDED",
                data=cached_data,
                verification_status="VERIFIED",
                cached=True,
            )

        # 3. Tool Execution with Retry Loop for Transient/Rate-limit errors
        request = ToolRequest(
            request_id=f"req_{step.id.hex[:12]}",
            tool=connector.connector_id,
            action=action,
            input=inputs,
            context=ToolContext(
                task_id=str(step.task_id),
                step_id=str(step.id),
                agent=step.agent or "orchestrator",
            ),
            idempotency_key=idempotency_key,
            dry_run=dry_run,
        )

        # Commit session so PostgreSQL row locks are released before waiting on connector execution
        await session.commit()

        attempt = 0
        response: Optional[ToolResponse] = None

        while attempt < self.max_retries:
            attempt += 1
            response = await connector.execute(request)

            if response.success:
                break

            if response.error and response.error.retryable:
                backoff_s = response.error.retry_after_s or (2 ** attempt + random.uniform(0, 0.5))
                await asyncio.sleep(min(backoff_s, 3.0))  # Cap backoff to 3s for fast tests
            if response.error:
                recovery = self.recovery_engine.evaluate_failure(
                    response.error,
                    current_attempt=attempt,
                    connector_id=connector.connector_id,
                )
                if recovery.strategy == RecoveryStrategy.RETRY_BACKOFF:
                    backoff_s = min(recovery.backoff_ms / 1000.0, 3.0)
                    await asyncio.sleep(backoff_s)
                    continue
                else:
                    break
            else:
                # Non-retryable failure
                break

        # Record Tool Call Audit
        tool_call_record = ToolCall(
            task_step_id=step.id,
            tool_id=step.tool_id,
            action=action,
            request=inputs,
            response=response.data if response else None,
            idempotency_key=idempotency_key,
            latency_ms=response.metadata.latency_ms if response else 0,
            cost_usd=Decimal(str(response.metadata.cost)) if response else Decimal("0.000000"),
            error_class=response.error.error_class.value if (response and response.error) else None,
            verification_status="PENDING",
        )
        session.add(tool_call_record)

        if not response or not response.success:
            err_msg = response.error.message if (response and response.error) else "Tool execution failed"
            await anomaly_detector.record_execution(conn_name, success=False, error=err_msg)
            step.status = "FAILED"
            step.finished_at = datetime.now(timezone.utc)
            step.error = {"message": err_msg}
            await self.idempotency_engine.fail(session, idempotency_key, is_retryable=False)
            session.add(
                TaskEvent(
                    task_id=step.task_id,
                    step_id=step.id,
                    from_state="RUNNING",
                    to_state="FAILED",
                    actor="system",
                    reason=err_msg,
                )
            )
            await session.flush()
            return StepExecutionResult(success=False, status="FAILED", error=err_msg)

        # 4. Post-Condition Verification
        verif_status = await self.verification_engine.verify_action(
            connector=connector,
            action=action,
            verification_hints=response.verification_hints,
        )
        tool_call_record.verification_status = verif_status.value

        if verif_status == VerificationStatus.VERIFICATION_FAILED:
            step.status = "FAILED"
            step.finished_at = datetime.now(timezone.utc)
            step.error = {"message": "Post-condition verification failed"}
            await self.idempotency_engine.fail(session, idempotency_key, is_retryable=False)
            session.add(
                TaskEvent(
                    task_id=step.task_id,
                    step_id=step.id,
                    from_state="RUNNING",
                    to_state="FAILED",
                    actor="verifier",
                    reason="Object not changed as expected",
                )
            )
            await session.flush()
            return StepExecutionResult(
                success=False,
                status="FAILED",
                verification_status=verif_status.value,
                error="Verification failed",
            )

        # 5. Success Completion
        await anomaly_detector.record_execution(conn_name, success=True)
        await self.idempotency_engine.complete(session, idempotency_key, response.data)
        step.status = "SUCCEEDED"
        step.outputs = response.data
        step.error = None
        step.finished_at = datetime.now(timezone.utc)

        session.add(
            TaskEvent(
                task_id=step.task_id,
                step_id=step.id,
                from_state="RUNNING",
                to_state="SUCCEEDED",
                actor="system",
                reason="Execution and verification succeeded",
            )
        )
        await session.flush()

        return StepExecutionResult(
            success=True,
            status="SUCCEEDED",
            data=response.data,
            verification_status=verif_status.value,
            cached=False,
        )

