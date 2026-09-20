"""Background Worker for OmniBrain using arq and Redis.

Consumes task execution jobs, leases task steps, and coordinates with
StepExecutionEngine and VerificationEngine.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.settings import get_settings
from packages.core.db.session import async_session_maker
from packages.core.db.models import Task, TaskStep, TaskEvent, User
from packages.core.execution.engine import StepExecutionEngine
from packages.connectors._sdk.testing import FakeConnector
from packages.connectors._sdk.contract import SideEffectType
from packages.connectors.gmail.client import GmailConnector
from packages.connectors.gdrive.client import GDriveConnector
from packages.connectors.gcal.client import GCalConnector
from packages.connectors.gsheets.client import GSheetsConnector
from packages.connectors.github.client import GitHubConnector
from packages.connectors.slack.client import SlackConnector
from packages.connectors.browser.client import BrowserConnector
from packages.connectors.mcp.client import MCPConnector
from packages.connectors.websearch.client import WebSearchConnector
from packages.connectors.host_agent.client import HostAgentConnector


@asynccontextmanager
async def _get_or_create_session(provided_session: Optional[AsyncSession] = None):
    if provided_session is not None:
        yield provided_session
    else:
        async with async_session_maker() as session:
            yield session


async def execute_task_job(
    ctx: Dict[str, Any],
    task_id_str: str,
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Execute all pending steps for a given task ID."""
    task_id = UUID(task_id_str)
    worker_id = ctx.get("worker_id", "arq-worker-1")

    async with _get_or_create_session(session) as s:
        # 1. Fetch Task
        task_res = await s.execute(select(Task).where(Task.id == task_id))
        task = task_res.scalar_one_or_none()
        if not task:
            return {"status": "error", "message": "Task not found"}

        task.status = "EXECUTING"
        await s.flush()

        # Check Emergency Kill Switch
        from packages.core.safety.kill_switch import emergency_kill_switch
        if await emergency_kill_switch.is_active():
            task.status = "FAILED"
            task.result = {"error": "Emergency Kill Switch is active. Task execution aborted."}
            await s.flush()
            return {"status": "failed", "error": "Emergency Kill Switch active"}

        # Fetch user settings for progressive autonomy level
        user_res = await s.execute(select(User).where(User.id == task.user_id))
        task_user = user_res.scalar_one_or_none()
        autonomy_level = 2
        if task_user and task_user.settings:
            autonomy_level = int(task_user.settings.get("autonomy_level", 2))

        # 2. Fetch steps ordered by dependency
        steps_res = await s.execute(
            select(TaskStep)
            .where(TaskStep.task_id == task_id)
            .order_by(TaskStep.created_at)
        )
        steps = steps_res.scalars().all()

        execution_engine = StepExecutionEngine()
        fake_connector = FakeConnector()

        # Resolve user Google OAuth token if connected
        google_token = None
        try:
            from packages.connectors.google_auth import GoogleAuthManager
            conn_res = await s.execute(
                select(Connection).where(
                    Connection.user_id == task.user_id,
                    Connection.provider == "google",
                    Connection.status == "ONLINE",
                )
            )
            google_conn = conn_res.scalar_one_or_none()
            if google_conn and google_conn.access_token_encrypted:
                auth_mgr = GoogleAuthManager()
                google_token = await auth_mgr.get_valid_access_token(google_conn, s)
        except Exception as ex:
            logger.warning(f"Could not load Google token for task {task_id}: {ex}")

        gmail_connector = GmailConnector(access_token=google_token)
        gdrive_connector = GDriveConnector(access_token=google_token)
        gcal_connector = GCalConnector(access_token=google_token)
        gsheets_connector = GSheetsConnector(access_token=google_token)
        github_connector = GitHubConnector()
        slack_connector = SlackConnector()
        browser_connector = BrowserConnector()
        mcp_connector = MCPConnector()
        websearch_connector = WebSearchConnector()
        host_agent_connector = None

        task_failed = False
        waiting_approval = False
        previous_step_outputs = {}

        for step in steps:
            if step.status in ("SUCCEEDED", "SKIPPED"):
                continue

            # Check Kill Switch mid-execution
            if await emergency_kill_switch.is_active():
                step.status = "FAILED"
                step.result = {"error": "Emergency Kill Switch activated during execution."}
                task.status = "FAILED"
                task.result = {"error": "Emergency Kill Switch activated mid-flight."}
                await s.flush()
                return {"status": "failed", "error": "Emergency Kill Switch active mid-flight"}

            # Acquire step lease
            now = datetime.now(timezone.utc)
            step.locked_by = worker_id
            step.lease_expires_at = now + timedelta(minutes=5)
            await s.flush()

            # Resolve connector
            cap = step.capability or ""
            connector = fake_connector
            if cap.startswith("gmail."):
                connector = gmail_connector
            elif cap.startswith("drive."):
                connector = gdrive_connector
            elif cap.startswith("calendar."):
                connector = gcal_connector
            elif cap.startswith("sheets."):
                connector = gsheets_connector
            elif cap.startswith("github."):
                connector = github_connector
            elif cap.startswith("slack."):
                connector = slack_connector
            elif cap.startswith("browser."):
                connector = browser_connector
            elif cap.startswith("host."):
                if host_agent_connector is None:
                    host_agent_connector = HostAgentConnector()
                connector = host_agent_connector
            elif cap.startswith("mcp."):
                connector = mcp_connector
            elif cap.startswith("web."):
                connector = websearch_connector

            # Dynamic Input Propagation across dependent steps
            step_inputs = dict(step.inputs or {})
            if cap == "gmail.read" and not step_inputs.get("message_id"):
                for prev_out in previous_step_outputs.values():
                    if isinstance(prev_out, dict):
                        msgs = prev_out.get("messages") or prev_out.get("data", {}).get("messages")
                        if msgs and isinstance(msgs, list) and len(msgs) > 0:
                            first_msg = msgs[0]
                            step_inputs["message_id"] = first_msg.get("id") if isinstance(first_msg, dict) else str(first_msg)
                            break

            # Execute step
            side_effect = SideEffectType.WRITE
            if step.kind == "tool" and ("read" in cap or "search" in cap or "list" in cap):
                side_effect = SideEffectType.READ
            elif step.kind == "tool" and ("delete" in cap or "send" in cap):
                side_effect = SideEffectType.DESTRUCTIVE if "delete" in cap else SideEffectType.EXTERNAL_SEND

            result = await execution_engine.execute_step(
                session=s,
                step=step,
                connector=connector,
                action=cap or "fake.action",
                inputs=step_inputs,
                user_id=task.user_id,
                side_effect=side_effect,
                autonomy_level=autonomy_level,
            )

            if result.success and result.data:
                previous_step_outputs[step.step_key] = result.data

            if result.status == "WAITING_APPROVAL":
                waiting_approval = True
                task.status = "WAITING_APPROVAL"
                await s.flush()
                return {"status": "waiting_approval", "step_id": str(step.id)}

            if not result.success:
                task_failed = True
                task.status = "FAILED"
                task.result = {"error": result.error}
                await s.flush()
                return {"status": "failed", "step_id": str(step.id), "error": result.error}

        if not task_failed and not waiting_approval:
            task.status = "COMPLETED"
            task.result = {
                "summary": "All steps executed and verified successfully.",
                "completed_steps": len(steps),
            }
            s.add(
                TaskEvent(
                    task_id=task.id,
                    from_state="EXECUTING",
                    to_state="COMPLETED",
                    actor="system",
                    reason="All DAG steps completed and verified",
                )
            )
            await s.flush()

        return {"status": task.status}


async def startup(ctx: Dict[str, Any]) -> None:
    """Worker startup hook."""
    ctx["worker_id"] = "omnibrain-worker-1"
    print("OmniBrain Background Worker initialized.")


async def shutdown(ctx: Dict[str, Any]) -> None:
    """Worker shutdown hook."""
    print("OmniBrain Background Worker shutting down.")


class WorkerSettings:
    """arq Worker configuration."""
    settings = get_settings()
    functions = [execute_task_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

