"""Integration test for Workflows and Automations REST API."""
import pytest
from sqlalchemy import delete
from packages.core.db.models import Workflow, WorkflowRun
from packages.core.security.auth import create_access_token


@pytest.mark.asyncio
async def test_workflows_api_crud_and_execution(test_client, test_user, db_session):
    # Clear prior workflows/runs for isolation
    await db_session.execute(delete(WorkflowRun).where(WorkflowRun.user_id == test_user.id))
    await db_session.execute(delete(Workflow).where(Workflow.user_id == test_user.id))
    await db_session.commit()

    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List workflows (should auto-seed default templates)
    res = await test_client.get("/v1/workflows", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["workflows"]) >= 3
    assert len(data["templates"]) >= 3
    seeded_wf_id = data["workflows"][0]["id"]

    # 2. Run the seeded workflow
    run_res = await test_client.post(f"/v1/workflows/{seeded_wf_id}/run", json={}, headers=headers)
    assert run_res.status_code == 200
    run_data = run_res.json()["data"]
    assert run_data["status"] == "COMPLETED"
    assert run_data["result"] is not None
    assert "step_logs" in run_data["result"]

    # 3. List runs for the workflow
    runs_res = await test_client.get(f"/v1/workflows/{seeded_wf_id}/runs", headers=headers)
    assert runs_res.status_code == 200
    runs_data = runs_res.json()["data"]
    assert len(runs_data["runs"]) >= 1
    assert runs_data["runs"][0]["status"] == "COMPLETED"

    # 4. Create custom workflow
    create_payload = {
        "name": "Integration Test Custom Flow",
        "description": "Scrapes news and notifies Slack",
        "trigger_type": "manual",
        "definition": {
            "steps": [
                {
                    "id": "step_extract",
                    "name": "Extract Content",
                    "connector": "browser",
                    "action": "browser.extract_content",
                    "inputs": {"url": "https://news.ycombinator.com"},
                },
                {
                    "id": "step_post",
                    "name": "Post to Slack",
                    "connector": "slack",
                    "action": "slack.post_message",
                    "inputs": {"channel": "#dev-team", "text": "Scraped article ready."},
                },
            ]
        },
    }
    create_res = await test_client.post("/v1/workflows", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    custom_wf = create_res.json()["data"]
    assert custom_wf["name"] == "Integration Test Custom Flow"
    custom_id = custom_wf["id"]

    # 5. Run custom workflow
    run_custom_res = await test_client.post(f"/v1/workflows/{custom_id}/run", json={}, headers=headers)
    assert run_custom_res.status_code == 200
    assert run_custom_res.json()["data"]["status"] == "COMPLETED"

    # 6. Delete custom workflow
    delete_res = await test_client.delete(f"/v1/workflows/{custom_id}", headers=headers)
    assert delete_res.status_code == 200
    assert delete_res.json()["data"]["deleted_id"] == custom_id

    # Verify deletion
    get_res = await test_client.get(f"/v1/workflows/{custom_id}", headers=headers)
    assert get_res.status_code == 404

