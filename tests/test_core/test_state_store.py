"""Tests for the state store (episodic, semantic, context digest)."""

import pytest

from codeforge.core.state_store import (
    ContextDigestBuilder,
    EpisodicStore,
    SemanticStore,
)
from codeforge.utils.exceptions import StateNotFoundError


class TestEpisodicStore:
    def test_add_and_get_entry(self):
        store = EpisodicStore()
        store.add("e1", "decision", {"key": "value"}, agent_id="pm", phase="requirements")
        retrieved = store.get("e1")
        assert retrieved.id == "e1"
        assert retrieved.type == "decision"
        assert retrieved.content == {"key": "value"}
        assert retrieved.agent_id == "pm"

    def test_get_nonexistent_raises(self):
        store = EpisodicStore()
        with pytest.raises(StateNotFoundError):
            store.get("nonexistent")

    def test_query_by_type(self):
        store = EpisodicStore()
        store.add("e1", "decision", {})
        store.add("e2", "artifact", {})
        store.add("e3", "decision", {})
        results = store.query(entry_type="decision")
        assert len(results) == 2

    def test_query_by_agent(self):
        store = EpisodicStore()
        store.add("e1", "type1", {}, agent_id="pm")
        store.add("e2", "type2", {}, agent_id="architect")
        results = store.query(agent_id="pm")
        assert len(results) == 1
        assert results[0].id == "e1"

    def test_query_by_phase(self):
        store = EpisodicStore()
        store.add("e1", "x", {}, phase="requirements")
        store.add("e2", "x", {}, phase="implementation")
        results = store.query(phase="requirements")
        assert len(results) == 1

    def test_query_by_tags(self):
        store = EpisodicStore()
        store.add("e1", "x", {}, tags=["important", "urgent"])
        store.add("e2", "x", {}, tags=["routine"])
        results = store.query(tags=["important"])
        assert len(results) == 1

    def test_get_all_sorted_newest_first(self):
        store = EpisodicStore()
        store.add("e1", "x", {})
        store.add("e2", "x", {})
        all_entries = store.get_all()
        assert len(all_entries) == 2
        assert all_entries[0].timestamp >= all_entries[1].timestamp

    def test_delete_entry(self):
        store = EpisodicStore()
        store.add("e1", "x", {})
        store.delete("e1")
        with pytest.raises(StateNotFoundError):
            store.get("e1")

    def test_serialize_roundtrip(self):
        store = EpisodicStore()
        store.add("e1", "type1", {"key": "val"}, agent_id="pm")
        data = store.to_dict()
        restored = EpisodicStore.from_dict(data)
        assert restored.get("e1").content == {"key": "val"}


class TestSemanticStore:
    def test_add_and_get(self):
        store = SemanticStore()
        store.add("s1", "FastAPI for async", "Use FastAPI for async APIs", "technology")
        retrieved = store.get("s1")
        assert retrieved.pattern == "FastAPI for async"

    def test_query_by_category(self):
        store = SemanticStore()
        store.add("s1", "p1", "d1", "technology")
        store.add("s2", "p2", "d2", "style")
        results = store.query(category="technology")
        assert len(results) == 1

    def test_search_keyword(self):
        store = SemanticStore()
        store.add("s1", "React for frontend", "Use React", "technology")
        store.add("s2", "FastAPI for backend", "Use FastAPI", "technology")
        results = store.search("react")
        assert len(results) == 1

    def test_increment_usage(self):
        store = SemanticStore()
        store.add("s1", "p1", "d1", "tech")
        store.increment_usage("s1")
        assert store.get("s1").usage_count == 1

    def test_serialize_roundtrip(self):
        store = SemanticStore()
        store.add("s1", "p1", "d1", "tech", confidence=0.8)
        data = store.to_dict()
        restored = SemanticStore.from_dict(data)
        assert restored.get("s1").confidence == 0.8


class TestContextDigestBuilder:
    def test_build_episodic_digest(self):
        episodic = EpisodicStore()
        semantic = SemanticStore()
        builder = ContextDigestBuilder(episodic, semantic)

        episodic.add("e1", "decision", {"topic": "database"})
        digest = builder.build_episodic_digest()

        assert "decision" in digest
        assert "database" in digest

    def test_build_episodic_digest_with_no_entries(self):
        episodic = EpisodicStore()
        semantic = SemanticStore()
        builder = ContextDigestBuilder(episodic, semantic)

        digest = builder.build_episodic_digest()
        assert "No relevant" in digest

    def test_build_semantic_digest(self):
        episodic = EpisodicStore()
        semantic = SemanticStore()
        builder = ContextDigestBuilder(episodic, semantic)

        semantic.add("s1", "Use SQLite", "SQLite for dev", "technology")
        digest = builder.build_semantic_digest()

        assert "Use SQLite" in digest

    def test_build_full_digest(self):
        episodic = EpisodicStore()
        semantic = SemanticStore()
        builder = ContextDigestBuilder(episodic, semantic)

        episodic.add("e1", "decision", {"x": 1})
        digest = builder.build_full_digest()
        assert "Project History" in digest
