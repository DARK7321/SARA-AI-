"""Unit tests for WorkflowEngine."""
import pytest
from sqlalchemy import delete
from packages.core.db.models import Workflow, WorkflowRun, Notification
from packages.core.workflows.engine import WorkflowEngine, BUILTIN_TEMPLATES


@pytest.mark.asyncio
async def test_workflow_engine_templates():
    engine = WorkflowEngine()
    templates = engine.list_templates()
    assert len(templates) >= 3
    ids = [t["template_id"] for t in templates]
    assert "morning_standup_briefing" in ids
    assert "github_triage_alert" in ids
    assert "tech_intelligence_digest" in ids


@pytest.mark.asyncio
async def test_workflow_engine_seed_and_run(db_session, test_user):
    engine = WorkflowEngine()

    # Clean up prior test runs
    await db_session.execute(delete(WorkflowRun).where(WorkflowRun.user_id == test_user.id))
    await db_session.execute(delete(Workflow).where(Workflow.user_id == test_user.id))
    await db_session.flush()

    # 1. Seed workflows
    seeded = await engine.seed_default_workflows(db_session, test_user.id)
    assert len(seeded) >= 3

    # 2. Select one workflow to execute
    wf = seeded[0]
    run = await engine.run_workflow(db_session, wf)

    assert run.status == "COMPLETED"
    assert run.finished_at is not None
    assert run.result is not None
    assert "step_logs" in run.result
    assert len(run.result["step_logs"]) == len(wf.definition["steps"])
    assert all(log["status"] == "COMPLETED" for log in run.result["step_logs"])


@pytest.mark.asyncio
async def test_workflow_engine_custom_step_execution(db_session, test_user):
    engine = WorkflowEngine()

    # Define custom workflow with multiple steps
    custom_wf = Workflow(
        user_id=test_user.id,
        name="Custom Test Pipeline",
        description="Testing custom pipeline step outputs",
        trigger_type="manual",
        is_active=True,
        definition={
            "steps": [
                {
                    "id": "s1",
                    "name": "Step 1: Check GitHub",
                    "connector": "github",
                    "action": "github.list_issues",
                    "inputs": {"repo": "owner/omnibrain"},
                },
                {
                    "id": "s2",
                    "name": "Step 2: Slack Alert",
                    "connector": "slack",
                    "action": "slack.post_message",
                    "inputs": {"channel": "#general", "text": "Issues scanned successfully"},
                },
            ]
        },
    )
    db_session.add(custom_wf)
    await db_session.flush()

    run = await engine.run_workflow(db_session, custom_wf)
    assert run.status == "COMPLETED"
    assert len(run.result["step_logs"]) == 2
    assert run.result["step_logs"][0]["status"] == "COMPLETED"
    assert run.result["step_logs"][1]["status"] == "COMPLETED"

