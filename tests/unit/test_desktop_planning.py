import pytest

from packages.core.brain.classifier import IntentEngine
from packages.core.brain.planner import DAGPlanner


@pytest.mark.asyncio
async def test_desktop_command_builds_open_type_verify_plan():
    classification = await IntentEngine().classify(
        "Open Notepad and type hello world",
        provider_name="mock",
    )

    assert classification.is_conversational is False
    assert classification.required_capabilities == [
        "host.open_app",
        "host.type_text",
        "host.read_screen",
    ]
    assert classification.entities["app"] == "notepad"

    plan = DAGPlanner().plan(classification, initial_inputs={"text": "hello world"})
    assert [step.capability for step in plan.steps] == classification.required_capabilities
    assert plan.steps[0].inputs["app"] == "notepad"
    assert plan.steps[1].inputs["text"] == "hello world"
    assert plan.steps[2].depends_on == [plan.steps[1].step_key]