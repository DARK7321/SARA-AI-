"""Slack Action handlers with sandbox fixture support."""
import time
from typing import Any, Dict, List, Optional
import httpx

SLACK_API_BASE = "https://slack.com/api"


class SlackSandbox:
    """In-memory Slack sandbox for offline development and unit testing."""

    def __init__(self):
        self.channels: Dict[str, List[Dict[str, Any]]] = {
            "#general": [
                {
                    "id": "msg-101",
                    "user": "U12345",
                    "text": "Team standup at 10:00 AM IST today.",
                    "ts": "1725786000.000100",
                },
                {
                    "id": "msg-102",
                    "user": "U12346",
                    "text": "Please review the latest PR for OmniBrain v2.",
                    "ts": "1725789600.000200",
                },
            ],
            "#dev-team": [
                {
                    "id": "msg-201",
                    "user": "U12347",
                    "text": "CI pipeline is green on main branch.",
                    "ts": "1725793200.000300",
                }
            ],
            "#alerts": [],
        }

    def post_message(
        self,
        channel: str = "#general",
        text: str = "",
        blocks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        ch_key = channel if channel.startswith("#") else f"#{channel}"
        channel_msgs = self.channels.setdefault(ch_key, [])
        ts = f"{time.time():.6f}"
        msg_obj = {
            "id": f"msg-{int(time.time() * 1000)}",
            "user": "U_BOT_OMNIBRAIN",
            "text": text,
            "blocks": blocks or [],
            "ts": ts,
        }
        channel_msgs.append(msg_obj)
        return {
            "ok": True,
            "channel": ch_key,
            "ts": ts,
            "message": msg_obj,
        }

    def read_channel(self, channel: str = "#general", limit: int = 10) -> List[Dict[str, Any]]:
        ch_key = channel if channel.startswith("#") else f"#{channel}"
        messages = self.channels.get(ch_key, [])
        return messages[-limit:]

    def list_channels(self) -> List[Dict[str, Any]]:
        return [
            {"id": ch, "name": ch.lstrip("#"), "is_channel": True}
            for ch in self.channels.keys()
        ]


class SlackActions:
    """Dispatches Slack actions to live API or sandbox."""

    def __init__(self, sandbox: Optional[SlackSandbox] = None):
        self.sandbox = sandbox or SlackSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Any:
        # Offline sandbox fallback
        if not access_token or access_token.startswith("mock-"):
            if action == "slack.post_message":
                return self.sandbox.post_message(
                    channel=inputs.get("channel", "#general"),
                    text=inputs.get("text", ""),
                    blocks=inputs.get("blocks"),
                )
            elif action == "slack.read_channel":
                return self.sandbox.read_channel(
                    channel=inputs.get("channel", "#general"),
                    limit=inputs.get("limit", 10),
                )
            elif action == "slack.list_channels":
                return self.sandbox.list_channels()
            else:
                raise ValueError(f"Unsupported Slack action: {action}")

        # Live Slack Web API execution
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            if action == "slack.post_message":
                payload = {
                    "channel": inputs.get("channel", "#general"),
                    "text": inputs.get("text", ""),
                }
                if "blocks" in inputs:
                    payload["blocks"] = inputs["blocks"]
                resp = await client.post(
                    f"{SLACK_API_BASE}/chat.postMessage",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()

            elif action == "slack.read_channel":
                channel = inputs.get("channel", "")
                limit = inputs.get("limit", 10)
                resp = await client.get(
                    f"{SLACK_API_BASE}/conversations.history?channel={channel}&limit={limit}",
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()

            elif action == "slack.list_channels":
                resp = await client.get(
                    f"{SLACK_API_BASE}/conversations.list",
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()

            else:
                raise ValueError(f"Unsupported Slack action: {action}")

