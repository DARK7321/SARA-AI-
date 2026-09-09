"""Unit and integration tests for Emergency Kill Switch and Safety Telemetry."""
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.deps import get_current_user
from packages.core.safety.kill_switch import EmergencyKillSwitch, emergency_kill_switch


@pytest.mark.asyncio
async def test_kill_switch_lifecycle():
    """Test kill switch activation, status inspection, and deactivation."""
    ks = EmergencyKillSwitch()

    # Initial state should be inactive
    assert await ks.is_active() is False
    status = await ks.get_status()
    assert status["active"] is False

    # Activate
    res_activate = await ks.activate(reason="Test drill", triggered_by="tester@example.com")
    assert res_activate["active"] is True
    assert await ks.is_active() is True
    assert (await ks.get_status())["reason"] == "Test drill"

    # Deactivate
    res_deactivate = await ks.deactivate(actor="tester@example.com")
    assert res_deactivate["active"] is False
    assert await ks.is_active() is False


@pytest.mark.asyncio
async def test_kill_switch_api(db_session, test_user):
    """Test /v1/safety/kill-switch and /v1/safety/status endpoints."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Trigger kill switch
        post_res = await ac.post("/v1/safety/kill-switch", json={"active": True, "reason": "Security Alert"})
        assert post_res.status_code == 200
        assert post_res.json()["data"]["active"] is True

        # Check status
        status_res = await ac.get("/v1/safety/status")
        assert status_res.status_code == 200
        data = status_res.json()["data"]
        assert data["kill_switch"]["active"] is True
        assert "circuit_breakers" in data
        assert "autonomy_level" in data

        # Resume / Deactivate
        resume_res = await ac.post("/v1/safety/kill-switch", json={"active": False})
        assert resume_res.status_code == 200
        assert resume_res.json()["data"]["active"] is False

    app.dependency_overrides.clear()

