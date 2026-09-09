"""Unit tests for Universal Multi-Agent Frameworks Connector."""
import pytest
from packages.connectors._sdk.contract import ToolRequest, ToolContext
from packages.connectors.frameworks.client import FrameworksConnector


@pytest.mark.asyncio
async def test_frameworks_connector_dry_run():
    connector = FrameworksConnector()
    req = ToolRequest(
        request_id="req_dry",
        tool="connector-frameworks",
        action="crewai.execute",
        input={"task": "Simulated crew run"},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_dry",
        dry_run=True,
    )
    resp = await connector.execute(req)
    assert resp.success is True
    assert resp.data["simulated"] is True


@pytest.mark.asyncio
async def test_frameworks_connector_list():
    connector = FrameworksConnector()
    req = ToolRequest(
        request_id="req_list",
        tool="connector-frameworks",
        action="frameworks.list",
        input={},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_list",
    )
    resp = await connector.execute(req)
    assert resp.success is True
    frameworks = resp.data["frameworks"]
    assert len(frameworks) == 3
    names = [f["framework"] for f in frameworks]
    assert "crewai" in names
    assert "langgraph" in names
    assert "autogen" in names


@pytest.mark.asyncio
async def test_frameworks_connector_execute_crewai(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    connector = FrameworksConnector()
    req = ToolRequest(
        request_id="req_crew",
        tool="connector-frameworks",
        action="crewai.execute",
        input={
            "task": "Research multi-tenant vector databases",
            "crew_name": "deep_research",
        },
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_crew",
    )
    resp = await connector.execute(req)
    assert resp.success is True
    assert resp.data["framework"] == "crewai"
    assert resp.data["status"] == "COMPLETED"
    assert len(resp.data["agent_dialogue"]) >= 3


@pytest.mark.asyncio
async def test_frameworks_connector_execute_autogen(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    connector = FrameworksConnector()
    req = ToolRequest(
        request_id="req_ag",
        tool="connector-frameworks",
        action="autogen.execute",
        input={
            "task": "Design async worker retry logic",
            "team_name": "coder_and_critic",
        },
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_ag",
    )
    resp = await connector.execute(req)
    assert resp.success is True
    assert resp.data["framework"] == "autogen"
    assert resp.data["status"] == "COMPLETED"

