"""Base abstractions and data contracts for Multi-Agent Framework Adapters."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    role: str = Field(description="Agent role or persona, e.g., 'Senior Researcher', 'Coder', 'Critic'")
    name: str = Field(description="Agent identifier name")
    content: str = Field(description="Message body or thought")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FrameworkExecutionResult(BaseModel):
    framework: str = Field(description="Framework name: 'crewai', 'langgraph', 'autogen'")
    crew_or_graph_name: str = Field(description="Name of the executed crew, graph, or team")
    status: str = Field(default="COMPLETED", description="COMPLETED, FAILED, or PARTIAL")
    task: str = Field(description="Original task or prompt given to the framework")
    agent_dialogue: List[AgentMessage] = Field(default_factory=list, description="Step-by-step dialogue and agent thoughts")
    final_output: str = Field(description="Final synthesized output produced by the crew/graph")
    execution_time_ms: int = Field(default=0, description="Elapsed execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional framework telemetry or token counts")


class BaseFrameworkAdapter(ABC):
    """Abstract interface for multi-agent framework integrations."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def is_installed(self) -> bool:
        """Check whether the underlying framework library is installed in the environment."""
        pass

    @abstractmethod
    def list_available_crews_or_graphs(self) -> List[Dict[str, Any]]:
        """List pre-built agent crews, teams, or computation graphs supported by this adapter."""
        pass

    @abstractmethod
    async def execute(
        self,
        task: str,
        crew_or_graph_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> FrameworkExecutionResult:
        """Execute the multi-agent task and return structured results with agent dialogue."""
        pass

