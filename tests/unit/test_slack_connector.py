"""Unit tests for Slack Universal Tool Connector."""
import pytest
from packages.connectors.slack.client import SlackConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_slack_post_message_and_verify():
    connector = SlackConnector()
    req = ToolRequest(
        request_id="req_slack_1",
        tool="connector-slack",
        action="slack.post_message",
        input={"channel": "#general", "text": "Hello from OmniBrain Automation!"},
        context=ToolContext(task_id="t_slack", step_id="s_sl1"),
        idempotency_key="key_sl_1",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["ok"] is True
    assert res.data["channel"] == "#general"
    assert "ts" in res.data
    assert res.verification_hints["check"] == "message_posted"

    # Verification check
    verified = await connector.verify(req.action, res.data)
    assert verified is True


@pytest.mark.asyncio
async def test_slack_read_channel():
    connector = SlackConnector()
    req = ToolRequest(
        request_id="req_slack_2",
        tool="connector-slack",
        action="slack.read_channel",
        input={"channel": "#general", "limit": 5},
        context=ToolContext(task_id="t_slack", step_id="s_sl2"),
        idempotency_key="key_sl_2",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "messages" in res.data
    assert len(res.data["messages"]) >= 1


@pytest.mark.asyncio
async def test_slack_list_channels():
    connector = SlackConnector()
    req = ToolRequest(
        request_id="req_slack_3",
        tool="connector-slack",
        action="slack.list_channels",
        input={},
        context=ToolContext(task_id="t_slack", step_id="s_sl3"),
        idempotency_key="key_sl_3",
    )
    res = await connector.execute(req)
    assert res.success is True
    assert "channels" in res.data
    assert any(ch["name"] == "general" for ch in res.data["channels"])


@pytest.mark.asyncio
async def test_slack_dry_run():
    connector = SlackConnector()
    req = ToolRequest(
        request_id="req_slack_4",
        tool="connector-slack",
        action="slack.post_message",
        input={"channel": "#general", "text": "Dry run message"},
        context=ToolContext(task_id="t_slack", step_id="s_sl4"),
        idempotency_key="key_sl_4",
        dry_run=True,
    )
    res = await connector.execute(req)
    assert res.success is True
    assert res.data["simulated"] is True
    assert res.verification_hints["dry_run"] is True
