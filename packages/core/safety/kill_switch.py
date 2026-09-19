"""Emergency Kill Switch Manager for OmniBrain.

Provides an instant system-wide cutoff that blocks all autonomous tool execution
and halts worker tasks immediately upon activation.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from apps.api.settings import get_settings

logger = logging.getLogger("omnibrain.safety.kill_switch")

REDIS_KILL_SWITCH_KEY = "omnibrain:system:kill_switch"


class EmergencyKillSwitch:
    """Manages the global emergency kill switch state."""

    def __init__(self, redis_url: Optional[str] = None):
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._in_memory_state: Dict[str, Any] = {
            "active": False,
            "activated_at": None,
            "reason": None,
            "triggered_by": None,
        }

    async def _get_client(self) -> Optional[aioredis.Redis]:
        if self._redis is not None:
            try:
                await self._redis.ping()
                return self._redis
            except Exception as e:
                logger.debug(f"Redis client stale for kill-switch ({e}), recreating connection.")
                self._redis = None

        try:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2.0,
            )
            await self._redis.ping()
        except Exception as e:
            logger.debug(f"Redis connection unavailable for kill-switch ({e}), falling back to memory.")
            self._redis = None
        return self._redis

    async def is_active(self) -> bool:
        """Return whether the emergency kill switch is currently active."""
        client = await self._get_client()
        if client:
            try:
                raw = await client.get(REDIS_KILL_SWITCH_KEY)
                if raw:
                    data = json.loads(raw)
                    return bool(data.get("active", False))
                return False
            except Exception as e:
                logger.warning(f"Failed to read kill switch from Redis ({e}), using memory fallback.")
        return bool(self._in_memory_state.get("active", False))

    async def get_status(self) -> Dict[str, Any]:
        """Return the complete kill switch state."""
        client = await self._get_client()
        if client:
            try:
                raw = await client.get(REDIS_KILL_SWITCH_KEY)
                if raw:
                    return json.loads(raw)
                return {
                    "active": False,
                    "activated_at": None,
                    "reason": None,
                    "triggered_by": None,
                }
            except Exception as e:
                logger.warning(f"Failed to query kill switch status ({e}), using memory fallback.")
        return dict(self._in_memory_state)

    async def activate(
        self,
        reason: str = "Manual emergency stop triggered by user",
        triggered_by: str = "user",
    ) -> Dict[str, Any]:
        """Activate emergency stop, locking out all autonomous tool execution."""
        state = {
            "active": True,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "triggered_by": triggered_by,
        }
        self._in_memory_state = state
        client = await self._get_client()
        if client:
            try:
                await client.set(REDIS_KILL_SWITCH_KEY, json.dumps(state))
            except Exception as e:
                logger.error(f"Failed to persist kill switch activation to Redis: {e}")
        logger.critical(f"EMERGENCY KILL SWITCH ACTIVATED by {triggered_by}: {reason}")
        return state

    async def deactivate(self, actor: str = "user") -> Dict[str, Any]:
        """Deactivate emergency stop, restoring normal system operations."""
        state = {
            "active": False,
            "activated_at": None,
            "reason": None,
            "triggered_by": None,
            "resumed_by": actor,
            "resumed_at": datetime.now(timezone.utc).isoformat(),
        }
        self._in_memory_state = state
        client = await self._get_client()
        if client:
            try:
                await client.set(REDIS_KILL_SWITCH_KEY, json.dumps(state))
            except Exception as e:
                logger.error(f"Failed to persist kill switch deactivation to Redis: {e}")
        logger.info(f"EMERGENCY KILL SWITCH DEACTIVATED by {actor}. System resumed.")
        return state


emergency_kill_switch = EmergencyKillSwitch()


def get_kill_switch() -> EmergencyKillSwitch:
    """Retrieve singleton instance of EmergencyKillSwitch."""
    return emergency_kill_switch

