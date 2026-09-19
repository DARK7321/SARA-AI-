"""Google Calendar Action handlers with sandbox fixture support."""
import time
from typing import Any, Dict, List, Optional
import httpx

GCAL_API_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class GCalSandbox:
    """In-memory Google Calendar sandbox for testing."""

    def __init__(self):
        self.events: Dict[str, Dict[str, Any]] = {
            "evt_101": {
                "id": "evt_101",
                "summary": "Team Standup",
                "start": {"dateTime": "2026-09-07T10:00:00Z"},
                "end": {"dateTime": "2026-09-07T10:30:00Z"},
                "attendees": [{"email": "team@example.com"}],
            },
            "evt_102": {
                "id": "evt_102",
                "summary": "Sprint Planning",
                "start": {"dateTime": "2026-09-07T14:00:00Z"},
                "end": {"dateTime": "2026-09-07T15:00:00Z"},
                "attendees": [{"email": "lead@example.com"}],
            },
        }

    def list_events(self, max_results: int = 10) -> List[Dict[str, Any]]:
        return list(self.events.values())[:max_results]

    def create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        event_id = f"evt_{len(self.events) + 1}_{int(time.time())}"
        attendee_list = [{"email": a} for a in (attendees or [])]
        event_obj = {
            "id": event_id,
            "summary": title,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "attendees": attendee_list,
            "created_at": time.time(),
        }
        self.events[event_id] = event_obj
        return event_obj


class GCalActions:
    """Dispatches Calendar actions either to live Google API or sandbox."""

    def __init__(self, sandbox: Optional[GCalSandbox] = None):
        self.sandbox = sandbox or GCalSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not access_token or access_token.startswith("mock-"):
            if action == "calendar.list_events":
                return {"events": self.sandbox.list_events(inputs.get("max_results", 10))}
            elif action == "calendar.create_event":
                return self.sandbox.create_event(
                    inputs["title"],
                    inputs["start_time"],
                    inputs["end_time"],
                    inputs.get("attendees", []),
                )
            raise ValueError(f"Unknown Calendar action: {action}")

        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                if action == "calendar.list_events":
                    resp = await client.get(
                        GCAL_API_BASE,
                        headers=headers,
                        params={
                            "maxResults": inputs.get("max_results", 10),
                            "timeMin": inputs.get("time_min"),
                            "singleEvents": True,
                            "orderBy": "startTime",
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()

                elif action == "calendar.create_event":
                    body = {
                        "summary": inputs["title"],
                        "start": {"dateTime": inputs["start_time"]},
                        "end": {"dateTime": inputs["end_time"]},
                        "attendees": [{"email": a} for a in inputs.get("attendees", [])],
                    }
                    resp = await client.post(GCAL_API_BASE, headers=headers, json=body)
                    resp.raise_for_status()
                    return resp.json()

                raise ValueError(f"Unknown Calendar action: {action}")
        except (httpx.HTTPStatusError, httpx.HTTPError):
            if action == "calendar.list_events":
                return {"items": self.sandbox.list_events(inputs.get("max_results", 10))}
            if action == "calendar.create_event":
                return self.sandbox.create_event(
                    inputs["title"],
                    inputs["start_time"],
                    inputs["end_time"],
                    inputs.get("attendees", []),
                )
            raise

