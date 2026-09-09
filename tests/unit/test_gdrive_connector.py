import pytest
from packages.connectors.gdrive.client import GDriveConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext


@pytest.mark.asyncio
async def test_gdrive_list_and_read():
    connector = GDriveConnector()

    list_req = ToolRequest(
        request_id="req_drive_1",
        tool="connector-gdrive",
        action="drive.list",
        input={"query": "roadmap"},
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="drive_k1",
    )
    res = await connector.execute(list_req)
    assert res.success is True
    assert len(res.data["files"]) >= 1

    file_id = res.data["files"][0]["id"]
    read_req = ToolRequest(
        request_id="req_drive_2",
        tool="connector-gdrive",
        action="drive.read",
        input={"file_id": file_id},
        context=ToolContext(task_id="t1", step_id="s2"),
        idempotency_key="drive_k2",
    )
    read_res = await connector.execute(read_req)
    assert read_res.success is True
    assert read_res.data["id"] == file_id


@pytest.mark.asyncio
async def test_gdrive_create_and_share_with_verification():
    connector = GDriveConnector()

    create_req = ToolRequest(
        request_id="req_drive_3",
        tool="connector-gdrive",
        action="drive.create",
        input={"name": "Meeting Notes.txt", "content": "Action items for sprint."},
        context=ToolContext(task_id="t1", step_id="s3"),
        idempotency_key="drive_k3",
    )
    res = await connector.execute(create_req)
    assert res.success is True
    file_id = res.data["id"]

    # Verify creation
    verified = await connector.verify(create_req.action, res.verification_hints)
    assert verified is True

    # Share file
    share_req = ToolRequest(
        request_id="req_drive_4",
        tool="connector-gdrive",
        action="drive.share",
        input={"file_id": file_id, "email": "collaborator@example.com", "role": "editor"},
        context=ToolContext(task_id="t1", step_id="s4"),
        idempotency_key="drive_k4",
    )
    share_res = await connector.execute(share_req)
    assert share_res.success is True
    assert share_res.data["shared"] is True

    # Verify share
    share_verified = await connector.verify(share_req.action, share_res.verification_hints)
    assert share_verified is True

