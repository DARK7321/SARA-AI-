"""Integration tests for Mobile Automation Companion API."""
import pytest
from packages.core.security.auth import create_access_token


@pytest.mark.asyncio
async def test_mobile_api_flows(test_client, test_user):
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test SMS Webhook Ingestion with OTP
    sms_payload = {
        "event_type": "sms_received",
        "sender": "HDFC-BANK",
        "text": "Your secret OTP for transaction is 849201. Do not share.",
    }
    sms_res = await test_client.post("/v1/mobile/webhook", json=sms_payload)
    assert sms_res.status_code == 200
    sms_data = sms_res.json()["data"]
    assert sms_data["received"] is True
    assert sms_data["notification_created"] is True

    # 2. Test Battery Alert Webhook Ingestion
    batt_payload = {
        "event_type": "battery_alert",
        "battery_level": 8,
    }
    batt_res = await test_client.post("/v1/mobile/webhook", json=batt_payload)
    assert batt_res.status_code == 200
    assert batt_res.json()["data"]["notification_created"] is True

    # 3. Test Mobile Summary Endpoint
    summary_res = await test_client.get("/v1/mobile/summary")
    assert summary_res.status_code == 200
    summary_data = summary_res.json()["data"]
    assert summary_data["system_status"] == "ONLINE"
    assert summary_data["unread_notifications"] >= 1

    # 4. Test Mobile Quick Action
    qa_res = await test_client.post(
        "/v1/mobile/quick-action",
        json={"action": "morning_briefing"},
    )
    assert qa_res.status_code == 200
    assert "briefing_generated" in qa_res.json()["data"]

