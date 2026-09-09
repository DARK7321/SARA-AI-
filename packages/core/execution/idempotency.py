"""Idempotency Engine for OmniBrain.

Guarantees zero-duplicate side-effects across network retries and server restarts
using the PostgreSQL idempotency_keys table.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import IdempotencyKey


class IdempotencyEngine:
    """Manages idempotent execution locks and cached responses."""

    def __init__(self, default_ttl_hours: int = 48):
        self.default_ttl_hours = default_ttl_hours

    async def acquire_or_get_cached(
        self,
        session: AsyncSession,
        idempotency_key: str,
        tool: str,
        action: str,
        fingerprint: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Attempt to acquire execution lock or return cached response.
        
        Returns:
            (should_execute: bool, cached_response: Optional[dict])
            - If (False, response) -> Cache hit! Do NOT execute tool. Return cached response.
            - If (True, None) -> Lock acquired, proceed to execute.
        """
        result = await session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        )
        record = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if record:
            # Check expiration
            if record.expires_at < now:
                # Expired key, reset to IN_PROGRESS
                record.status = "IN_PROGRESS"
                record.created_at = now
                record.expires_at = now + timedelta(hours=self.default_ttl_hours)
                await session.flush()
                return True, None

            if record.status == "COMPLETED" and record.response is not None:
                # Safe cache hit
                return False, record.response

            if record.status == "IN_PROGRESS":
                # Currently executing elsewhere; prevent duplicate execution
                return False, {"status": "in_progress", "message": "Concurrent execution in progress"}

        # First execution, record key with IN_PROGRESS lock
        new_record = IdempotencyKey(
            key=idempotency_key,
            tool=tool,
            action=action,
            status="IN_PROGRESS",
            fingerprint=fingerprint,
            created_at=now,
            expires_at=now + timedelta(hours=self.default_ttl_hours),
        )
        session.add(new_record)
        await session.flush()
        return True, None

    async def complete(
        self,
        session: AsyncSession,
        idempotency_key: str,
        response_data: Dict[str, Any],
    ) -> None:
        """Mark idempotency key as COMPLETED and store response payload."""
        result = await session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "COMPLETED"
            record.response = response_data
            await session.flush()

    async def fail(
        self,
        session: AsyncSession,
        idempotency_key: str,
        is_retryable: bool = False,
    ) -> None:
        """Handle failure: if retryable delete key to allow immediate retry, else mark FAILED."""
        result = await session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        )
        record = result.scalar_one_or_none()
        if record:
            if is_retryable:
                await session.delete(record)
            else:
                record.status = "FAILED"
            await session.flush()

