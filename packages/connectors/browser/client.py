"""Browser Connector Client conforming to Universal Tool Contract."""
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
from packages.connectors.browser.actions import BrowserActions, BrowserSandbox


class BrowserConnector(BaseConnector):
    """Browser Universal Tool Connector."""

    def __init__(
        self,
        sandbox: Optional[BrowserSandbox] = None,
        force_sandbox: bool = False,
    ):
        super().__init__(
            connector_id="connector-browser",
            name="Browser",
            version="1.0",
        )
        self.actions = BrowserActions(sandbox=sandbox)
        self.force_sandbox = force_sandbox

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
                force_sandbox=self.force_sandbox,
            )

            verification_hints = {
                "check": "content_extracted",
                "url": request.input.get("url"),
                "has_content": bool(result_data.get("content")),
            }

            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data=result_data,
                metadata=ToolMetadata(latency_ms=latency_ms),
                verification_hints=verification_hints,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                error=ToolError(
                    error_class=ErrorClass.EXTERNAL_API_ERROR,
                    message=str(e),
                    retryable=False,
                ),
                metadata=ToolMetadata(latency_ms=latency_ms),
            )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE",
            "connector_id": self.connector_id,
            "mode": "sandbox" if self.force_sandbox else "live",
        }

    def get_capabilities(self) -> List[str]:
        return [
            "browser.extract_content",
            "browser.open",
            "browser.search",
            "browser.search_images",
            "browser.navigate",
        ]

    async def verify(
        self,
        action: str,
        result: Any,
        expected_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if action == "browser.extract_content":
            return bool(result and (result.get("content") or result.get("title")))
        if action in ("browser.search", "browser.search_images", "browser.open"):
            return bool(result and result.get("success", False))
        return True
