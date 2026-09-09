"""Unit and integration tests for Progressive Autonomy Levels 0 to 4."""
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.deps import get_current_user
from packages.connectors._sdk.contract import SideEffectType
from packages.core.policy.engine import PolicyEngine, PolicyEffect
from packages.core.db.models import User


def test_autonomy_level_0_strict_manual():
    """Autonomy Level 0 requires explicit confirmation for every single action."""
    engine = PolicyEngine()
    # Even a read action requires confirmation at Level 0
    res_read = engine.evaluate(action="gmail.read_email", side_effect=SideEffectType.READ, autonomy_level=0)
    assert res_read.effect == PolicyEffect.CONFIRM
    assert "Level 0" in res_read.reason

    # Write action requires confirmation
    res_write = engine.evaluate(action="notes.create", side_effect=SideEffectType.WRITE, autonomy_level=0)
    assert res_write.effect == PolicyEffect.CONFIRM


def test_autonomy_level_1_assisted():
    """Autonomy Level 1 allows read actions, but requires confirmation for all mutations."""
    engine = PolicyEngine()
    # Read allowed
    res_read = engine.evaluate(action="gmail.read_email", side_effect=SideEffectType.READ, autonomy_level=1)
    assert res_read.effect == PolicyEffect.ALLOW

    # Mutations require confirmation
    res_write = engine.evaluate(action="gsheets.append", side_effect=SideEffectType.WRITE, autonomy_level=1)
    assert res_write.effect == PolicyEffect.CONFIRM
    assert "Level 1" in res_write.reason


def test_autonomy_level_2_balanced():
    """Autonomy Level 2 allows safe writes, but confirms external sends and destructive operations."""
    engine = PolicyEngine()
    # Safe write allowed
    res_write = engine.evaluate(action="notes.create", side_effect=SideEffectType.WRITE, risk_level="LOW", autonomy_level=2)
    assert res_write.effect == PolicyEffect.ALLOW

    # External send confirms
    res_send = engine.evaluate(action="gmail.send_email", side_effect=SideEffectType.EXTERNAL_SEND, autonomy_level=2)
    assert res_send.effect == PolicyEffect.CONFIRM

    # Destructive confirms
    res_delete = engine.evaluate(action="gdrive.delete_file", side_effect=SideEffectType.DESTRUCTIVE, autonomy_level=2)
    assert res_delete.effect == PolicyEffect.CONFIRM


def test_autonomy_level_3_auto_low_risk():
    """Autonomy Level 3 allows safe writes and routine external sends; confirms only destructive or critical."""
    engine = PolicyEngine()
    # Safe write allowed
    res_write = engine.evaluate(action="notes.create", side_effect=SideEffectType.WRITE, autonomy_level=3)
    assert res_write.effect == PolicyEffect.ALLOW

    # Routine external send allowed
    res_send = engine.evaluate(action="slack.post_message", side_effect=SideEffectType.EXTERNAL_SEND, risk_level="LOW", autonomy_level=3)
    assert res_send.effect == PolicyEffect.ALLOW

    # Destructive confirms
    res_delete = engine.evaluate(action="gdrive.delete_file", side_effect=SideEffectType.DESTRUCTIVE, autonomy_level=3)
    assert res_delete.effect == PolicyEffect.CONFIRM


def test_autonomy_level_4_full_autonomous():
    """Autonomy Level 4 allows all verified operations."""
    engine = PolicyEngine()
    res_delete = engine.evaluate(action="gdrive.delete_file", side_effect=SideEffectType.DESTRUCTIVE, autonomy_level=4)
    assert res_delete.effect == PolicyEffect.ALLOW


def test_kill_switch_overrides_autonomy_level():
    """Kill switch overrides any autonomy level and strictly DENIES execution."""
    engine = PolicyEngine()
    # Even at Level 4 and a pure read action, kill switch active forces DENY
    res = engine.evaluate(
        action="gmail.read_email",
        side_effect=SideEffectType.READ,
        autonomy_level=4,
        kill_switch_active=True,
    )
    assert res.effect == PolicyEffect.DENY
    assert "EMERGENCY KILL SWITCH" in res.reason


@pytest.mark.asyncio
async def test_autonomy_api_endpoints(db_session, test_user):
    """Test GET and POST /v1/policies/autonomy."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Get autonomy settings
        get_res = await ac.get("/v1/policies/autonomy")
        assert get_res.status_code == 200
        data = get_res.json()["data"]
        assert "current_level" in data
        assert "tiers" in data

        # Update to Level 3
        post_res = await ac.post("/v1/policies/autonomy", json={"autonomy_level": 3})
        assert post_res.status_code == 200
        post_data = post_res.json()["data"]
        assert post_data["updated_level"] == 3

    app.dependency_overrides.clear()

