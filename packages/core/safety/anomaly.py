"""Anomaly Detection and Circuit Breaker Guard for OmniBrain.

Protects against cascading failures and runaway task errors by tracking rolling
error rates per connector and automatically tripping circuit breakers.
"""
from datetime import datetime, timezone
from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from apps.api.settings import get_settings

logger = logging.getLogger("omnibrain.safety.anomaly")

REDIS_CIRCUIT_PREFIX = "omnibrain:circuit_breaker:"
KNOWN_CONNECTORS = [
    "gmail",
    "gdrive",
    "gcal",
    "gsheets",
    "github",
    "slack",
    "browser",
    "mcp",
    "fake",
]


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"        # Normal healthy operation
    OPEN = "OPEN"            # Tripped: blocking all calls
    HALF_OPEN = "HALF_OPEN"  # Testing recovery with single requests


class AnomalyDetector:
    """Tracks error rates and manages circuit breaker lifecycle per connector."""

    def __init__(
        self,
        consecutive_failure_threshold: int = 3,
        failure_rate_threshold: float = 0.5,
        window_size: int = 10,
        cooldown_seconds: int = 60,
        redis_url: Optional[str] = None,
    ):
        self.threshold = consecutive_failure_threshold
        self.rate_threshold = failure_rate_threshold
        self.window_size = window_size
        self.cooldown_seconds = cooldown_seconds
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._in_memory_breakers: Dict[str, Dict[str, Any]] = {}

    async def _get_client(self) -> Optional[aioredis.Redis]:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                )
                await self._redis.ping()
            except Exception as e:
                logger.debug(f"Redis unavailable for circuit breaker ({e}), using memory fallback.")
                self._redis = None
        return self._redis

    def _default_breaker_data(self, name: str) -> Dict[str, Any]:
        return {
            "connector": name,
            "state": CircuitBreakerState.CLOSED.value,
            "consecutive_failures": 0,
            "recent_results": [],  # List of booleans (True=success, False=fail)
            "last_tripped_at": None,
            "last_error": None,
            "total_calls": 0,
            "total_failures": 0,
        }

    async def _get_breaker_data(self, connector: str) -> Dict[str, Any]:
        client = await self._get_client()
        if client:
            try:
                raw = await client.get(f"{REDIS_CIRCUIT_PREFIX}{connector}")
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Error reading breaker data from Redis: {e}")

        if connector not in self._in_memory_breakers:
            self._in_memory_breakers[connector] = self._default_breaker_data(connector)
        return self._in_memory_breakers[connector]

    async def _save_breaker_data(self, connector: str, data: Dict[str, Any]) -> None:
        self._in_memory_breakers[connector] = data
        client = await self._get_client()
        if client:
            try:
                await client.set(f"{REDIS_CIRCUIT_PREFIX}{connector}", json.dumps(data))
            except Exception as e:
                logger.warning(f"Error writing breaker data to Redis: {e}")

    async def is_available(self, connector: str) -> bool:
        """Check whether the given connector is currently allowed to execute."""
        data = await self._get_breaker_data(connector)
        state = data.get("state", CircuitBreakerState.CLOSED.value)

        if state == CircuitBreakerState.CLOSED.value:
            return True

        if state == CircuitBreakerState.OPEN.value:
            last_tripped_str = data.get("last_tripped_at")
            if last_tripped_str:
                last_tripped = datetime.fromisoformat(last_tripped_str)
                now = datetime.now(timezone.utc)
                elapsed = (now - last_tripped).total_seconds()
                if elapsed >= self.cooldown_seconds:
                    # Cooldown elapsed: transition to HALF_OPEN
                    data["state"] = CircuitBreakerState.HALF_OPEN.value
                    await self._save_breaker_data(connector, data)
                    logger.info(f"Circuit breaker for '{connector}' entered HALF_OPEN state.")
                    return True
            return False

        if state == CircuitBreakerState.HALF_OPEN.value:
            # Allow single probe request
            return True

        return True

    async def record_execution(
        self,
        connector: str,
        success: bool,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an execution result and evaluate circuit breaker thresholds."""
        data = await self._get_breaker_data(connector)
        data["total_calls"] = data.get("total_calls", 0) + 1

        recent = data.get("recent_results", [])
        recent.append(success)
        if len(recent) > self.window_size:
            recent.pop(0)
        data["recent_results"] = recent

        current_state = data.get("state", CircuitBreakerState.CLOSED.value)

        if success:
            data["consecutive_failures"] = 0
            if current_state == CircuitBreakerState.HALF_OPEN.value:
                data["state"] = CircuitBreakerState.CLOSED.value
                data["last_error"] = None
                logger.info(f"Circuit breaker for '{connector}' recovered to CLOSED.")
        else:
            data["total_failures"] = data.get("total_failures", 0) + 1
            data["consecutive_failures"] = data.get("consecutive_failures", 0) + 1
            data["last_error"] = error or "Unknown execution failure"

            # Check tripping conditions
            trip_due_to_consecutive = data["consecutive_failures"] >= self.threshold

            trip_due_to_rate = False
            if len(recent) >= 4:
                fail_rate = recent.count(False) / len(recent)
                if fail_rate >= self.rate_threshold:
                    trip_due_to_rate = True

            if trip_due_to_consecutive or trip_due_to_rate or current_state == CircuitBreakerState.HALF_OPEN.value:
                data["state"] = CircuitBreakerState.OPEN.value
                data["last_tripped_at"] = datetime.now(timezone.utc).isoformat()
                reason = "consecutive errors" if trip_due_to_consecutive else "high failure rate"
                logger.error(
                    f"CIRCUIT BREAKER TRIPPED to OPEN for connector '{connector}' due to {reason}! "
                    f"Consecutive errors: {data['consecutive_failures']}. Error: {error}"
                )

        await self._save_breaker_data(connector, data)
        return data

    async def reset(self, connector: Optional[str] = None) -> Dict[str, Any]:
        """Manually reset the circuit breaker for a specific connector or all."""
        connectors_to_reset = [connector] if connector else KNOWN_CONNECTORS
        results = {}
        for c in connectors_to_reset:
            data = self._default_breaker_data(c)
            await self._save_breaker_data(c, data)
            results[c] = data
            logger.info(f"Circuit breaker manually RESET for connector '{c}'.")
        return results

    async def get_status(self, connector: str) -> Dict[str, Any]:
        """Get status for a single connector."""
        return await self._get_breaker_data(connector)

    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all registered connectors and general health."""
        connectors_status = {}
        tripped_count = 0

        for c in KNOWN_CONNECTORS:
            status = await self._get_breaker_data(c)
            connectors_status[c] = status
            if status.get("state") == CircuitBreakerState.OPEN.value:
                tripped_count += 1

        return {
            "connectors": connectors_status,
            "tripped_count": tripped_count,
            "system_circuit_healthy": tripped_count == 0,
        }


anomaly_detector = AnomalyDetector()

