import pytest
from packages.connectors.gmail.client import GmailConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_gmail_read_and_search():
    connector = GmailConnector()

    # Test search
    search_req = ToolRequest(
        request_id="req_gmail_1",
        tool="connector-gmail",
        action="gmail.search",
        input={"query": "meeting"},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_1",
    )
    res = await connector.execute(search_req)
    assert res.success is True
    assert len(res.data["messages"]) >= 1
    assert "Meeting" in res.data["messages"][0]["subject"]

    # Test read
    msg_id = res.data["messages"][0]["id"]
    read_req = ToolRequest(
        request_id="req_gmail_2",
        tool="connector-gmail",
        action="gmail.read",
        input={"message_id": msg_id},
        context=ToolContext(task_id="t1", step_id="s2"),
        idempotency_key="key_2",
    )
    read_res = await connector.execute(read_req)
    assert read_res.success is True
    assert read_res.data["id"] == msg_id


@pytest.mark.asyncio
async def test_gmail_draft_with_verification():
    connector = GmailConnector()

    draft_req = ToolRequest(
        request_id="req_gmail_3",
        tool="connector-gmail",
        action="gmail.draft",
        input={"to": "client@example.com", "subject": "Proposal Draft", "body": "Please find proposal."},
        context=ToolContext(task_id="t1", step_id="s3"),
        idempotency_key="key_3",
    )
    res = await connector.execute(draft_req)
    assert res.success is True
    assert "id" in res.data
    assert res.verification_hints["check"] == "draft_created"

    # Post-condition verification check
    verified = await connector.verify(draft_req.action, res.verification_hints)
    assert verified is True


@pytest.mark.asyncio
async def test_gmail_send_with_verification():
    connector = GmailConnector()

    send_req = ToolRequest(
        request_id="req_gmail_4",
        tool="connector-gmail",
        action="gmail.send",
        input={"to": "client@example.com", "subject": "Official Invoice", "body": "Attached."},
        context=ToolContext(task_id="t1", step_id="s4"),
        idempotency_key="key_4",
    )
    res = await connector.execute(send_req)
    assert res.success is True
    assert res.verification_hints["check"] == "message_sent"

    verified = await connector.verify(send_req.action, res.verification_hints)
    assert verified is True

