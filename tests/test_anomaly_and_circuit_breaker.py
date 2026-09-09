"""Unit and integration tests for Anomaly Detection and Circuit Breakers."""
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.deps import get_current_user
from packages.core.safety.anomaly import AnomalyDetector, CircuitBreakerState


@pytest.mark.asyncio
async def test_circuit_breaker_tripping_on_consecutive_failures():
    """Test that reaching consecutive failure threshold trips breaker to OPEN."""
    detector = AnomalyDetector(consecutive_failure_threshold=3, cooldown_seconds=60)
    connector = "test_conn"

    # Initially closed and available
    assert await detector.is_available(connector) is True

    # 1st failure
    await detector.record_execution(connector, success=False, error="Timeout 1")
    assert await detector.is_available(connector) is True

    # 2nd failure
    await detector.record_execution(connector, success=False, error="Timeout 2")
    assert await detector.is_available(connector) is True

    # 3rd failure -> trips breaker to OPEN!
    res = await detector.record_execution(connector, success=False, error="Timeout 3")
    assert res["state"] == CircuitBreakerState.OPEN.value
    assert await detector.is_available(connector) is False

    # Manual reset returns to CLOSED
    await detector.reset(connector)
    assert await detector.is_available(connector) is True
    status = await detector.get_status(connector)
    assert status["state"] == CircuitBreakerState.CLOSED.value


@pytest.mark.asyncio
async def test_circuit_breaker_reset_api(db_session, test_user):
    """Test POST /v1/safety/circuit-breaker/reset endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/safety/circuit-breaker/reset", json={"connector": "gmail"})
        assert res.status_code == 200
        assert "reset_connectors" in res.json()["data"]

    app.dependency_overrides.clear()

