"""Integration test for Notifications, Proactive triggers, and Vector Memory API."""
import pytest
from packages.core.security.auth import create_access_token


@pytest.mark.asyncio
async def test_proactive_api_flow(test_client, test_user):
    """Test triggering proactive cycle, fetching notifications, and marking as read."""
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger proactive scan
    trigger_res = await test_client.post(
        "/v1/proactive/trigger",
        json={"force_briefing": True, "include_audio": False},
        headers=headers,
    )
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.json()["data"]
    assert trigger_data["generated_count"] >= 1
    notif_id = trigger_data["notifications"][0]["id"]

    # 2. List notifications
    list_res = await test_client.get("/v1/notifications", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()["data"]
    assert len(list_data["notifications"]) >= 1
    assert list_data["unread_count"] >= 1

    # 3. Mark notification as read
    read_res = await test_client.post(
        f"/v1/notifications/{notif_id}/read",
        headers=headers,
    )
    assert read_res.status_code == 200
    assert read_res.json()["data"]["status"] == "READ"

    # 4. List unread only
    unread_res = await test_client.get("/v1/notifications?unread_only=true", headers=headers)
    assert unread_res.status_code == 200
    unreads = unread_res.json()["data"]["notifications"]
    assert not any(n["id"] == notif_id for n in unreads)

    # 5. Store memory via API
    mem_create_res = await test_client.post(
        "/v1/memory",
        json={
            "content": "User prefers concise answers with bullet points",
            "category": "preference",
            "confidence": 0.9,
        },
        headers=headers,
    )
    assert mem_create_res.status_code == 200
    mem_data = mem_create_res.json()["data"]
    assert mem_data["category"] == "preference"

    # 6. Search memory via API
    mem_search_res = await test_client.get(
        "/v1/memory?query=bullet points answers",
        headers=headers,
    )
    assert mem_search_res.status_code == 200
    search_mems = mem_search_res.json()["data"]["memories"]
    assert len(search_mems) > 0
    assert any("bullet points" in m["content"] for m in search_mems)

