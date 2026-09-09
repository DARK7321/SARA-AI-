import pytest
from packages.connectors.gsheets.client import GSheetsConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_gsheets_read_and_append():
    connector = GSheetsConnector()

    # Read rows
    read_req = ToolRequest(
        request_id="req_sheet_1",
        tool="connector-gsheets",
        action="sheets.read_rows",
        input={"spreadsheet_id": "sheet_101", "range": "Sheet1!A1:C10"},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="sheet_k1",
    )
    res = await connector.execute(read_req)
    assert res.success is True
    assert len(res.data["rows"]) >= 3

    # Append rows
    append_req = ToolRequest(
        request_id="req_sheet_2",
        tool="connector-gsheets",
        action="sheets.append_rows",
        input={"spreadsheet_id": "sheet_101", "range": "Sheet1!A1", "values": [["Product", "$30,000", "$5,000"]]},
        context=ToolContext(task_id="t1", step_id="s2"),
        idempotency_key="sheet_k2",
    )
    append_res = await connector.execute(append_req)
    assert append_res.success is True
    assert append_res.data["appended_rows"] == 1


@pytest.mark.asyncio
async def test_gsheets_update_cell_with_reread_verification():
    connector = GSheetsConnector()

    update_req = ToolRequest(
        request_id="req_sheet_3",
        tool="connector-gsheets",
        action="sheets.update_cell",
        input={"spreadsheet_id": "sheet_101", "cell": "B2", "value": "$55,000"},
        context=ToolContext(task_id="t1", step_id="s3"),
        idempotency_key="sheet_k3",
    )
    res = await connector.execute(update_req)
    assert res.success is True
    assert res.data["value"] == "$55,000"

    # Re-read verification: check that cell B2 actually holds "$55,000"
    verified = await connector.verify(update_req.action, res.verification_hints)
    assert verified is True

