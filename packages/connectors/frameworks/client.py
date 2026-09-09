"""Universal Tool Contract Connector for Multi-Agent Frameworks."""
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
from packages.core.agents.frameworks import (
    get_framework_adapter,
    list_all_frameworks,
)


class FrameworksConnector(BaseConnector):
    """Universal Tool Connector for CrewAI, LangGraph, and AutoGen."""

    def __init__(self):
        super().__init__(
            connector_id="connector-frameworks",
            name="MultiAgentFrameworks",
            version="1.0",
        )

    async def health_check(self) -> Dict[str, Any]:
        """Return connector health status."""
        return {
            "status": "ONLINE",
            "frameworks": ["crewai", "langgraph", "autogen"],
            "ready": True,
        }

    def get_capabilities(self) -> List[str]:
        """Return capability tags provided by this connector."""
        return [
            "frameworks.list",
            "frameworks.execute",
            "crewai.execute",
            "langgraph.execute",
            "autogen.execute",
        ]

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
            action = request.action.lower()
            inputs = request.input or {}

            if action in ("frameworks.list", "list"):
                frameworks_data = list_all_frameworks()
                latency_ms = int((time.time() - start_time) * 1000)
                return ToolResponse(
                    success=True,
                    data={"frameworks": frameworks_data},
                    metadata=ToolMetadata(latency_ms=latency_ms),
                )

            # Determine framework and target
            framework_name = "crewai"
            if action.startswith("crewai"):
                framework_name = "crewai"
            elif action.startswith("langgraph"):
                framework_name = "langgraph"
            elif action.startswith("autogen"):
                framework_name = "autogen"
            else:
                framework_name = inputs.get("framework", "crewai")

            task_desc = inputs.get("task") or inputs.get("prompt") or "Perform comprehensive analysis"
            template_name = inputs.get("crew_name") or inputs.get("graph_name") or inputs.get("team_name") or inputs.get("template")

            adapter = get_framework_adapter(framework_name)
            result = await adapter.execute(
                task=task_desc,
                crew_or_graph_name=template_name,
                config=inputs.get("config"),
            )

            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data=result.model_dump(),
                metadata=ToolMetadata(latency_ms=latency_ms),
                verification_hints={
                    "framework": framework_name,
                    "dialogue_count": len(result.agent_dialogue),
                    "status": result.status,
                },
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                error=ToolError(
                    message=f"Framework execution failed: {str(e)}",
                    error_class=ErrorClass.EXTERNAL_API_ERROR,
                    details={"error": str(e)},
                ),
                metadata=ToolMetadata(latency_ms=latency_ms),
            )

