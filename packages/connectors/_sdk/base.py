"""Base Connector SDK for OmniBrain.

Every connector plugin extends BaseConnector, exposing capabilities
under the Universal Tool Contract.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from packages.connectors._sdk.contract import (
    ToolRequest,
    ToolResponse,
    ToolError,
    ErrorClass,
    ToolMetadata,
)


class BaseConnector(ABC):
    """Abstract Base Connector interface."""

    def __init__(self, connector_id: str, name: str, version: str = "1.0"):
        self.connector_id = connector_id
        self.name = name
        self.version = version

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResponse:
        """Execute an action strictly conforming to the Universal Tool Contract."""
        ...

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return connector health status: ONLINE, DEGRADED, RATE_LIMITED, AUTH_FAILURE, OFFLINE."""
        ...

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return capability tags provided by this connector (e.g. ['email.send', 'email.read'])."""
        ...

    async def verify(self, action: str, hints: Dict[str, Any]) -> bool:
        """Post-condition verification check.
        
        Subclasses can override to perform a real read-after-write verification.
        Default returns True if no hints required.
        """
        return True
