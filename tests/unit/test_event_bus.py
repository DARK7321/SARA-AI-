"""Unit tests for Redis Streams EventBus."""
import pytest
from packages.core.events.bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_and_read():
    bus = EventBus(redis_url="redis://nonexistent:9999/0")  # forces in-memory fallback for test isolation

    # 1. Publish test event
    payload = {"status": "ok", "action": "test_ping"}
    event = await bus.publish_event(
        topic="events.test.topic",
        data=payload,
        source="unit_test",
    )
    assert event.event_id is not None
    assert event.topic == "events.test.topic"
    assert event.data["status"] == "ok"

    # 2. Read events from topic
    events = await bus.read_events(topic="events.test.topic", count=5)
    assert len(events) >= 1
    assert events[0]["event_id"] == event.event_id
    assert events[0]["source"] == "unit_test"


@pytest.mark.asyncio
async def test_event_bus_list_recent_events():
    bus = EventBus(redis_url="redis://nonexistent:9999/0")

    await bus.publish_event(
        topic="events.webhooks.github",
        data={"issue": "test_bug"},
        source="github_test",
    )
    await bus.publish_event(
        topic="events.mobile.webhook",
        data={"battery": 85},
        source="phone_test",
    )

    recent = await bus.list_recent_events(limit=10)
    assert len(recent) >= 2
    sources = [e.get("source") for e in recent]
    assert "github_test" in sources
    assert "phone_test" in sources

