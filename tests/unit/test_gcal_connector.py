import pytest
from packages.connectors.gcal.client import GCalConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_gcal_list_and_create_event():
    connector = GCalConnector()

    # List events
    list_req = ToolRequest(
        request_id="req_cal_1",
        tool="connector-gcal",
        action="calendar.list_events",
        input={"max_results": 5},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="cal_k1",
    )
    res = await connector.execute(list_req)
    assert res.success is True
    assert len(res.data["events"]) >= 1

    # Create event
    create_req = ToolRequest(
        request_id="req_cal_2",
        tool="connector-gcal",
        action="calendar.create_event",
        input={
            "title": "Strategy Sync",
            "start_time": "2026-09-08T15:00:00Z",
            "end_time": "2026-09-08T16:00:00Z",
            "attendees": ["partner@example.com"],
        },
        context=ToolContext(task_id="t1", step_id="s2"),
        idempotency_key="cal_k2",
    )
    create_res = await connector.execute(create_req)
    assert create_res.success is True
    assert create_res.data["summary"] == "Strategy Sync"

    # Verify event exists
    verified = await connector.verify(create_req.action, create_res.verification_hints)
    assert verified is True

