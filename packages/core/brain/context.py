"""Context Engine for OmniBrain.

Assembles runtime context for LLM prompts: user profile, active capabilities,
recent history, and system time.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import User, Connection, Task
from packages.core.memory.store import get_memory_store

logger = logging.getLogger("omnibrain.brain.context")


class SystemContext:
    def __init__(
        self,
        user_name: str,
        user_email: str,
        timezone_str: str,
        current_time_iso: str,
        active_tools: List[str],
        recent_tasks: List[Dict[str, Any]],
        memories: Optional[List[Dict[str, Any]]] = None,
    ):
        self.user_name = user_name
        self.user_email = user_email
        self.timezone_str = timezone_str
        self.current_time_iso = current_time_iso
        self.active_tools = active_tools
        self.recent_tasks = recent_tasks
        self.memories = memories or []

    def to_system_prompt_snippet(self) -> str:
        """Format context into a concise markdown section for the LLM system prompt."""
        tools_list = ", ".join(self.active_tools) if self.active_tools else "None connected"
        tasks_summary = "\n".join(
            f"- [{t['status']}] {t['goal']}" for t in self.recent_tasks[:3]
        ) or "None"

        memory_section = ""
        if self.memories:
            mem_lines = "\n".join(
                f"- [{m.get('category', 'memory')}] {m.get('content')}"
                for m in self.memories
            )
            memory_section = f"\n### Relevant Memories & User Preferences\n{mem_lines}\n"

        return (
            f"### Current Context\n"
            f"- User: {self.user_name} ({self.user_email})\n"
            f"- Timezone: {self.timezone_str}\n"
            f"- Current Time: {self.current_time_iso}\n"
            f"- Connected Tools: {tools_list}\n"
            f"- Recent Tasks:\n{tasks_summary}\n"
            f"{memory_section}"
        )


class ContextEngine:
    """Gathers user state and available tool capabilities from the database."""

    async def assemble_context(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: Optional[str] = None,
    ) -> SystemContext:
        """Query user profile, active connections, recent tasks, and relevant long-term memories."""
        # 1. User
        user_res = await session.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        user_name = user.name if user else "User"
        user_email = user.email if user else "user@omnibrain.local"
        tz_str = user.timezone if user else "UTC"

        # 2. Connections
        conns_res = await session.execute(
            select(Connection).where(
                Connection.user_id == user_id,
                Connection.status == "ONLINE",
            )
        )
        conns = conns_res.scalars().all()
        active_tools = []
        for c in conns:
            if c.provider == "google":
                active_tools.extend(["Gmail", "Google Drive", "Google Calendar", "Google Sheets"])
            else:
                active_tools.append(c.provider.title())

        if not active_tools:
            # Default sandbox tools are always available in dev
            active_tools = ["Gmail (Sandbox)", "Google Drive (Sandbox)", "Google Calendar (Sandbox)", "Google Sheets (Sandbox)"]

        # 3. Recent tasks
        tasks_res = await session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(5)
        )
        recent_tasks = [
            {"goal": t.intent.get("goal", "Unknown"), "status": t.status}
            for t in tasks_res.scalars().all()
        ]

        # 4. Long-term memory & preferences retrieval
        memories = []
        try:
            mem_store = get_memory_store()
            if query:
                matches = await mem_store.search_memories(
                    session=session,
                    user_id=user_id,
                    query=query,
                    top_k=4,
                    min_similarity=0.15,
                )
                for mem, sim in matches:
                    memories.append({
                        "category": mem.category,
                        "content": mem.content,
                        "similarity": sim,
                    })

            # Also fetch persistent user preferences
            if len(memories) < 3:
                prefs = await mem_store.list_memories(
                    session=session,
                    user_id=user_id,
                    category="preference",
                    limit=3,
                )
                seen_content = {m.get("content") for m in memories}
                for p in prefs:
                    if p.content not in seen_content:
                        memories.append({
                            "category": p.category,
                            "content": p.content,
                        })
        except Exception as e:
            logger.warning(f"Error querying memories for context: {e}")

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        return SystemContext(
            user_name=user_name,
            user_email=user_email,
            timezone_str=tz_str,
            current_time_iso=now_iso,
            active_tools=active_tools,
            recent_tasks=recent_tasks,
            memories=memories,
        )

