import pytest


@pytest.mark.asyncio
async def test_auth_login_success(test_client):
    response = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    assert response.status_code == 200
    res = response.json()
    assert res["ok"] is True
    assert "access_token" in res["data"]
    assert "refresh_token" in res["data"]
    assert res["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_auth_login_invalid_password(test_client):
    response = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "WrongPassword"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_auth_me_authenticated(test_client):
    # First login
    login_res = await test_client.post(
        "/v1/auth/login",
        data={"username": "admin@omnibrain.local", "password": "OmniBrain@2026"},
    )
    token = login_res.json()["data"]["access_token"]

    # Request /me
    me_res = await test_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["ok"] is True
    assert data["data"]["email"] in ("admin@omnibrain.local", "vikas635026@gmail.com")
    assert data["data"]["role"] == "owner"


@pytest.mark.asyncio
async def test_auth_me_unauthorized(test_client):
    response = await test_client.get("/v1/auth/me")
    assert response.status_code == 401

