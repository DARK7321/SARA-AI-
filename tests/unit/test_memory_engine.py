"""Unit tests for OmniBrain Long-Term Vector Memory Engine."""
import pytest
from uuid import uuid4

from packages.core.db.models import User, Memory
from packages.core.memory.embeddings import compute_fallback_embedding, get_embedding_service, EMBEDDING_DIM
from packages.core.memory.store import MemoryStore
from packages.core.brain.context import ContextEngine


def test_fallback_embedding_generation():
    """Verify fallback embedding generates a normalized 768-dim vector."""
    vec = compute_fallback_embedding("User prefers responses in Hindi and Hinglish")
    assert len(vec) == EMBEDDING_DIM
    # Check unit vector normalization
    magnitude = sum(x * x for x in vec) ** 0.5
    assert abs(magnitude - 1.0) < 1e-4

    # Empty string produces zero vector
    zero_vec = compute_fallback_embedding("")
    assert len(zero_vec) == EMBEDDING_DIM
    assert sum(zero_vec) == 0.0


@pytest.mark.asyncio
async def test_memory_store_lifecycle(db_session, test_user):
    """Test storing, searching, and deleting memories via MemoryStore."""
    from sqlalchemy import delete
    await db_session.execute(delete(Memory).where(Memory.user_id == test_user.id))
    await db_session.flush()

    store = MemoryStore()

    # 1. Store preference
    mem1 = await store.store_memory(
        session=db_session,
        user_id=test_user.id,
        content="User prefers communications in Hindi with respectful tone",
        category="preference",
        confidence=0.95,
        source="user_stated",
    )
    assert mem1.id is not None
    assert mem1.category == "preference"

    # 2. Store fact
    mem2 = await store.store_memory(
        session=db_session,
        user_id=test_user.id,
        content="Primary project is OmniBrain AI operating system",
        category="fact",
        confidence=1.0,
    )
    assert mem2.id is not None

    # 3. Search memories with relevant query
    matches = await store.search_memories(
        session=db_session,
        user_id=test_user.id,
        query="What language does the user prefer?",
        top_k=2,
    )
    assert len(matches) > 0
    top_mem, similarity = matches[0]
    assert top_mem.category == "preference"
    assert "Hindi" in top_mem.content
    assert similarity > 0.1

    # 4. Search with category filter
    fact_matches = await store.search_memories(
        session=db_session,
        user_id=test_user.id,
        query="OmniBrain system",
        category="fact",
    )
    assert len(fact_matches) > 0
    assert all(m.category == "fact" for m, _ in fact_matches)

    # 5. List memories
    all_mems = await store.list_memories(session=db_session, user_id=test_user.id)
    assert len(all_mems) >= 2

    # 6. Delete memory
    deleted = await store.delete_memory(session=db_session, user_id=test_user.id, memory_id=mem1.id)
    assert deleted is True

    remaining = await store.list_memories(session=db_session, user_id=test_user.id)
    assert not any(m.id == mem1.id for m in remaining)


@pytest.mark.asyncio
async def test_context_engine_memory_injection(db_session, test_user):
    """Verify ContextEngine includes relevant memories in system prompt snippet."""
    from sqlalchemy import delete
    await db_session.execute(delete(Memory).where(Memory.user_id == test_user.id))
    await db_session.flush()

    store = MemoryStore()
    await store.store_memory(
        session=db_session,
        user_id=test_user.id,
        content="Client Acme Corp requires weekly progress report on Friday",
        category="fact",
    )

    context_engine = ContextEngine()
    sys_ctx = await context_engine.assemble_context(
        session=db_session,
        user_id=test_user.id,
        query="progress report for Acme Corp",
    )

    assert len(sys_ctx.memories) > 0
    snippet = sys_ctx.to_system_prompt_snippet()
    assert "Relevant Memories" in snippet
    assert "Acme Corp" in snippet
