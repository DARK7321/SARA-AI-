import pytest
from decimal import Decimal
from uuid import uuid4

from packages.connectors._sdk.contract import SideEffectType
from packages.core.policy.engine import PolicyEngine, PolicyEffect
from packages.core.policy.budgets import check_budget, record_spend
from packages.core.policy.approvals import create_approval_request, resolve_approval
from packages.core.db.models import User, Budget, Task, TaskStep


def test_policy_read_allowed():
    engine = PolicyEngine()
    result = engine.evaluate(
        action="docs.read",
        side_effect=SideEffectType.READ,
        risk_level="LOW",
    )
    assert result.effect == PolicyEffect.ALLOW


def test_policy_destructive_requires_confirmation():
    engine = PolicyEngine()
    result = engine.evaluate(
        action="files.delete",
        side_effect=SideEffectType.DESTRUCTIVE,
        risk_level="HIGH",
    )
    assert result.effect == PolicyEffect.CONFIRM


def test_policy_external_send_requires_confirmation():
    engine = PolicyEngine()
    result = engine.evaluate(
        action="email.send",
        side_effect=SideEffectType.EXTERNAL_SEND,
        risk_level="MEDIUM",
    )
    assert result.effect == PolicyEffect.CONFIRM


def test_policy_budget_exceeded_denied():
    engine = PolicyEngine()
    result = engine.evaluate(
        action="docs.read",
        side_effect=SideEffectType.READ,
        budget_exceeded=True,
    )
    assert result.effect == PolicyEffect.DENY
    assert "budget" in result.reason.lower()


def test_policy_level_0_strict():
    engine = PolicyEngine()
    result = engine.evaluate(
        action="docs.read",
        side_effect=SideEffectType.READ,
        autonomy_level=0,
    )
    assert result.effect == PolicyEffect.CONFIRM


@pytest.mark.asyncio
async def test_budget_guard_database_check(db_session):
    from datetime import datetime, timezone

    # Create test user & budget
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"budget_test_{user_id.hex[:6]}@example.com",
        name="Budget Tester",
        role="user",
        settings={},
    )
    budget = Budget(
        user_id=user_id,
        scope="daily",
        limit_usd=Decimal("5.0000"),
        spent_usd=Decimal("4.5000"),
        period_start=datetime.now(timezone.utc),
    )
    db_session.add_all([user, budget])
    await db_session.commit()

    # Small expense ($0.20) should not exceed ($4.50 + $0.20 <= $5.00)
    exceeded, remaining = await check_budget(db_session, user_id, Decimal("0.2000"))
    assert exceeded is False
    assert remaining == Decimal("0.5000")

    # Large expense ($1.00) should exceed ($4.50 + $1.00 > $5.00)
    exceeded, remaining = await check_budget(db_session, user_id, Decimal("1.0000"))
    assert exceeded is True

    # Record spend
    await record_spend(db_session, user_id, Decimal("0.3000"))
    await db_session.refresh(budget)
    assert budget.spent_usd == Decimal("4.8000")


@pytest.mark.asyncio
async def test_approval_lifecycle(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"approval_test_{user_id.hex[:6]}@example.com",
        name="Approval Tester",
        role="user",
        settings={},
    )
    task_id = uuid4()
    task = Task(
        id=task_id,
        user_id=user_id,
        source="chat",
        intent={"goal": "Send report"},
        path="SMART",
        status="PLANNED",
    )
    step_id = uuid4()
    step = TaskStep(
        id=step_id,
        task_id=task_id,
        step_key="send_email",
        kind="tool",
        status="PLANNED",
        inputs={"to": "client@example.com"},
    )
    db_session.add_all([user, task, step])
    await db_session.commit()

    # Create approval
    summary = {
        "what": "Send Email",
        "why": "Weekly client report",
        "target": "client@example.com",
        "risk": "MEDIUM",
    }
    approval = await create_approval_request(
        db_session, task_id, step_id, user_id, summary
    )
    assert approval.status == "pending"

    await db_session.refresh(step)
    await db_session.refresh(task)
    assert step.status == "WAITING_APPROVAL"
    assert task.status == "WAITING_APPROVAL"

    # Resolve approval
    resolved = await resolve_approval(db_session, approval.id, "approved")
    assert resolved.status == "approved"
    await db_session.refresh(step)
    assert step.status == "AUTHORIZED"
