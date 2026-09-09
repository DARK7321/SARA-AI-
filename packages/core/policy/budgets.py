"""Budget Guard for OmniBrain.

Enforces spend caps from the `budgets` table before model and tool calls.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import Budget


async def check_budget(
    session: AsyncSession,
    user_id: UUID,
    estimated_cost_usd: Decimal = Decimal("0.0000"),
    scope: str = "daily",
) -> Tuple[bool, Decimal]:
    """Check whether user has exceeded their budget.
    
    Returns:
        (is_exceeded, remaining_budget_usd)
    """
    result = await session.execute(
        select(Budget).where(Budget.user_id == user_id, Budget.scope == scope)
    )
    budget = result.scalar_one_or_none()

    if not budget:
        # No budget configured -> default allow
        return False, Decimal("9999.0000")

    projected_spend = budget.spent_usd + estimated_cost_usd
    remaining = budget.limit_usd - budget.spent_usd

    if projected_spend > budget.limit_usd:
        return True, remaining

    return False, remaining


async def record_spend(
    session: AsyncSession,
    user_id: UUID,
    actual_cost_usd: Decimal,
    scope: str = "daily",
) -> None:
    """Record actual spend against the user's budget."""
    if actual_cost_usd <= Decimal("0.0000"):
        return

    result = await session.execute(
        select(Budget).where(Budget.user_id == user_id, Budget.scope == scope)
    )
    budget = result.scalar_one_or_none()

    if budget:
        budget.spent_usd += actual_cost_usd
        await session.flush()
