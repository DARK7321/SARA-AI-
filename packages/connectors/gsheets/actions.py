"""Google Sheets Action handlers with sandbox fixture support."""
from typing import Any, Dict, List, Optional
import httpx

GSHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class GSheetsSandbox:
    """In-memory Google Sheets sandbox for testing and development."""

    def __init__(self):
        self.sheets: Dict[str, Dict[str, Any]] = {
            "sheet_101": {
                "title": "Quarterly Budget 2026",
                "cells": {
                    "A1": "Department", "B1": "Budget", "C1": "Spent",
                    "A2": "Engineering", "B2": "$50,000", "C2": "$12,000",
                    "A3": "Marketing", "B3": "$20,000", "C3": "$8,500",
                },
                "rows": [
                    ["Department", "Budget", "Spent"],
                    ["Engineering", "$50,000", "$12,000"],
                    ["Marketing", "$20,000", "$8,500"],
                ],
            }
        }

    def read_rows(self, spreadsheet_id: str, range_name: str = "Sheet1!A1:C10") -> List[List[Any]]:
        if spreadsheet_id in self.sheets:
            return self.sheets[spreadsheet_id]["rows"]
        raise ValueError(f"Spreadsheet {spreadsheet_id} not found")

    def append_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> Dict[str, Any]:
        if spreadsheet_id in self.sheets:
            self.sheets[spreadsheet_id]["rows"].extend(values)
            return {"spreadsheet_id": spreadsheet_id, "appended_rows": len(values)}
        raise ValueError(f"Spreadsheet {spreadsheet_id} not found")

    def update_cell(self, spreadsheet_id: str, cell: str, value: Any) -> Dict[str, Any]:
        if spreadsheet_id in self.sheets:
            self.sheets[spreadsheet_id]["cells"][cell] = value
            return {"spreadsheet_id": spreadsheet_id, "cell": cell, "value": value}
        raise ValueError(f"Spreadsheet {spreadsheet_id} not found")

    def read_cell(self, spreadsheet_id: str, cell: str) -> Any:
        if spreadsheet_id in self.sheets:
            return self.sheets[spreadsheet_id]["cells"].get(cell)
        return None


class GSheetsActions:
    """Dispatches Google Sheets actions either to live API or sandbox."""

    def __init__(self, sandbox: Optional[GSheetsSandbox] = None):
        self.sandbox = sandbox or GSheetsSandbox()

    async def execute_action(
        self,
        action: str,
        inputs: Dict[str, Any],
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not access_token or access_token.startswith("mock-"):
            if action == "sheets.read_rows":
                return {"rows": self.sandbox.read_rows(inputs["spreadsheet_id"], inputs.get("range", "A1:C10"))}
            elif action == "sheets.append_rows":
                return self.sandbox.append_rows(inputs["spreadsheet_id"], inputs.get("range", "A1"), inputs["values"])
            elif action == "sheets.update_cell":
                return self.sandbox.update_cell(inputs["spreadsheet_id"], inputs["cell"], inputs["value"])
            raise ValueError(f"Unknown Sheets action: {action}")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            sheet_id = inputs["spreadsheet_id"]

            if action == "sheets.read_rows":
                rng = inputs.get("range", "Sheet1!A1:Z100")
                resp = await client.get(f"{GSHEETS_API_BASE}/{sheet_id}/values/{rng}", headers=headers)
                resp.raise_for_status()
                return resp.json()

            elif action == "sheets.append_rows":
                rng = inputs.get("range", "Sheet1!A1")
                resp = await client.post(
                    f"{GSHEETS_API_BASE}/{sheet_id}/values/{rng}:append",
                    headers=headers,
                    params={"valueInputOption": "USER_ENTERED"},
                    json={"values": inputs["values"]},
                )
                resp.raise_for_status()
                return resp.json()

            elif action == "sheets.update_cell":
                cell = inputs["cell"]
                resp = await client.put(
                    f"{GSHEETS_API_BASE}/{sheet_id}/values/{cell}",
                    headers=headers,
                    params={"valueInputOption": "USER_ENTERED"},
                    json={"values": [[inputs["value"]]]},
                )
                resp.raise_for_status()
                return resp.json()

            raise ValueError(f"Unknown Sheets action: {action}")

