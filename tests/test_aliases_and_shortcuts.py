"""Unit and integration tests for Natural Language Aliases and Fast-Path Chat Trigger."""
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.api.deps import get_current_user


@pytest.mark.asyncio
async def test_aliases_api_crud(db_session, test_user):
    """Test GET, POST, and DELETE /v1/aliases."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. List aliases (includes defaults)
        list_res = await ac.get("/v1/aliases")
        assert list_res.status_code == 200
        data = list_res.json()["data"]
        alias_names = [a["name"] for a in data["aliases"]]
        assert "morning" in alias_names
        assert "triage" in alias_names

        # 2. Create custom alias
        create_res = await ac.post(
            "/v1/aliases",
            json={
                "name": "daily-standup",
                "target_type": "workflow",
                "target_id": "Morning Briefing",
                "parameters": {"channel": "#general"},
            },
        )
        assert create_res.status_code == 200
        created_id = create_res.json()["data"]["id"]

        # 3. Verify it appears in list
        list_res2 = await ac.get("/v1/aliases")
        names2 = [a["name"] for a in list_res2.json()["data"]["aliases"]]
        assert "daily-standup" in names2

        # 4. Delete custom alias
        del_res = await ac.delete(f"/v1/aliases/{created_id}")
        assert del_res.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_triggers_workflow_via_alias(db_session, test_user):
    """Test that sending 'morning' in chat executes Morning Briefing via fast-path alias."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/v1/chat",
            json={"message": "morning", "include_audio": False},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["path"] == "FAST"
        assert "Morning" in data["reply"]
        assert data["report"] is not None
        assert data["report"]["status"] == "COMPLETED"

    app.dependency_overrides.clear()
