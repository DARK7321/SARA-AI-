import pytest

@pytest.mark.asyncio
async def test_root_endpoint(test_client):
    response = await test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["message"] == "Welcome to OmniBrain"

@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    response = await test_client.get("/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_center(test_client):
    response = await test_client.get("/v1/health/center")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "components" in data["data"]
