"""Redis Streams Event Bus for OmniBrain.

Provides decoupled, high-throughput asynchronous event publishing and streaming
with fallback to in-memory buffers for local testing.
"""
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

import redis.asyncio as aioredis
from pydantic import BaseModel, Field

from apps.api.settings import get_settings

logger = logging.getLogger("omnibrain.events.bus")


class EventPayload(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    source: str = "system"
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EventBus:
    """Pub/Sub & Event Streaming Bus backed by Redis Streams."""

    def __init__(self, redis_url: Optional[str] = None):
        self.settings = get_settings()
        self.redis_url = redis_url or self.settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._in_memory_streams: Dict[str, List[Dict[str, Any]]] = {}

    async def _get_client(self) -> Optional[aioredis.Redis]:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                )
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}), using in-memory event stream fallback.")
                self._redis = None
        return self._redis

    async def publish_event(
        self,
        topic: str,
        data: Dict[str, Any],
        source: str = "system",
    ) -> EventPayload:
        """Publish an event to a specific stream topic."""
        event = EventPayload(
            topic=topic,
            source=source,
            data=data,
        )

        client = await self._get_client()
        if client:
            try:
                await client.xadd(
                    topic,
                    {
                        "event_id": event.event_id,
                        "source": event.source,
                        "data": json.dumps(event.data),
                        "timestamp": event.timestamp,
                    },
                    maxlen=1000,
                )
                return event
            except Exception as e:
                logger.error(f"Failed to publish to Redis stream {topic}: {e}")

        # In-memory fallback
        stream = self._in_memory_streams.setdefault(topic, [])
        stream.append({
            "event_id": event.event_id,
            "topic": topic,
            "source": event.source,
            "data": event.data,
            "timestamp": event.timestamp,
        })
        if len(stream) > 500:
            self._in_memory_streams[topic] = stream[-500:]

        return event

    async def read_events(
        self,
        topic: str,
        count: int = 20,
    ) -> List[Dict[str, Any]]:
        """Read latest events from a stream topic."""
        client = await self._get_client()
        if client:
            try:
                # xrevrange gets newest events first
                raw_events = await client.xrevrange(topic, max="+", min="-", count=count)
                events = []
                for msg_id, fields in raw_events:
                    try:
                        data_dict = json.loads(fields.get("data", "{}"))
                    except Exception:
                        data_dict = fields.get("data", {})

                    events.append({
                        "msg_id": msg_id,
                        "event_id": fields.get("event_id"),
                        "topic": topic,
                        "source": fields.get("source"),
                        "data": data_dict,
                        "timestamp": fields.get("timestamp"),
                    })
                return events
            except Exception as e:
                logger.warning(f"Error reading Redis stream {topic}: {e}")

        # In-memory fallback
        mem_stream = self._in_memory_streams.get(topic, [])
        return list(reversed(mem_stream[-count:]))

    async def list_recent_events(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Collect recent events across all common topics."""
        common_topics = [
            "events.webhooks.github",
            "events.webhooks.slack",
            "events.webhooks.custom",
            "events.mobile.webhook",
            "events.workflow.triggered",
            "events.system.alert",
        ]
        all_events = []
        for topic in common_topics:
            topic_events = await self.read_events(topic=topic, count=10)
            all_events.extend(topic_events)

        all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_events[:limit]

