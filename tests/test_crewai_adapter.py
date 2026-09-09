"""Unit tests for CrewAI Multi-Agent Framework Adapter."""
import pytest
from packages.core.agents.frameworks.crewai_adapter import CrewAIAdapter


@pytest.mark.asyncio
async def test_crewai_adapter_metadata():
    adapter = CrewAIAdapter()
    assert adapter.name == "crewai"
    assert isinstance(adapter.is_installed(), bool)

    crews = adapter.list_available_crews_or_graphs()
    assert len(crews) >= 3
    crew_ids = [c["id"] for c in crews]
    assert "deep_research" in crew_ids
    assert "code_review" in crew_ids
    assert "content_strategy" in crew_ids


@pytest.mark.asyncio
async def test_crewai_execute_deep_research(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = CrewAIAdapter()
    result = await adapter.execute(
        task="Investigate quantum neural networks and latency benchmarks",
        crew_or_graph_name="deep_research",
    )

    assert result.framework == "crewai"
    assert result.crew_or_graph_name == "deep_research"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) >= 3
    assert result.agent_dialogue[0].name == "researcher"
    assert "researcher" in [m.name for m in result.agent_dialogue]
    assert "critic" in [m.name for m in result.agent_dialogue]
    assert "synthesizer" in [m.name for m in result.agent_dialogue]
    assert "CrewAI Execution Report" in result.final_output


@pytest.mark.asyncio
async def test_crewai_execute_code_review(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = CrewAIAdapter()
    result = await adapter.execute(
        task="Review async connection pool and Redis pipeline caching logic",
        crew_or_graph_name="code_review",
    )

    assert result.framework == "crewai"
    assert result.crew_or_graph_name == "code_review"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) == 3
    roles = [m.role for m in result.agent_dialogue]
    assert "Security Auditor" in roles
    assert "Performance Engineer" in roles
    assert "Senior Architect" in roles

