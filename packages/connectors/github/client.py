"""GitHub Connector Client conforming to Universal Tool Contract."""
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
from packages.connectors.github.actions import GitHubActions, GitHubSandbox


class GitHubConnector(BaseConnector):
    """GitHub Universal Tool Connector."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        sandbox: Optional[GitHubSandbox] = None,
    ):
        super().__init__(
            connector_id="connector-github",
            name="GitHub",
            version="1.0",
        )
        self.access_token = access_token
        self.actions = GitHubActions(sandbox=sandbox)

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
            if request.action == "github.create_issue":
                verification_hints = {
                    "check": "issue_created",
                    "number": result_data.get("number") if isinstance(result_data, dict) else None,
                }

            if isinstance(result_data, list):
                if request.action == "github.list_issues":
                    output_data = {"issues": result_data}
                elif request.action == "github.list_prs":
                    output_data = {"pull_requests": result_data}
                else:
                    output_data = {"items": result_data}
            else:
                output_data = result_data or {}

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
            "mode": "live" if (self.access_token and not self.access_token.startswith("mock-")) else "sandbox",
        }

    def get_capabilities(self) -> List[str]:
        return [
            "github.list_issues",
            "github.create_issue",
            "github.list_prs",
        ]

    async def verify(
        self,
        action: str,
        result: Any,
        expected_state: Optional[Dict[str, Any]] = None,
    ) -> bool:
        if action == "github.create_issue":
            return bool(result and result.get("number"))
        return True
