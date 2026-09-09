"""Google Calendar Post-condition Verification logic."""
from typing import Any, Dict
from packages.connectors.gcal.actions import GCalActions


class GCalVerifier:
    """Verifies event creation on Google Calendar."""

    def __init__(self, actions: GCalActions):
        self.actions = actions

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        if not hints:
            return True

        if hints.get("check") == "event_exists":
            event_id = hints.get("event_id")
            return event_id in self.actions.sandbox.events

        return True

