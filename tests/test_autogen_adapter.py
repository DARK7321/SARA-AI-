"""Unit tests for Microsoft AutoGen Framework Adapter."""
import pytest
from packages.core.agents.frameworks.autogen_adapter import AutoGenAdapter


@pytest.mark.asyncio
async def test_autogen_adapter_metadata():
    adapter = AutoGenAdapter()
    assert adapter.name == "autogen"
    assert isinstance(adapter.is_installed(), bool)

    teams = adapter.list_available_crews_or_graphs()
    assert len(teams) >= 2
    team_ids = [t["id"] for t in teams]
    assert "coder_and_critic" in team_ids
    assert "strategy_debate" in team_ids


@pytest.mark.asyncio
async def test_autogen_execute_coder_and_critic(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = AutoGenAdapter()
    result = await adapter.execute(
        task="Implement a thread-safe LRU cache with TTL expiration in Python",
        crew_or_graph_name="coder_and_critic",
    )

    assert result.framework == "autogen"
    assert result.crew_or_graph_name == "coder_and_critic"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) >= 3
    # Check that termination keyword was handled
    assert result.metadata["terminated_cleanly"] is True
    assert any("TERMINATE" in msg.content for msg in result.agent_dialogue)


@pytest.mark.asyncio
async def test_autogen_execute_strategy_debate(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = AutoGenAdapter()
    result = await adapter.execute(
        task="Evaluate GraphQL vs gRPC for internal service communications",
        crew_or_graph_name="strategy_debate",
    )

    assert result.framework == "autogen"
    assert result.crew_or_graph_name == "strategy_debate"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) >= 3
    assert result.metadata["turns_completed"] >= 3

