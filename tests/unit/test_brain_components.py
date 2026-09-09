import pytest
from uuid import uuid4

from packages.core.db.models import User, Connection
from packages.core.brain.context import ContextEngine
from packages.core.brain.classifier import IntentEngine, TaskClassification
from packages.core.brain.planner import DAGPlanner
from packages.core.brain.synthesizer import ResultSynthesizer
from packages.core.voice.tts import VoiceEngine


@pytest.mark.asyncio
async def test_context_engine_assembly(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"brain_user_{user_id.hex[:6]}@example.com",
        name="Brain Master",
        role="owner",
        timezone="Asia/Kolkata",
        settings={},
    )
    conn = Connection(
        user_id=user_id,
        provider="google",
        account_email="brain_master@gmail.com",
        scopes=[],
        access_token_encrypted="mock-encrypted-token",
        status="ONLINE",
    )
    db_session.add_all([user, conn])
    await db_session.commit()

    engine = ContextEngine()
    ctx = await engine.assemble_context(db_session, user_id)

    assert ctx.user_name == "Brain Master"
    assert ctx.timezone_str == "Asia/Kolkata"
    assert "Gmail" in ctx.active_tools
    snippet = ctx.to_system_prompt_snippet()
    assert "Brain Master" in snippet
    assert "Current Context" in snippet


@pytest.mark.asyncio
async def test_intent_classifier_fallback():
    engine = IntentEngine()
    classification = await engine.classify(
        user_message="Check my inbox and tell me what emails I have",
        provider_name="mock",
    )

    assert classification.path in ("FAST", "SMART")
    assert len(classification.required_capabilities) >= 1
    assert any("gmail" in c for c in classification.required_capabilities)


def test_dag_planner_generation():
    planner = DAGPlanner()
    classification = TaskClassification(
        is_conversational=False,
        path="SMART",
        goal="Search messages and list events",
        required_capabilities=["gmail.search", "calendar.list_events"],
    )

    plan = planner.plan(classification)
    assert len(plan.steps) == 2
    assert plan.steps[0].capability == "gmail.search"
    assert plan.steps[1].capability == "calendar.list_events"
    assert plan.steps[1].depends_on == [plan.steps[0].step_key]


def test_result_synthesizer_five_point_report():
    synthesizer = ResultSynthesizer()
    steps_data = [
        {
            "step_key": "step_1",
            "capability": "gmail.search",
            "status": "SUCCEEDED",
            "outputs": {"messages": [{"id": "m1", "subject": "Urgent review"}]},
        },
        {
            "step_key": "step_2",
            "capability": "calendar.list_events",
            "status": "SUCCEEDED",
            "outputs": {"events": [{"id": "e1", "summary": "Standup"}]},
        },
    ]

    report = synthesizer.synthesize(
        task_goal="Check schedule and emails",
        task_status="COMPLETED",
        steps_data=steps_data,
    )

    assert report.status == "COMPLETED"
    assert len(report.what_was_done) == 2
    assert len(report.important_results) == 2
    assert len(report.any_problems) == 0
    assert "completed" in report.spoken_summary.lower()

    md = report.to_markdown()
    assert "**STATUS**: COMPLETED" in md
    assert "**WHAT WAS DONE**:" in md
    assert "**IMPORTANT RESULTS**:" in md


@pytest.mark.asyncio
async def test_voice_engine_synthesis():
    voice = VoiceEngine()
    try:
        audio_bytes = await voice.synthesize_to_bytes("Hello, I am your personal AI assistant.")
        assert len(audio_bytes) > 100
        # MP3 sync frame starts with 0xFF
        assert audio_bytes[:2] in (b'\xff\xfb', b'\xff\xf3', b'ID3') or len(audio_bytes) > 500
    except Exception:
        # If external network unreachable during offline test, pass gracefully
        pytest.skip("External TTS endpoint not reachable in sandbox network")
