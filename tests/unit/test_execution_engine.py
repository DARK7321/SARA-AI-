import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select

from packages.connectors._sdk.contract import SideEffectType, ToolError, ErrorClass
from packages.connectors._sdk.testing import FakeConnector
from packages.core.execution.engine import StepExecutionEngine
from packages.core.db.models import User, Task, TaskStep, ToolCall, IdempotencyKey, Approval


@pytest.mark.asyncio
async def test_step_execution_success(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"exec_test_{user_id.hex[:6]}@example.com",
        name="Exec Tester",
        role="user",
        settings={},
    )
    task_id = uuid4()
    task = Task(
        id=task_id,
        user_id=user_id,
        source="chat",
        intent={"goal": "Read file"},
        path="FAST",
        status="PLANNED",
    )
    step_id = uuid4()
    step = TaskStep(
        id=step_id,
        task_id=task_id,
        step_key="read_file",
        kind="tool",
        status="PLANNED",
        inputs={"file_name": "data.csv"},
    )
    db_session.add_all([user, task, step])
    await db_session.commit()

    connector = FakeConnector(
        predefined_responses={"fake.read": {"content": "col1,col2\nval1,val2"}}
    )
    engine = StepExecutionEngine()

    result = await engine.execute_step(
        session=db_session,
        step=step,
        connector=connector,
        action="fake.read",
        inputs={"file_name": "data.csv"},
        user_id=user_id,
        side_effect=SideEffectType.READ,
    )

    assert result.success is True
    assert result.status == "SUCCEEDED"
    assert result.cached is False
    assert result.verification_status == "VERIFIED"

    # Check database status
    await db_session.refresh(step)
    assert step.status == "SUCCEEDED"

    # Verify tool_calls entry
    tc_result = await db_session.execute(
        select(ToolCall).where(ToolCall.task_step_id == step_id)
    )
    tc = tc_result.scalar_one_or_none()
    assert tc is not None
    assert tc.action == "fake.read"
    assert tc.verification_status == "VERIFIED"


@pytest.mark.asyncio
async def test_step_execution_idempotency_caching(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"idemp_test_{user_id.hex[:6]}@example.com",
        name="Idemp Tester",
        role="user",
        settings={},
    )
    task_id = uuid4()
    task = Task(
        id=task_id,
        user_id=user_id,
        source="chat",
        intent={"goal": "Write draft"},
        path="SMART",
        status="PLANNED",
    )
    step_id = uuid4()
    step = TaskStep(
        id=step_id,
        task_id=task_id,
        step_key="write_draft",
        kind="tool",
        status="AUTHORIZED",  # Pre-authorized
        inputs={"content": "hello world"},
    )
    db_session.add_all([user, task, step])
    await db_session.commit()

    connector = FakeConnector()
    engine = StepExecutionEngine()

    # First run
    res1 = await engine.execute_step(
        session=db_session,
        step=step,
        connector=connector,
        action="fake.write",
        inputs={"content": "hello world"},
        user_id=user_id,
        side_effect=SideEffectType.WRITE,
    )
    assert res1.success is True
    assert res1.cached is False
    assert len(connector.call_history) == 1

    # Second run with exact same inputs
    res2 = await engine.execute_step(
        session=db_session,
        step=step,
        connector=connector,
        action="fake.write",
        inputs={"content": "hello world"},
        user_id=user_id,
        side_effect=SideEffectType.WRITE,
    )
    assert res2.success is True
    assert res2.cached is True
    # Crucial check: Connector was NOT called a second time!
    assert len(connector.call_history) == 1


@pytest.mark.asyncio
async def test_step_execution_approval_trigger(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"appr_test_{user_id.hex[:6]}@example.com",
        name="Appr Tester",
        role="user",
        settings={},
    )
    task_id = uuid4()
    task = Task(
        id=task_id,
        user_id=user_id,
        source="chat",
        intent={"goal": "Send payment"},
        path="SMART",
        status="PLANNED",
    )
    step_id = uuid4()
    step = TaskStep(
        id=step_id,
        task_id=task_id,
        step_key="send_payment",
        kind="tool",
        status="PLANNED",
        inputs={"recipient": "bob@example.com", "amount": 50},
    )
    db_session.add_all([user, task, step])
    await db_session.commit()

    connector = FakeConnector()
    engine = StepExecutionEngine()

    result = await engine.execute_step(
        session=db_session,
        step=step,
        connector=connector,
        action="fake.send",
        inputs={"recipient": "bob@example.com", "amount": 50},
        user_id=user_id,
        side_effect=SideEffectType.EXTERNAL_SEND,
        risk_level="HIGH",
    )

    assert result.status == "WAITING_APPROVAL"
    assert result.data.get("approval_required") is True
    assert len(connector.call_history) == 0  # Tool not called yet!

