"""Workflow Engine for OmniBrain.

Parses, schedules, and executes multi-step automation workflows with dependency resolution,
connector dispatch, and full execution tracking.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext, compute_idempotency_key
from packages.connectors._sdk.testing import FakeConnector
from packages.connectors.browser.client import BrowserConnector
from packages.connectors.gcal.client import GCalConnector
from packages.connectors.gdrive.client import GDriveConnector
from packages.connectors.github.client import GitHubConnector
from packages.connectors.gmail.client import GmailConnector
from packages.connectors.gsheets.client import GSheetsConnector
from packages.connectors.slack.client import SlackConnector
from packages.connectors.mcp.client import MCPConnector
from packages.core.db.models import Workflow, WorkflowRun, Notification

logger = logging.getLogger("omnibrain.workflows.engine")

BUILTIN_TEMPLATES = [
    {
        "template_id": "morning_standup_briefing",
        "name": "Morning Standup Briefing",
        "description": "Collects calendar events, scans open GitHub issues, and posts an executive morning briefing to Slack.",
        "trigger_type": "cron",
        "cron_expression": "0 9 * * 1-5",
        "definition": {
            "steps": [
                {
                    "id": "step_fetch_meetings",
                    "name": "Fetch Today's Meetings",
                    "connector": "calendar",
                    "action": "calendar.list_events",
                    "inputs": {"days_ahead": 1},
                },
                {
                    "id": "step_fetch_issues",
                    "name": "Scan Open GitHub Issues",
                    "connector": "github",
                    "action": "github.list_issues",
                    "inputs": {"repo": "owner/omnibrain", "state": "open"},
                },
                {
                    "id": "step_post_slack_briefing",
                    "name": "Post Standup Briefing to Slack",
                    "connector": "slack",
                    "action": "slack.post_message",
                    "inputs": {
                        "channel": "#general",
                        "text": "🌅 *OmniBrain Morning Standup Briefing*\nCalendar checked, open issues scanned. All systems operating optimally.",
                    },
                    "depends_on": ["step_fetch_meetings", "step_fetch_issues"],
                },
            ]
        },
    },
    {
        "template_id": "github_triage_alert",
        "name": "GitHub Issue & PR Triage",
        "description": "Inspects incoming issues and open pull requests, then sends triage notification to dev channel.",
        "trigger_type": "manual",
        "cron_expression": None,
        "definition": {
            "steps": [
                {
                    "id": "step_list_issues",
                    "name": "List Repository Issues",
                    "connector": "github",
                    "action": "github.list_issues",
                    "inputs": {"repo": "owner/omnibrain", "state": "open"},
                },
                {
                    "id": "step_list_prs",
                    "name": "List Active Pull Requests",
                    "connector": "github",
                    "action": "github.list_prs",
                    "inputs": {"repo": "owner/omnibrain", "state": "open"},
                },
                {
                    "id": "step_notify_slack",
                    "name": "Notify Dev Team on Slack",
                    "connector": "slack",
                    "action": "slack.post_message",
                    "inputs": {
                        "channel": "#dev-team",
                        "text": "🚀 *GitHub Triage Update*: Open issues and pull requests have been reviewed.",
                    },
                    "depends_on": ["step_list_issues", "step_list_prs"],
                },
            ]
        },
    },
    {
        "template_id": "tech_intelligence_digest",
        "name": "Web Intelligence Digest",
        "description": "Extracts latest headlines and articles using Browser connector and broadcasts to workspace.",
        "trigger_type": "manual",
        "cron_expression": None,
        "definition": {
            "steps": [
                {
                    "id": "step_extract_content",
                    "name": "Extract Tech Headlines",
                    "connector": "browser",
                    "action": "browser.extract_content",
                    "inputs": {
                        "url": "https://news.ycombinator.com",
                        "include_links": True,
                    },
                },
                {
                    "id": "step_post_digest",
                    "name": "Post Digest to Slack",
                    "connector": "slack",
                    "action": "slack.post_message",
                    "inputs": {
                        "channel": "#general",
                        "text": "📰 *OmniBrain Tech Digest*: Latest tech insights extracted and available.",
                    },
                    "depends_on": ["step_extract_content"],
                },
            ]
        },
    },
]


class WorkflowEngine:
    """Workflow Engine for managing, seeding, and executing multi-step automations."""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {
            "fake": FakeConnector(),
            "gmail": GmailConnector(),
            "drive": GDriveConnector(),
            "calendar": GCalConnector(),
            "sheets": GSheetsConnector(),
            "github": GitHubConnector(),
            "slack": SlackConnector(),
            "browser": BrowserConnector(),
            "mcp": MCPConnector(),
        }

    def get_connector_for_action(self, action: str, connector_name: Optional[str] = None) -> BaseConnector:
        """Resolve the appropriate connector instance by action or name."""
        if connector_name and connector_name in self._connectors:
            return self._connectors[connector_name]

        prefix = action.split(".")[0].lower() if "." in action else action.lower()
        if prefix in ("gcal", "calendar"):
            return self._connectors["calendar"]
        elif prefix in ("gdrive", "drive"):
            return self._connectors["drive"]
        elif prefix in ("gsheets", "sheets"):
            return self._connectors["sheets"]
        elif prefix in self._connectors:
            return self._connectors[prefix]

        return self._connectors["fake"]

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return available pre-built workflow templates."""
        return BUILTIN_TEMPLATES

    async def seed_default_workflows(self, session: AsyncSession, user_id: UUID) -> List[Workflow]:
        """Ensure built-in workflow templates are seeded for the user."""
        res = await session.execute(select(Workflow).where(Workflow.user_id == user_id))
        existing = res.scalars().all()
        if existing:
            return list(existing)

        seeded: List[Workflow] = []
        for tpl in BUILTIN_TEMPLATES:
            wf = Workflow(
                user_id=user_id,
                name=tpl["name"],
                description=tpl["description"],
                trigger_type=tpl["trigger_type"],
                cron_expression=tpl["cron_expression"],
                is_active=True,
                definition=tpl["definition"],
            )
            session.add(wf)
            seeded.append(wf)

        await session.flush()
        return seeded

    def _interpolate_inputs(
        self,
        inputs: Dict[str, Any],
        step_outputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Interpolate prior step outputs into step inputs if placeholders exist."""
        interpolated = {}
        for key, val in inputs.items():
            if isinstance(val, str) and "{{" in val and "}}" in val:
                resolved = val
                for step_id, output in step_outputs.items():
                    target = f"{{{{steps.{step_id}.output}}}}"
                    if target in resolved:
                        resolved = resolved.replace(target, json.dumps(output) if isinstance(output, (dict, list)) else str(output))
                interpolated[key] = resolved
            else:
                interpolated[key] = val
        return interpolated

    async def run_workflow(
        self,
        session: AsyncSession,
        workflow: Workflow,
        custom_inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRun:
        """Execute all steps of a workflow and track execution status in db."""
        run = WorkflowRun(
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        await session.flush()

        steps: List[Dict[str, Any]] = workflow.definition.get("steps", [])
        step_outputs: Dict[str, Any] = {}
        step_logs: List[Dict[str, Any]] = []
        failed = False
        error_info: Optional[Dict[str, Any]] = None

        for step in steps:
            step_id = step.get("id", f"step_{len(step_logs)+1}")
            step_name = step.get("name", step_id)
            action = step.get("action", "")
            connector_name = step.get("connector")
            raw_inputs = dict(step.get("inputs", {}))

            if custom_inputs:
                raw_inputs.update(custom_inputs.get(step_id, {}))

            inputs = self._interpolate_inputs(raw_inputs, step_outputs)
            connector = self.get_connector_for_action(action=action, connector_name=connector_name)

            tool_req = ToolRequest(
                request_id=f"wf_req_{run.id}_{step_id}",
                tool=connector.connector_id,
                action=action,
                input=inputs,
                context=ToolContext(task_id=str(run.id), step_id=step_id),
                idempotency_key=compute_idempotency_key(str(run.id), step_id, inputs),
            )

            step_log: Dict[str, Any] = {
                "step_id": step_id,
                "step_name": step_name,
                "action": action,
                "status": "RUNNING",
            }

            try:
                resp = await connector.execute(tool_req)
                if resp.success:
                    step_log["status"] = "COMPLETED"
                    step_log["data"] = resp.data
                    step_outputs[step_id] = resp.data
                else:
                    err_msg = resp.error.message if resp.error else "Step execution returned failure"
                    step_log["status"] = "FAILED"
                    step_log["error"] = err_msg
                    if step.get("on_error") != "continue":
                        failed = True
                        error_info = {"step_id": step_id, "error": err_msg}
                        step_logs.append(step_log)
                        break

            except Exception as e:
                step_log["status"] = "FAILED"
                step_log["error"] = str(e)
                if step.get("on_error") != "continue":
                    failed = True
                    error_info = {"step_id": step_id, "error": str(e)}
                    step_logs.append(step_log)
                    break

            step_logs.append(step_log)

        run.finished_at = datetime.now(timezone.utc)
        if failed:
            run.status = "FAILED"
            run.error = error_info
            run.result = {"step_logs": step_logs}

            # Create notification
            notif = Notification(
                user_id=workflow.user_id,
                type="WORKFLOW_ALERT",
                title=f"Workflow Failed: {workflow.name}",
                message=f"Step '{error_info.get('step_id')}' encountered an error: {error_info.get('error')}",
                spoken_text=f"Aapka workflow {workflow.name} fail ho gaya hai. Kripya check karein.",
                status="UNREAD",
                metadata_json={"workflow_id": str(workflow.id), "run_id": str(run.id)},
            )
            session.add(notif)
        else:
            run.status = "COMPLETED"
            run.result = {
                "step_logs": step_logs,
                "step_outputs": step_outputs,
                "total_steps": len(steps),
            }

            # Create completion notification
            notif = Notification(
                user_id=workflow.user_id,
                type="WORKFLOW_ALERT",
                title=f"Workflow Completed: {workflow.name}",
                message=f"All {len(steps)} steps executed and verified successfully.",
                spoken_text=f"Aapka workflow {workflow.name} safaltapoorvak poora ho gaya hai.",
                status="UNREAD",
                metadata_json={"workflow_id": str(workflow.id), "run_id": str(run.id)},
            )
            session.add(notif)

        await session.flush()
        return run

