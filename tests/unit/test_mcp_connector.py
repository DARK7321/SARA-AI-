"""Unit tests for Model Context Protocol (MCP) Universal Connector."""
import pytest
from packages.connectors.mcp.client import MCPConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_mcp_filesystem_read():
    connector = MCPConnector()
    req = ToolRequest(
        request_id="req_mcp_1",
        tool="connector-mcp",
        action="mcp.filesystem.read_file",
        input={"path": "README.md"},
        context=ToolContext(task_id="t_mcp", step_id="s_mcp1"),
        idempotency_key="key_mcp_1",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "OmniBrain" in res.data["content"]
    assert res.verification_hints["check"] == "mcp_tool_executed"

    verified = await connector.verify(req.action, res.verification_hints)
    assert verified is True


@pytest.mark.asyncio
async def test_mcp_sqlite_query():
    connector = MCPConnector()
    req = ToolRequest(
        request_id="req_mcp_2",
        tool="connector-mcp",
        action="mcp.sqlite.query",
        input={"query": "SELECT * FROM users"},
        context=ToolContext(task_id="t_mcp", step_id="s_mcp2"),
        idempotency_key="key_mcp_2",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "rows" in res.data
    assert len(res.data["rows"]) >= 1


@pytest.mark.asyncio
async def test_mcp_dry_run():
    connector = MCPConnector()
    req = ToolRequest(
        request_id="req_mcp_3",
        tool="connector-mcp",
        action="mcp.fetch.get",
        input={"url": "https://example.com/api"},
        context=ToolContext(task_id="t_mcp", step_id="s_mcp3"),
        idempotency_key="key_mcp_3",
        dry_run=True,
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["simulated"] is True


@pytest.mark.asyncio
async def test_mcp_health_and_capabilities():
    connector = MCPConnector()
    health = await connector.health_check()
    assert health["status"] == "ONLINE"
    assert health["connector_id"] == "connector-mcp"

    caps = connector.get_capabilities()
    assert "mcp.filesystem.read_file" in caps
    assert "mcp.sqlite.query" in caps

