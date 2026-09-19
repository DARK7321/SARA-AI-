import time

import jwt
import pytest
from fastapi.testclient import TestClient

from packages.connectors.host_agent.server import JWT_SECRET, app


def _headers():
    token = jwt.encode(
        {
            "aud": "host-agent",
            "iss": "omnibrain-api",
            "exp": int(time.time()) + 60,
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_host_agent_health_and_authentication():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.post("/actions", json={"action": {}}).status_code == 401


@pytest.mark.parametrize(
    "action",
    [
        {"capability": "host.open_app", "app": "notepad"},
        {"capability": "host.move_mouse", "x": 100, "y": 200},
        {"capability": "host.click", "button": "left", "clicks": 1},
        {"capability": "host.type_text", "text": "hello"},
        {"capability": "host.hotkey", "keys": ["ctrl", "l"]},
        {"capability": "host.press_key", "key": "enter"},
        {"capability": "host.scroll", "amount": 3},
        {"capability": "host.drag_mouse", "start_x": 10, "start_y": 10, "end_x": 20, "end_y": 20},
        {"capability": "host.active_window"},
        {"capability": "host.read_screen"},
    ],
)
def test_host_actions_support_dry_run_without_touching_desktop(action):
    payload = {
        "request_id": "req-test",
        "task_id": "task-test",
        "step_id": "step-test",
        "idempotency_key": "idem-test",
        "action": {**action, "dry_run": True},
    }
    with TestClient(app) as client:
        response = client.post("/actions", json=payload, headers=_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["simulated"] is True


def test_host_agent_rejects_unknown_app_in_dry_run():
    payload = {
        "request_id": "req-test",
        "task_id": "task-test",
        "step_id": "step-test",
        "idempotency_key": "idem-test",
        "action": {"capability": "host.open_app", "app": "powershell", "dry_run": True},
    }
    with TestClient(app) as client:
        response = client.post("/actions", json=payload, headers=_headers())

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "allowlisted" in response.json()["error"]["message"]


def test_host_agent_rejects_file_outside_allowed_roots():
    payload = {
        "request_id": "req-test",
        "task_id": "task-test",
        "step_id": "step-test",
        "idempotency_key": "idem-test",
        "action": {
            "capability": "host.file_op",
            "action": "read",
            "path": "C:/Windows/win.ini",
            "dry_run": True,
        },
    }
    with TestClient(app) as client:
        response = client.post("/actions", json=payload, headers=_headers())

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "allowed folders" in response.json()["error"]["message"]