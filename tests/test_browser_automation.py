"""Unit tests for Chrome and Browser Automation Pipeline in OmniBrain."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from packages.core.brain.classifier import IntentEngine, TaskClassification, clean_search_query
from packages.core.brain.planner import DAGPlanner, CAPABILITY_CONNECTOR_MAP
from packages.connectors.host_agent.client import HostAgentConnector
from packages.connectors.browser.client import BrowserConnector
from packages.connectors._sdk.contract import ToolRequest, ToolContext, SideEffectType
from packages.core.execution.engine import StepExecutionEngine
from packages.core.db.models import User, Task, TaskStep, ToolCall


def test_clean_search_query_variants():
    """Verify clean_search_query extracts clean terms across English, Hindi, and Hinglish."""
    test_cases = [
        ("hey sara open chrome and search about 1967 ford mustang", "1967 ford mustang"),
        ("sara open crome and search about 1967 ford mustang", "1967 ford mustang"),
        ("open chrome and search about 1967 ford mustang", "1967 ford mustang"),
        ("open chrome and search 1967 ford mustang image", "1967 ford mustang image"),
        ("chrome me search box me likho 1967 ford mustang", "1967 ford mustang"),
        ("chrome kholo aur 1967 ford mustang search karo", "1967 ford mustang"),
        ("chrome me 1967 ford mustang dhundo", "1967 ford mustang"),
        ("search 1967 ford mustang in chrome", "1967 ford mustang"),
        ("search about 1967 ford mustang", "1967 ford mustang"),
        ("1967 ford mustang", "1967 ford mustang"),
        ("open chrome and then search 1967 ford mustang", "1967 ford mustang"),
        ("chrome open karke 1967 ford mustang search karo", "1967 ford mustang"),
        ("open chrome", ""),
        ("sara crome open kar", ""),
        ("open google chrome", ""),
        ("open chrome browser", ""),
        ("sara crome open kar do", ""),
    ]
    for inp, expected in test_cases:
        res = clean_search_query(inp)
        if expected == "":
            assert res == "", f"Expected empty query for pure open '{inp}', got '{res}'"
        else:
            assert expected in res, f"Expected '{expected}' in '{res}' for input '{inp}'"


@pytest.mark.asyncio
async def test_classifier_chrome_search_intent():
    """Verify deterministic and prompt-based classification of Chrome search requests."""
    engine = IntentEngine()
    
    # Deterministic fallback classification
    cmd = "hey sara open chrome and search about 1967 ford mustang"
    classification = await engine.classify(cmd, provider_name="mock_offline")
    
    assert classification.is_conversational is False
    assert "host.open_app" in classification.required_capabilities
    assert "browser.search" in classification.required_capabilities
    assert classification.entities.get("app") == "chrome"
    assert "1967 ford mustang" in classification.entities.get("query", "")


def test_dag_planner_chrome_search():
    """Verify DAGPlanner decomposes Chrome search into host.open_app and browser.search with propagated inputs."""
    planner = DAGPlanner()
    classification = TaskClassification(
        is_conversational=False,
        path="SMART",
        goal="Open Chrome and search about 1967 Ford Mustang",
        entities={"app": "chrome", "query": "1967 ford mustang"},
        required_capabilities=["host.open_app", "browser.search"],
    )
    raw_cmd = "hey sara open chrome and search about 1967 ford mustang"
    dag = planner.plan(classification, initial_inputs={"raw_command": raw_cmd})

    assert len(dag.steps) == 2
    step1, step2 = dag.steps[0], dag.steps[1]

    # Step 1: Open Chrome
    assert step1.capability == "host.open_app"
    assert step1.tool_id == "connector-host-agent"
    assert step1.inputs["app"] == "chrome"
    assert step1.inputs["query"] == "1967 ford mustang"
    assert step1.inputs["raw_command"] == raw_cmd

    # Step 2: Browser Search
    assert step2.capability == "browser.search"
    assert step2.tool_id == "connector-browser"
    assert step2.inputs["query"] == "1967 ford mustang"
    assert step2.inputs["raw_command"] == raw_cmd
    assert step2.depends_on == [step1.step_key]


def test_capability_connector_map_has_browser():
    """Verify CAPABILITY_CONNECTOR_MAP maps browser capabilities to connector-browser."""
    assert "browser.search" in CAPABILITY_CONNECTOR_MAP
    assert CAPABILITY_CONNECTOR_MAP["browser.search"][0] == "connector-browser"
    assert "browser.open" in CAPABILITY_CONNECTOR_MAP
    assert CAPABILITY_CONNECTOR_MAP["browser.open"][0] == "connector-browser"
    assert "browser.search_images" in CAPABILITY_CONNECTOR_MAP
    assert CAPABILITY_CONNECTOR_MAP["browser.search_images"][0] == "connector-browser"


@pytest.mark.asyncio
async def test_host_agent_connector_preserves_query_and_raw_command():
    """Verify HostAgentConnector does not exclude query or raw_command from inputs."""
    connector = HostAgentConnector()
    req = ToolRequest(
        request_id="req_test_host_1",
        tool="connector-host-agent",
        action="host.open_app",
        input={
            "app": "chrome",
            "query": "1967 ford mustang",
            "raw_command": "hey sara open chrome and search about 1967 ford mustang",
            "dry_run": False,
            "goal": "ignored goal",
        },
        context=ToolContext(task_id="t1", step_id="s1"),
        idempotency_key="key_1",
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {"opened": True, "window_title": "Chrome Search: 1967 ford mustang"}}
        mock_post.return_value = mock_resp

        res = await connector.execute(req)
        assert res.success is True
        assert mock_post.called
        sent_json = mock_post.call_args[1]["json"]
        action_payload = sent_json["action"]
        
        # Verify raw_command and query were preserved!
        assert action_payload.get("app") == "chrome"
        assert action_payload.get("query") == "1967 ford mustang"
        assert action_payload.get("raw_command") == "hey sara open chrome and search about 1967 ford mustang"
        # Verify junk was excluded
        assert "goal" not in action_payload
        assert "dry_run" not in action_payload


if __name__ == "__main__":
    import asyncio
    test_clean_search_query_variants()
    print("[PASS] test_clean_search_query_variants")
    asyncio.run(test_classifier_chrome_search_intent())
    print("[PASS] test_classifier_chrome_search_intent")
    test_dag_planner_chrome_search()
    print("[PASS] test_dag_planner_chrome_search")
    test_capability_connector_map_has_browser()
    print("[PASS] test_capability_connector_map_has_browser")
    asyncio.run(test_host_agent_connector_preserves_query_and_raw_command())
    print("[PASS] test_host_agent_connector_preserves_query_and_raw_command")
    print("\nALL BROWSER AUTOMATION TESTS PASSED SUCCESSFULLY!")

