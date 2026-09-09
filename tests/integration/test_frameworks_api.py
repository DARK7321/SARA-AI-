"""Integration tests for Multi-Agent Frameworks API."""
import pytest
from packages.core.security.auth import create_access_token
from packages.core.safety.kill_switch import get_kill_switch


@pytest.mark.asyncio
async def test_frameworks_api_list_and_execution(test_client, test_user, monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List Frameworks
    res = await test_client.get("/v1/frameworks", headers=headers)
    assert res.status_code == 200
    frameworks = res.json()["data"]["frameworks"]
    assert len(frameworks) == 3
    names = [f["framework"] for f in frameworks]
    assert "crewai" in names
    assert "langgraph" in names
    assert "autogen" in names

    # 2. Run CrewAI
    crew_res = await test_client.post(
        "/v1/frameworks/crewai/run",
        json={"task": "Deep research on LLM caching patterns", "template": "deep_research"},
        headers=headers,
    )
    assert crew_res.status_code == 200
    crew_data = crew_res.json()["data"]
    assert crew_data["framework"] == "crewai"
    assert crew_data["status"] == "COMPLETED"
    assert len(crew_data["agent_dialogue"]) >= 3
    run_id = crew_data["run_id"]

    # 3. Retrieve Run by ID
    get_run_res = await test_client.get(f"/v1/frameworks/runs/{run_id}", headers=headers)
    assert get_run_res.status_code == 200
    assert get_run_res.json()["data"]["run_id"] == run_id

    # 4. Run LangGraph
    lg_res = await test_client.post(
        "/v1/frameworks/langgraph/run",
        json={"task": "Process incoming PDF documentation", "template": "document_processor"},
        headers=headers,
    )
    assert lg_res.status_code == 200
    lg_data = lg_res.json()["data"]
    assert lg_data["framework"] == "langgraph"
    assert lg_data["status"] == "COMPLETED"
    assert "nodes_visited" in lg_data["metadata"]

    # 5. Run AutoGen
    ag_res = await test_client.post(
        "/v1/frameworks/autogen/run",
        json={"task": "Design async worker pool", "template": "coder_and_critic"},
        headers=headers,
    )
    assert ag_res.status_code == 200
    ag_data = ag_res.json()["data"]
    assert ag_data["framework"] == "autogen"
    assert ag_data["status"] == "COMPLETED"
    assert ag_data["metadata"]["terminated_cleanly"] is True

    # 6. Test Kill Switch lockdown blocks framework execution
    kill_switch = get_kill_switch()
    await kill_switch.activate(reason="Test lockdown")
    try:
        locked_res = await test_client.post(
            "/v1/frameworks/crewai/run",
            json={"task": "Should be blocked by kill switch"},
            headers=headers,
        )
        assert locked_res.status_code == 423
        assert "Emergency Kill Switch is ACTIVE" in locked_res.json()["detail"]
    finally:
        await kill_switch.deactivate()

