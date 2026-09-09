"""Integration test for Conversational Chat and Task Execution endpoint (/v1/chat)."""
import pytest


@pytest.mark.asyncio
async def test_chat_conversational_turn(test_client):
    # 1. Login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Conversational Q&A (FAST path)
    chat_res = await test_client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "Hello! Who are you and how can you help me today?"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]
    assert data["path"] == "FAST"
    assert data["reply"] is not None
    assert len(data["reply"]) > 5


@pytest.mark.asyncio
async def test_chat_task_execution_command(test_client):
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Actionable Command (SMART path: plans DAG, executes steps, produces 5-point report)
    cmd_res = await test_client.post(
        "/v1/chat",
        headers=headers,
        json={
            "message": "Search my inbox for meeting emails and list today's calendar events",
            "include_audio": False,
        },
    )
    assert cmd_res.status_code == 200
    data = cmd_res.json()["data"]
    assert data["task_id"] is not None
    assert data["report"] is not None
    assert data["report"]["status"] == "COMPLETED"
    assert len(data["report"]["what_was_done"]) >= 1
    assert data["reply"] is not None

