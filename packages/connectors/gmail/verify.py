"""Gmail Post-condition Verification logic."""
from typing import Any, Dict
from packages.connectors.gmail.actions import GmailActions


class GmailVerifier:
    """Verifies that an action had the expected outcome in Gmail."""

    def __init__(self, actions: GmailActions):
        self.actions = actions

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        if not hints:
            return True

        check_type = hints.get("check")

        if check_type == "draft_created":
            draft_id = hints.get("draft_id")
            return draft_id in self.actions.sandbox.drafts

        if check_type == "message_sent":
            sent_id = hints.get("sent_id")
            return sent_id in self.actions.sandbox.sent

        return True

