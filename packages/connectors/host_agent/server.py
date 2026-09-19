"""Local Windows host agent for safe, allowlisted desktop actions."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

try:
    import pyautogui
except ImportError:  # pragma: no cover - exercised on hosts without GUI dependencies
    pyautogui = None

app = FastAPI(title="OmniBrain Windows Host Agent", version="1.0.0")
JWT_SECRET = os.environ.get("OMNIBRAIN_HOST_JWT_SECRET", "OMNIBRAIN_HOST_JWT_SECRET_DEV_KEY")
JWT_ALGORITHM = "HS256"

# Keep app launching constrained to well-known, non-admin desktop applications.
ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
}

ALLOWED_ROOTS = tuple(
    Path(path).expanduser().resolve()
    for path in os.environ.get(
        "OMNIBRAIN_HOST_ALLOWED_ROOTS",
        "~/Desktop;~/Documents;~/Downloads",
    ).split(";")
    if path.strip()
)


class ActionRequest(BaseModel):
    request_id: str
    task_id: str
    step_id: str
    idempotency_key: str
    approval_id: Optional[str] = None
    action: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, str]] = None


def _authenticate(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        return jwt.decode(
            authorization[7:],
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience="host-agent",
            issuer="omnibrain-api",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid host-agent token") from exc


def _require_gui_backend() -> None:
    if pyautogui is None:
        raise RuntimeError("pyautogui is not installed; install project requirements first")


def _safe_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser().resolve()
    if not any(candidate == root or root in candidate.parents for root in ALLOWED_ROOTS):
        raise ValueError("Path is outside the host-agent allowed folders")
    return candidate


def _run_action(action: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    capability = action.get("capability")
    if capability == "host.open_app":
        app_name = str(action.get("app", "")).lower().strip()
        executable = ALLOWED_APPS.get(app_name)
        if executable is None:
            raise ValueError(f"Application is not allowlisted: {app_name}")
        if dry_run:
            return {"simulated": True, "capability": capability, "app": app_name}
        subprocess.Popen([executable], shell=False)
        return {"capability": capability, "app": app_name, "launched": True}

    if capability == "host.move_mouse":
        x, y = int(action["x"]), int(action["y"])
        if x < 0 or y < 0:
            raise ValueError("Mouse coordinates must be non-negative")
        if dry_run:
            return {"simulated": True, "capability": capability, "x": x, "y": y}
        _require_gui_backend()
        pyautogui.moveTo(x, y, duration=0.15)
        return {"capability": capability, "x": x, "y": y}

    if capability == "host.click":
        button = str(action.get("button", "left")).lower()
        clicks = int(action.get("clicks", 1))
        if button not in {"left", "right", "middle"} or clicks not in {1, 2}:
            raise ValueError("Only left, right, or middle single/double clicks are supported")
        if dry_run:
            return {"simulated": True, "capability": capability, "button": button, "clicks": clicks}
        _require_gui_backend()
        pyautogui.click(button=button, clicks=clicks, interval=0.1)
        return {"capability": capability, "button": button, "clicks": clicks}

    if capability == "host.type_text":
        text = str(action.get("text", ""))
        if not text or len(text) > 4000:
            raise ValueError("Text must contain 1 to 4000 characters")
        if dry_run:
            return {"simulated": True, "capability": capability, "text_length": len(text)}
        _require_gui_backend()
        pyautogui.write(text, interval=0.01)
        return {"capability": capability, "typed": True, "text_length": len(text)}

    if capability == "host.hotkey":
        keys = action.get("keys")
        if not isinstance(keys, list) or not keys or len(keys) > 4 or not all(isinstance(k, str) for k in keys):
            raise ValueError("keys must be a list of 1 to 4 key names")
        if dry_run:
            return {"simulated": True, "capability": capability, "keys": keys}
        _require_gui_backend()
        pyautogui.hotkey(*keys)
        return {"capability": capability, "keys": keys}

    if capability == "host.press_key":
        key = str(action.get("key", "")).lower().strip()
        allowed_keys = {"enter", "esc", "tab", "backspace", "delete", "space", "up", "down", "left", "right", "home", "end"}
        if not (len(key) == 1 or key in allowed_keys):
            raise ValueError("Unsupported key")
        if dry_run:
            return {"simulated": True, "capability": capability, "key": key}
        _require_gui_backend()
        pyautogui.press(key)
        return {"capability": capability, "key": key}

    if capability == "host.scroll":
        amount = int(action.get("amount", 0))
        if not -20 <= amount <= 20 or amount == 0:
            raise ValueError("Scroll amount must be between -20 and 20, excluding zero")
        if dry_run:
            return {"simulated": True, "capability": capability, "amount": amount}
        _require_gui_backend()
        pyautogui.scroll(amount)
        return {"capability": capability, "amount": amount}

    if capability == "host.drag_mouse":
        start = (int(action["start_x"]), int(action["start_y"]))
        end = (int(action["end_x"]), int(action["end_y"]))
        if min(*start, *end) < 0:
            raise ValueError("Mouse coordinates must be non-negative")
        if dry_run:
            return {"simulated": True, "capability": capability, "start": start, "end": end}
        _require_gui_backend()
        pyautogui.moveTo(*start)
        pyautogui.dragTo(*end, duration=0.25, button=str(action.get("button", "left")))
        return {"capability": capability, "start": start, "end": end}

    if capability == "host.file_op":
        operation = str(action.get("action", "")).lower()
        target = _safe_path(str(action.get("path", "")))
        if operation == "list":
            if not target.is_dir():
                raise ValueError("Target is not a directory")
            entries = [{"name": item.name, "is_dir": item.is_dir()} for item in target.iterdir()]
            return {"capability": capability, "action": operation, "path": str(target), "entries": entries}
        if operation == "read":
            if not target.is_file() or target.stat().st_size > 1_000_000:
                raise ValueError("Only files up to 1 MB can be read")
            return {"capability": capability, "action": operation, "path": str(target), "content": target.read_text(encoding="utf-8")}
        if operation in {"write", "create"}:
            content = str(action.get("content", ""))
            if len(content) > 1_000_000:
                raise ValueError("File content exceeds 1 MB")
            if dry_run:
                return {"simulated": True, "capability": capability, "action": operation, "path": str(target)}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"capability": capability, "action": operation, "path": str(target), "written": True}
        if operation == "delete":
            if dry_run:
                return {"simulated": True, "capability": capability, "action": operation, "path": str(target)}
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
            return {"capability": capability, "action": operation, "path": str(target), "deleted": True}
        raise ValueError("Unsupported file operation")

    if capability == "host.active_window":
        if dry_run:
            return {"simulated": True, "capability": capability}
        try:
            import pygetwindow
            window = pygetwindow.getActiveWindow()
            return {"capability": capability, "title": window.title if window else None}
        except Exception as exc:
            raise RuntimeError(f"Active-window inspection unavailable: {exc}") from exc

    if capability == "host.read_screen":
        if dry_run:
            return {"simulated": True, "capability": capability}
        _require_gui_backend()
        image = pyautogui.screenshot()
        output_dir = os.path.join(os.path.expanduser("~"), ".omnibrain", "screenshots")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{action.get('request_id', 'screen')}.png")
        image.save(output_path)
        return {"capability": capability, "screenshot_path": output_path, "width": image.width, "height": image.height}

    raise ValueError(f"Unsupported host capability: {capability}")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "omnibrain-host-agent"}


@app.post("/actions", response_model=ActionResponse)
def execute_action(request: ActionRequest, _: Dict[str, Any] = Depends(_authenticate)) -> ActionResponse:
    try:
        data = _run_action(request.action, dry_run=bool(request.action.get("dry_run", False)))
        return ActionResponse(success=True, data=data)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        return ActionResponse(success=False, error={"class": "POLICY_DENIED", "message": str(exc)})
