"""Google Sheets Post-condition Re-read Verification logic."""
from typing import Any, Dict
from packages.connectors.gsheets.actions import GSheetsActions


class GSheetsVerifier:
    """Verifies that cells in Google Sheets actually hold the written values (re-read verification)."""

    def __init__(self, actions: GSheetsActions):
        self.actions = actions

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        if not hints:
            return True

        if hints.get("check") == "cell_value_matches":
            spreadsheet_id = hints.get("spreadsheet_id")
            cell = hints.get("cell")
            expected_value = hints.get("expected_value")

            actual_value = self.actions.sandbox.read_cell(spreadsheet_id, cell)
            return str(actual_value) == str(expected_value)

        return True

