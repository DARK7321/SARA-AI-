"""Google Calendar Connector Client conforming to the Universal Tool Contract."""
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
from packages.connectors.gcal.actions import GCalActions, GCalSandbox
from packages.connectors.gcal.verify import GCalVerifier


class GCalConnector(BaseConnector):
    """Google Calendar Connector plugin."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        sandbox: Optional[GCalSandbox] = None,
    ):
        super().__init__(
            connector_id="connector-gcal",
            name="Google Calendar",
            version="1.0",
        )
        self.access_token = access_token
        self.actions = GCalActions(sandbox=sandbox)
        self.verifier = GCalVerifier(actions=self.actions)

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
            if request.action == "calendar.create_event":
                verification_hints = {"check": "event_exists", "event_id": result_data.get("id")}

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
                error=ToolError(error_class=ErrorClass.TRANSIENT, message=f"Calendar API error: {str(e)}", retryable=True),
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
            "calendar.list_events",
            "calendar.create_event",
        ]

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        return await self.verifier.verify(action, hints)

