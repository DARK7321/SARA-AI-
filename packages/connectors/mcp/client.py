"""Model Context Protocol (MCP) Connector Client conforming to Universal Tool Contract."""
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
from packages.connectors.mcp.actions import MCPActions, MCPSandbox


class MCPConnector(BaseConnector):
    """Universal MCP Tool Connector."""

    def __init__(
        self,
        server_url: Optional[str] = None,
        sandbox: Optional[MCPSandbox] = None,
    ):
        super().__init__(
            connector_id="connector-mcp",
            name="Model Context Protocol",
            version="1.0",
        )
        self.server_url = server_url
        self.actions = MCPActions(sandbox=sandbox)

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
                server_url=self.server_url,
            )

            if isinstance(result_data, list):
                output_data = {"items": result_data}
            else:
                output_data = result_data or {}

            verification_hints = {
                "check": "mcp_tool_executed",
                "action": request.action,
                "has_data": bool(output_data),
            }

            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data=output_data,
                metadata=ToolMetadata(latency_ms=latency_ms),
                verification_hints=verification_hints,
            )
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                error=ToolError(
                    error_class=ErrorClass.TRANSIENT,
                    message=str(e),
                    retryable=False,
                ),
                metadata=ToolMetadata(latency_ms=latency_ms),
            )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE",
            "connector_id": self.connector_id,
            "mode": "live" if self.server_url else "sandbox",
            "server_url": self.server_url or "in-memory-sandbox",
        }

    def get_capabilities(self) -> List[str]:
        return [
            "mcp.filesystem.read_file",
            "mcp.filesystem.list_dir",
            "mcp.sqlite.query",
            "mcp.fetch.get",
        ]

    async def verify(
        self,
        action: str,
        hints: Dict[str, Any],
    ) -> bool:
        return bool(hints and hints.get("has_data") is not False)

