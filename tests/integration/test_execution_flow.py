"""End-to-End Integration and Chaos Tests for OmniBrain Phase 1.

Verifies:
1. Complete Plan -> Policy -> Execute -> Verify -> Report flow.
2. Human-in-the-Loop (HITL) approval pause and resume flow.
3. Chaos retry resilience with 0 duplicate side effects.
"""
import pytest
from uuid import uuid4
from sqlalchemy import select

from packages.core.db.models import Task, TaskStep, ToolCall, IdempotencyKey
from apps.worker.main import execute_task_job


@pytest.mark.asyncio
async def test_end_to_end_task_creation_and_execution(test_client):
    # 1. Login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Submit Task
    task_res = await test_client.post(
        "/v1/tasks",
        headers=headers,
        json={
            "goal": "Process quarterly sales data",
            "path": "FAST",
            "source": "chat",
            "initial_inputs": {"quarter": "Q1", "records": 50},
        },
    )
    assert task_res.status_code == 200
    task_data = task_res.json()["data"]
    task_id = task_data["task_id"]
    assert task_data["status"] == "COMPLETED"

    # 3. Verify task details via GET /v1/tasks/{task_id}
    detail_res = await test_client.get(f"/v1/tasks/{task_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["status"] == "COMPLETED"
    assert len(detail["steps"]) >= 1
    assert detail["steps"][0]["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_end_to_end_approval_pause_and_resume(test_client, db_session):
    # 1. Login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get owner user
    me_res = await test_client.get("/v1/auth/me", headers=headers)
    owner_id = me_res.json()["data"]["id"]

    # 2. Create Task with a High-Risk step that triggers approval
    task = Task(
        user_id=owner_id,
        source="chat",
        intent={"goal": "Delete legacy archive"},
        path="SMART",
        status="PLANNED",
    )
    db_session.add(task)
    await db_session.flush()

    # Step has DESTRUCTIVE side-effect
    step = TaskStep(
        task_id=task.id,
        step_key="delete_archive",
        kind="tool",
        capability="fake.delete",
        status="PLANNED",
        inputs={"archive_id": "arc_999"},
    )
    db_session.add(step)
    await db_session.commit()

    # 3. Worker executes job -> pauses on approval
    job_result = await execute_task_job({"worker_id": "test-worker"}, str(task.id), session=db_session)
    await db_session.commit()
    assert job_result["status"] == "waiting_approval"

    # 4. Check Pending Approvals API
    pending_res = await test_client.get("/v1/approvals/pending", headers=headers)
    assert pending_res.status_code == 200
    approvals = pending_res.json()["data"]
    assert len(approvals) >= 1
    approval = next(a for a in approvals if str(a["task_id"]) == str(task.id))
    approval_id = approval["id"]
    assert approval["status"] == "pending"

    # 5. Approve the action via API
    decision_res = await test_client.post(
        f"/v1/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "approved"},
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["data"]["status"] == "approved"

    # 6. Verify task finished COMPLETED after approval resume
    await db_session.refresh(task)
    assert task.status == "COMPLETED"


@pytest.mark.asyncio
async def test_chaos_resume_prevents_duplicate_execution(test_client, db_session):
    # 1. Login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await test_client.get("/v1/auth/me", headers=headers)
    owner_id = me_res.json()["data"]["id"]

    # 2. Setup Task with step
    task = Task(
        user_id=owner_id,
        source="chat",
        intent={"goal": "Send invoice notification"},
        path="FAST",
        status="PLANNED",
    )
    db_session.add(task)
    await db_session.flush()

    step = TaskStep(
        task_id=task.id,
        step_key="notify_user",
        kind="tool",
        capability="fake.notify",
        status="PLANNED",
        inputs={"invoice_id": "inv_101", "amount": 250},
    )
    db_session.add(step)
    await db_session.commit()

    # 3. First execution
    res1 = await execute_task_job({"worker_id": "worker-alpha"}, str(task.id), session=db_session)
    await db_session.commit()
    assert res1["status"] == "COMPLETED"

    # Count tool_calls records
    calls_query = select(ToolCall).where(ToolCall.task_step_id == step.id)
    initial_calls = (await db_session.execute(calls_query)).scalars().all()
    assert len(initial_calls) == 1

    # 4. Simulate Chaos / Network Retry: Reset step status to RUNNING and re-execute
    step.status = "RUNNING"
    await db_session.commit()

    res2 = await execute_task_job({"worker_id": "worker-beta"}, str(task.id), session=db_session)
    await db_session.commit()
    assert res2["status"] == "COMPLETED"

    # Verify idempotency key was hit and NO second external call was recorded!
    final_calls = (await db_session.execute(calls_query)).scalars().all()
    assert len(final_calls) == 1, "Duplicate side-effect prevented by IdempotencyEngine"
