"""Google Sheets Connector Client conforming to the Universal Tool Contract."""
import time
from typing import Any, Dict, List, Optional

from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import (
    ToolRequest,
    ToolResponse,
    ToolMetadata,
    ToolError,
    ErrorClass,
)
from packages.connectors.gsheets.actions import GSheetsActions, GSheetsSandbox
from packages.connectors.gsheets.verify import GSheetsVerifier


class GSheetsConnector(BaseConnector):
    """Google Sheets Connector plugin."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        sandbox: Optional[GSheetsSandbox] = None,
    ):
        super().__init__(
            connector_id="connector-gsheets",
            name="Google Sheets",
            version="1.0",
        )
        self.access_token = access_token
        self.actions = GSheetsActions(sandbox=sandbox)
        self.verifier = GSheetsVerifier(actions=self.actions)

    async def execute(self, request: ToolRequest) -> ToolResponse:
        start_time = time.time()

        if request.dry_run:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data={"simulated": True, "action": request.action, "inputs": request.input},
                metadata=ToolMetadata(latency_ms=latency_ms),
                verification_hints={"dry_run": True},
            )

        try:
            result_data = await self.actions.execute_action(
                action=request.action,
                inputs=request.input,
                access_token=self.access_token,
            )

            verification_hints = {}
            if request.action == "sheets.update_cell":
                verification_hints = {
                    "check": "cell_value_matches",
                    "spreadsheet_id": request.input.get("spreadsheet_id"),
                    "cell": request.input.get("cell"),
                    "expected_value": request.input.get("value"),
                }

            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data=result_data,
                metadata=ToolMetadata(latency_ms=latency_ms, cost=0.0),
                verification_hints=verification_hints,
            )

        except ValueError as ve:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                error=ToolError(error_class=ErrorClass.VALIDATION, message=str(ve)),
                metadata=ToolMetadata(latency_ms=latency_ms),
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                error=ToolError(error_class=ErrorClass.TRANSIENT, message=f"Sheets API error: {str(e)}", retryable=True),
                metadata=ToolMetadata(latency_ms=latency_ms),
            )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE",
            "connector_id": self.connector_id,
            "mode": "live" if (self.access_token and not self.access_token.startswith("mock-")) else "sandbox",
        }

    def get_capabilities(self) -> List[str]:
        return [
            "sheets.read_rows",
            "sheets.append_rows",
            "sheets.update_cell",
        ]

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        return await self.verifier.verify(action, hints)

