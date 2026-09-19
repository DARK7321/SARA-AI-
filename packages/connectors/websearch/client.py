"""Web Search Connector for OmniBrain.

Enables Sara to search the internet in real-time using DuckDuckGo.
"""
from typing import Any, Dict, List
from duckduckgo_search import DDGS
import logging
import time

from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import ToolRequest, ToolResponse, ToolMetadata, ToolError, ErrorClass

logger = logging.getLogger("omnibrain.connectors.websearch")

class WebSearchConnector(BaseConnector):
    """Provides real-time internet search capabilities."""

    def __init__(self):
        super().__init__(
            connector_id="connector-websearch",
            name="Web Search",
            version="1.0"
        )

    async def execute(self, request: ToolRequest) -> ToolResponse:
        start_time = time.time()
        try:
            if request.action == "web.search":
                query = request.input.get("query")
                max_results = request.input.get("max_results", 3)
                results = self._search(query, max_results)
                from packages.core.security.injection import wrap_dict
                results = wrap_dict("websearch", results)
                latency_ms = int((time.time() - start_time) * 1000)
                return ToolResponse(
                    success=True,
                    data={"results": results},
                    metadata=ToolMetadata(latency_ms=latency_ms)
                )
            else:
                return ToolResponse(
                    success=False,
                    error=ToolError(error_class=ErrorClass.VALIDATION, message=f"Unknown capability: {request.action}")
                )
        except Exception as e:
            return ToolResponse(
                success=False,
                error=ToolError(error_class=ErrorClass.TOOL_UNAVAILABLE, message=str(e))
            )

    def _search(self, query: str, max_results: int) -> List[Dict[str, str]]:
        if not query:
            raise ValueError("Query is required for web search.")
            
        logger.info(f"Executing web search for: '{query}'")
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
        return results

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ONLINE",
            "connector_id": self.connector_id
        }

    def get_capabilities(self) -> List[str]:
        return ["web.search"]

