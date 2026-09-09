"""Integration test for Friday Chat Delegation to Multi-Agent Frameworks."""
import pytest
from packages.core.security.auth import create_access_token


@pytest.mark.asyncio
async def test_chat_delegation_to_crewai(test_client, test_user, monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await test_client.post(
        "/v1/chat",
        json={"message": "Friday please use CrewAI to conduct research on database sharding"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["path"] == "DELEGATED"
    assert data["task_id"] == "fw-crewai"
    assert "CREWAI" in data["reply"]
    assert data["report"] is not None
    assert data["report"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_chat_delegation_to_autogen(test_client, test_user, monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await test_client.post(
        "/v1/chat",
        json={"message": "AutoGen debate team evaluate synchronous vs asynchronous RPC"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["path"] == "DELEGATED"
    assert data["task_id"] == "fw-autogen"
    assert "AUTOGEN" in data["reply"]
    assert data["report"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_chat_delegation_to_langgraph(test_client, test_user, monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await test_client.post(
        "/v1/chat",
        json={"message": "LangGraph state graph pipeline process new sales reports"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["path"] == "DELEGATED"
    assert data["task_id"] == "fw-langgraph"
    assert "LANGGRAPH" in data["reply"]
    assert data["report"]["status"] == "COMPLETED"

