"""Google Drive Connector Client conforming to the Universal Tool Contract."""
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
from packages.connectors.gdrive.actions import GDriveActions, GDriveSandbox
from packages.connectors.gdrive.verify import GDriveVerifier


class GDriveConnector(BaseConnector):
    """Google Drive Connector plugin."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        sandbox: Optional[GDriveSandbox] = None,
    ):
        super().__init__(
            connector_id="connector-gdrive",
            name="Google Drive",
            version="1.0",
        )
        self.access_token = access_token
        self.actions = GDriveActions(sandbox=sandbox)
        self.verifier = GDriveVerifier(actions=self.actions)

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
            if request.action == "drive.create":
                verification_hints = {"check": "file_exists", "file_id": result_data.get("id")}
            elif request.action == "drive.share":
                verification_hints = {
                    "check": "file_shared",
                    "file_id": request.input.get("file_id"),
                    "email": request.input.get("email"),
                }

            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data=result_data,
                metadata=ToolMetadata(latency_ms=latency_ms),
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
                error=ToolError(error_class=ErrorClass.TRANSIENT, message=f"Drive API error: {str(e)}", retryable=True),
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
            "drive.list",
            "drive.read",
            "drive.create",
            "drive.share",
        ]

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        return await self.verifier.verify(action, hints)

