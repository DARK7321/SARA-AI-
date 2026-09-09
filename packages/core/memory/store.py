"""Memory Store for OmniBrain Long-Term Vector Memory.

Provides semantic search, persistence, and categorization of user preferences,
facts, and historical context using PostgreSQL pgvector.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import Memory
from packages.core.memory.embeddings import get_embedding_service

logger = logging.getLogger("omnibrain.memory.store")


class MemoryStore:
    """Vector-backed memory storage and retrieval engine."""

    def __init__(self):
        self.embedding_service = get_embedding_service()

    async def store_memory(
        self,
        session: AsyncSession,
        user_id: UUID,
        content: str,
        category: str = "fact",
        confidence: float = 1.0,
        source: str = "user_stated",
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """Embed and persist a new memory record."""
        clean_content = content.strip()
        embedding = await self.embedding_service.get_embedding(clean_content)

        memory = Memory(
            user_id=user_id,
            category=category,
            content=clean_content,
            embedding=embedding,
            confidence=confidence,
            source=source,
            metadata_json=metadata_json or {},
        )
        session.add(memory)
        await session.flush()
        return memory

    async def search_memories(
        self,
        session: AsyncSession,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.1,
    ) -> List[Tuple[Memory, float]]:
        """Semantic similarity search against stored memories using cosine distance."""
        clean_query = query.strip()
        if not clean_query:
            return []

        query_embedding = await self.embedding_service.get_embedding(clean_query)

        # In pgvector: cosine distance ranges from 0 (identical) to 2 (opposite)
        # Cosine similarity = 1.0 - cosine_distance
        distance_col = Memory.embedding.cosine_distance(query_embedding).label("distance")

        stmt = select(Memory, distance_col).where(
            Memory.user_id == user_id,
            Memory.embedding.is_not(None),
        )

        if category:
            stmt = stmt.where(Memory.category == category)

        stmt = stmt.order_by(distance_col.asc()).limit(top_k)

        result = await session.execute(stmt)
        matches = []
        for mem, dist in result.all():
            similarity = max(0.0, 1.0 - float(dist))
            if similarity >= min_similarity:
                matches.append((mem, round(similarity, 4)))

        return matches

    async def list_memories(
        self,
        session: AsyncSession,
        user_id: UUID,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Memory]:
        """Fetch recent memories chronologically."""
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        if category:
            stmt = stmt.where(Memory.category == category)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_memory(
        self,
        session: AsyncSession,
        user_id: UUID,
        memory_id: UUID,
    ) -> bool:
        """Delete a memory item by ID."""
        stmt = delete(Memory).where(
            Memory.id == memory_id,
            Memory.user_id == user_id,
        )
        res = await session.execute(stmt)
        return res.rowcount > 0


_default_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Singleton getter for MemoryStore."""
    global _default_memory_store
    if _default_memory_store is None:
        _default_memory_store = MemoryStore()
    return _default_memory_store

