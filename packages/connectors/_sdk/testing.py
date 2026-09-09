"""Simulated / Fake Connector for automated testing and sandbox environments.

Allows testing full task execution graphs without touching real external accounts.
"""
import time
from typing import Any, Dict, List, Optional
from packages.connectors._sdk.base import BaseConnector
from packages.connectors._sdk.contract import (
    ToolRequest,
    ToolResponse,
    ToolError,
    ErrorClass,
    ToolMetadata,
)


class FakeConnector(BaseConnector):
    """Configurable test connector that simulates external systems."""

    def __init__(
        self,
        connector_id: str = "connector-fake",
        name: str = "Fake Test Connector",
        version: str = "1.0",
        predefined_responses: Optional[Dict[str, Dict[str, Any]]] = None,
        injected_errors: Optional[Dict[str, ToolError]] = None,
    ):
        super().__init__(connector_id=connector_id, name=name, version=version)
        self.predefined_responses = predefined_responses or {}
        self.injected_errors = injected_errors or {}
        self.call_history: List[ToolRequest] = []
        self.created_objects: Dict[str, Dict[str, Any]] = {}
        self.health_status = "ONLINE"

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """Simulate tool execution with call tracking, error injection, and dry-run support."""
        start_time = time.time()
        self.call_history.append(request)

        # 1. Check if error is injected for this action
        if request.action in self.injected_errors:
            error = self.injected_errors.pop(request.action)  # Pop so subsequent retries can succeed
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=False,
                data={},
                metadata=ToolMetadata(latency_ms=latency_ms, retries=0),
                error=error,
            )

        # 2. Check if dry_run mode
        if request.dry_run:
            latency_ms = int((time.time() - start_time) * 1000)
            return ToolResponse(
                success=True,
                data={"simulated": True, "action": request.action, "would_affect": request.input},
                metadata=ToolMetadata(latency_ms=latency_ms, cached=False),
                verification_hints={"dry_run": True},
            )

        # 3. Simulate success response
        action_data = self.predefined_responses.get(
            request.action,
            {"status": "ok", "action": request.action, "result": request.input},
        )

        # Record created object for post-condition checks
        obj_id = f"fake_obj_{len(self.created_objects) + 1}"
        self.created_objects[obj_id] = request.input

        latency_ms = int((time.time() - start_time) * 1000)
        return ToolResponse(
            success=True,
            data=action_data,
            metadata=ToolMetadata(latency_ms=latency_ms, cost=0.0),
            verification_hints={"check": "object_exists", "object_id": obj_id},
        )

    async def health_check(self) -> Dict[str, Any]:
        return {"status": self.health_status, "connector_id": self.connector_id}

    def get_capabilities(self) -> List[str]:
        return ["fake.read", "fake.write", "fake.delete", "fake.notify"]

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        """Check if the object created during execution actually exists in store."""
        if not hints:
            return True
        if hints.get("dry_run"):
            return True
        obj_id = hints.get("object_id")
        return obj_id in self.created_objects if obj_id else True
