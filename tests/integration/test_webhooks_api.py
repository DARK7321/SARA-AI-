"""Integration tests for Inbound Webhooks API."""
import pytest
from packages.core.security.auth import create_access_token


@pytest.mark.asyncio
async def test_webhooks_api_ingestion_and_events(test_client, test_user):
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Post external GitHub webhook
    webhook_payload = {
        "action": "opened",
        "issue": {
            "number": 42,
            "title": "Webhook Triggered Bug",
            "body": "Reported via external webhook",
        },
    }
    wh_res = await test_client.post(
        "/v1/webhooks/github",
        json=webhook_payload,
    )
    assert wh_res.status_code == 200
    wh_data = wh_res.json()["data"]
    assert wh_data["received"] is True
    assert wh_data["source"] == "github"
    assert wh_data["event_id"] is not None

    # 2. List recent events via authenticated endpoint
    events_res = await test_client.get("/v1/webhooks/events", headers=headers)
    assert events_res.status_code == 200
    events_data = events_res.json()["data"]
    assert events_data["total_count"] >= 1

    # 3. Get webhooks setup info
    info_res = await test_client.get("/v1/webhooks/info", headers=headers)
    assert info_res.status_code == 200
    info_data = info_res.json()["data"]
    assert "endpoints" in info_data
    assert "github" in info_data["endpoints"]
    assert "mobile" in info_data["endpoints"]

