"""Multi-Agent Frameworks module for OmniBrain.

Exports adapters for CrewAI, LangGraph/LangChain, and AutoGen.
"""
from typing import Any, Dict, List, Optional

from packages.core.agents.frameworks.base import (
    AgentMessage,
    BaseFrameworkAdapter,
    FrameworkExecutionResult,
)
from packages.core.agents.frameworks.crewai_adapter import CrewAIAdapter
from packages.core.agents.frameworks.langgraph_adapter import LangGraphAdapter
from packages.core.agents.frameworks.autogen_adapter import AutoGenAdapter

_REGISTRY: Dict[str, BaseFrameworkAdapter] = {}


def get_framework_adapter(name: str) -> BaseFrameworkAdapter:
    """Retrieve or instantiate a framework adapter by name."""
    normalized = name.lower().strip()
    if normalized not in _REGISTRY:
        if normalized in ("crewai", "crew_ai", "crew"):
            _REGISTRY[normalized] = CrewAIAdapter()
        elif normalized in ("langgraph", "langchain", "lang_graph"):
            _REGISTRY[normalized] = LangGraphAdapter()
        elif normalized in ("autogen", "pyautogen", "auto_gen"):
            _REGISTRY[normalized] = AutoGenAdapter()
        else:
            raise ValueError(f"Unknown multi-agent framework: '{name}'. Supported: crewai, langgraph, autogen")
    return _REGISTRY[normalized]


def list_all_frameworks() -> List[Dict[str, Any]]:
    """List all registered framework adapters with availability and supported templates."""
    adapters = [CrewAIAdapter(), LangGraphAdapter(), AutoGenAdapter()]
    results = []
    for adapter in adapters:
        results.append({
            "framework": adapter.name,
            "is_installed": adapter.is_installed(),
            "templates": adapter.list_available_crews_or_graphs(),
        })
    return results


__all__ = [
    "AgentMessage",
    "BaseFrameworkAdapter",
    "FrameworkExecutionResult",
    "CrewAIAdapter",
    "LangGraphAdapter",
    "AutoGenAdapter",
    "get_framework_adapter",
    "list_all_frameworks",
]

