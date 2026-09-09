"""Unit tests for OmniBrain Proactive Heartbeat Engine."""
import pytest
from datetime import datetime, timezone, timedelta

from packages.core.db.models import Notification
from apps.worker.proactive import ProactiveEngine
from packages.core.voice.tts import VoiceEngine


@pytest.mark.asyncio
async def test_proactive_cycle_generates_briefing(db_session, test_user):
    """Test that running proactive cycle generates a daily morning briefing."""
    engine = ProactiveEngine()

    # Run cycle with force_briefing=True and generate_audio=False for quick unit testing
    notifs = await engine.run_proactive_cycle(
        session=db_session,
        user_id=test_user.id,
        force_briefing=True,
        generate_audio=False,
    )

    assert len(notifs) >= 1
    briefing = next((n for n in notifs if n.type == "BRIEFING"), None)
    assert briefing is not None
    assert briefing.status == "UNREAD"
    assert "briefing" in briefing.title.lower()
    assert "Calendar" in briefing.message
    assert "Inbox" in briefing.message
    assert briefing.spoken_text is not None


@pytest.mark.asyncio
async def test_proactive_cycle_deduplication(db_session, test_user):
    """Test that multiple runs within the same day do not create duplicate briefings."""
    from sqlalchemy import delete
    await db_session.execute(delete(Notification).where(Notification.user_id == test_user.id))
    await db_session.flush()

    engine = ProactiveEngine()

    # First run creates briefing
    notifs_1 = await engine.run_proactive_cycle(
        session=db_session,
        user_id=test_user.id,
        force_briefing=False,
        generate_audio=False,
    )
    assert any(n.type == "BRIEFING" for n in notifs_1)

    # Second run immediately after should NOT generate another briefing
    notifs_2 = await engine.run_proactive_cycle(
        session=db_session,
        user_id=test_user.id,
        force_briefing=False,
        generate_audio=False,
    )
    assert not any(n.type == "BRIEFING" for n in notifs_2)
