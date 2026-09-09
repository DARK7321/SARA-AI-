"""Unit tests for LangGraph & LangChain Adapter."""
import pytest
from packages.core.agents.frameworks.langgraph_adapter import LangGraphAdapter


@pytest.mark.asyncio
async def test_langgraph_adapter_metadata():
    adapter = LangGraphAdapter()
    assert adapter.name == "langgraph"
    assert isinstance(adapter.is_installed(), bool)

    graphs = adapter.list_available_crews_or_graphs()
    assert len(graphs) >= 3
    graph_ids = [g["id"] for g in graphs]
    assert "document_processor" in graph_ids
    assert "data_pipeline" in graph_ids
    assert "support_triage" in graph_ids


@pytest.mark.asyncio
async def test_langgraph_execute_document_processor(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = LangGraphAdapter()
    result = await adapter.execute(
        task="Parse and validate quarterly financial revenue breakdown",
        crew_or_graph_name="document_processor",
    )

    assert result.framework == "langgraph"
    assert result.crew_or_graph_name == "document_processor"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) >= 4
    nodes_visited = result.metadata["nodes_visited"]
    assert "ingest" in nodes_visited
    assert "extract_entities" in nodes_visited
    assert "validate" in nodes_visited
    assert "summarize" in nodes_visited
    assert result.metadata["cycle_count"] >= 1


@pytest.mark.asyncio
async def test_langgraph_execute_data_pipeline(monkeypatch):
    monkeypatch.setenv("TESTING", "1")
    adapter = LangGraphAdapter()
    result = await adapter.execute(
        task="Normalize analytics events stream into warehouse format",
        crew_or_graph_name="data_pipeline",
    )

    assert result.framework == "langgraph"
    assert result.crew_or_graph_name == "data_pipeline"
    assert result.status == "COMPLETED"
    assert len(result.agent_dialogue) == 4
    assert result.metadata["nodes_visited"] == ["extract", "transform", "quality_check", "load"]

