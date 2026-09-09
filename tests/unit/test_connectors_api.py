import pytest
from sqlalchemy import select
from packages.core.db.models import Connection


@pytest.mark.asyncio
async def test_connectors_listing_and_health(test_client):
    # 1. Login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List connectors
    res = await test_client.get("/v1/connectors", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "connectors" in data
    assert len(data["connectors"]) == 4

    connector_ids = [c["connector_id"] for c in data["connectors"]]
    assert "connector-gmail" in connector_ids
    assert "connector-gdrive" in connector_ids
    assert "connector-gcal" in connector_ids
    assert "connector-gsheets" in connector_ids


@pytest.mark.asyncio
async def test_google_auth_url_and_callback(test_client, db_session):
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get Auth URL
    auth_url_res = await test_client.get("/v1/connectors/google/auth-url", headers=headers)
    assert auth_url_res.status_code == 200
    auth_data = auth_url_res.json()["data"]
    assert "accounts.google.com" in auth_data["auth_url"]
    assert "state" in auth_data

    # Callback exchange
    callback_res = await test_client.post(
        "/v1/connectors/google/callback",
        headers=headers,
        json={"code": "mock-code-12345", "state": auth_data["state"]},
    )
    assert callback_res.status_code == 200
    assert callback_res.json()["data"]["status"] == "connected"

    # Verify connection was saved in database
    conn_result = await db_session.execute(
        select(Connection).where(
            Connection.provider == "google",
            Connection.account_email == "owner@gmail.com",
        )
    )
    conn = conn_result.scalars().first()
    assert conn is not None
    assert conn.status == "ONLINE"
    assert conn.access_token_encrypted is not None


@pytest.mark.asyncio
async def test_health_center_reports_connectors(test_client):
    res = await test_client.get("/v1/health/center")
    assert res.status_code == 200
    data = res.json()["data"]
    components = data["components"]
    assert "connectors" in components
    assert components["connectors"]["gmail"]["status"] == "ONLINE"
    assert components["connectors"]["gsheets"]["status"] == "ONLINE"

