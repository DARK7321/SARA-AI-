import pytest
from pydantic import BaseModel
from sqlalchemy import select

from packages.core.router.model_router import ModelRouter
from packages.core.router.prompt_registry import PromptRegistry
from packages.core.db.models import PromptRun


class ClassificationOutput(BaseModel):
    path: str
    goal: str
    urgency: str


def test_prompt_registry_loading():
    registry = PromptRegistry()
    sys_prompt, user_prompt = registry.format(
        "task_classifier", version=1, command="Clean my inbox"
    )

    assert sys_prompt is not None
    assert "OmniBrain" in sys_prompt
    assert "Clean my inbox" in user_prompt


@pytest.mark.asyncio
async def test_model_router_completion():
    router = ModelRouter()
    # Use mock provider for unit tests
    res = await router.complete(
        prompt="Test question",
        path="FAST",
        provider_name="mock",
    )
    assert res.content is not None
    assert res.model == "gemini-2.0-flash"
    assert res.provider == "mock"


@pytest.mark.asyncio
async def test_model_router_structured_output():
    router = ModelRouter()
    res = await router.complete(
        prompt="Classify this task",
        path="SMART",
        schema=ClassificationOutput,
        provider_name="mock",
    )
    assert res.structured_data is not None
    assert "path" in res.structured_data
    assert "goal" in res.structured_data


@pytest.mark.asyncio
async def test_model_router_telemetry_logging(db_session):
    router = ModelRouter()

    res = await router.complete(
        prompt="Log this test run",
        path="FAST",
        provider_name="mock",
        db_session=db_session,
        prompt_key="task_classifier",
        prompt_version=1,
    )

    assert res.content is not None

    # Check prompt_runs record in database
    result = await db_session.execute(
        select(PromptRun).where(PromptRun.prompt_key == "task_classifier")
    )
    run_record = result.scalar_one_or_none()
    assert run_record is not None
    assert run_record.model == "gemini-2.0-flash"
    assert run_record.valid_output is True

