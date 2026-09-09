"""Google Drive Post-condition Verification logic."""
from typing import Any, Dict
from packages.connectors.gdrive.actions import GDriveActions


class GDriveVerifier:
    """Verifies file creation and metadata changes in Google Drive."""

    def __init__(self, actions: GDriveActions):
        self.actions = actions

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        if not hints:
            return True

        check_type = hints.get("check")

        if check_type == "file_exists":
            file_id = hints.get("file_id")
            return file_id in self.actions.sandbox.files

        if check_type == "file_shared":
            file_id = hints.get("file_id")
            email = hints.get("email")
            if file_id in self.actions.sandbox.files:
                shares = self.actions.sandbox.files[file_id].get("shared_with", [])
                return any(s.get("email") == email for s in shares)

        return True

