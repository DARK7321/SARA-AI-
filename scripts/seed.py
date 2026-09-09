"""Seed script for OmniBrain.

Creates the initial owner user, default budget, and initial feature flags.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
import yaml

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from apps.api.settings import get_settings
from packages.core.db.session import async_session_maker
from packages.core.db.models import User, Budget, FeatureFlag
from packages.core.security.auth import get_password_hash


async def seed() -> None:
    settings = get_settings()
    print("Connecting to database for seeding...")

    async with async_session_maker() as session:
        async with session.begin():
            # 1. Seed Owner User
            owner_email = settings.OWNER_EMAIL
            result = await session.execute(select(User).where(User.email == owner_email))
            owner = result.scalar_one_or_none()

            if not owner:
                print(f"Creating owner user: {owner_email}...")
                owner = User(
                    email=owner_email,
                    name="OmniBrain Owner",
                    role="owner",
                    password_hash=get_password_hash(settings.OWNER_PASSWORD),
                    timezone="UTC",
                    settings={"theme": "system", "default_view": "home"},
                )
                session.add(owner)
                await session.flush()
                print(f"Owner user created with ID: {owner.id}")
            else:
                print(f"Owner user already exists with ID: {owner.id}")

            # 2. Seed Default Budget ($5.00 daily)
            budget_result = await session.execute(
                select(Budget).where(Budget.user_id == owner.id, Budget.scope == "daily")
            )
            existing_budget = budget_result.scalar_one_or_none()
            if not existing_budget:
                print("Creating default daily budget ($5.00)...")
                budget = Budget(
                    user_id=owner.id,
                    scope="daily",
                    limit_usd=Decimal("5.0000"),
                    spent_usd=Decimal("0.0000"),
                    period_start=datetime.now(timezone.utc),
                )
                session.add(budget)
            else:
                print("Default daily budget already exists.")

            # 3. Seed Feature Flags from config/flags.yaml
            try:
                with open("config/flags.yaml", "r", encoding="utf-8") as f:
                    flag_config = yaml.safe_load(f)
                    flags = flag_config.get("flags", {})
                    for flag_key, enabled in flags.items():
                        flag_result = await session.execute(
                            select(FeatureFlag).where(FeatureFlag.key == flag_key)
                        )
                        if not flag_result.scalar_one_or_none():
                            session.add(
                                FeatureFlag(key=flag_key, enabled=bool(enabled), rollout={})
                            )
                            print(f"Feature flag added: {flag_key} (enabled={enabled})")
            except Exception as e:
                print(f"Notice: Failed to load config/flags.yaml: {e}")

        print("\nSeed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
