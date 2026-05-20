"""Tests for the conflict resolver module."""

import asyncio

import pytest

from codeforge.core.conflict_resolver import (
    ConflictClassifier,
    ConflictResolver,
    ConflictType,
    ResolutionStrategy,
)
from codeforge.core.state_store import EpisodicStore


class TestConflictClassifier:
    def test_classify_security(self):
        result = ConflictClassifier.classify("The password is stored in plaintext")
        assert result == ConflictType.SECURITY

    def test_classify_performance(self):
        result = ConflictClassifier.classify("This has an N+1 query performance issue")
        assert result == ConflictType.PERFORMANCE

    def test_classify_architecture(self):
        result = ConflictClassifier.classify(
            "The architecture pattern should use dependency injection"
        )
        assert result == ConflictType.ARCHITECTURE

    def test_classify_style(self):
        result = ConflictClassifier.classify("Line length exceeds PEP 8 style guide")
        assert result == ConflictType.STYLE

    def test_classify_naming(self):
        result = ConflictClassifier.classify("Function name doesn't match naming convention")
        assert result == ConflictType.NAMING

    def test_classify_dependency(self):
        result = ConflictClassifier.classify("Package dependency version is incompatible")
        assert result == ConflictType.DEPENDENCY

    def test_classify_other_as_fallback(self):
        result = ConflictClassifier.classify("Some random issue")
        assert result == ConflictType.OTHER

    def test_classify_from_details(self):
        result = ConflictClassifier.classify(
            "Issue found",
            details={"vulnerability_type": "sql injection"},
        )
        assert result == ConflictType.SECURITY


class TestConflictResolver:
    @pytest.fixture
    def resolver(self):
        episodic = EpisodicStore()
        return ConflictResolver(episodic)

    def test_register_conflict(self, resolver):
        conflict = resolver.register_conflict(
            conflict_type=ConflictType.STYLE,
            agent_a="pm",
            agent_b="architect",
            description="Line length conflict",
        )
        assert conflict.agent_a == "pm"
        assert conflict.status == "unresolved"

    def test_resolve_security_conflict(self, resolver):
        async def run():
            conflict = resolver.register_conflict(
                conflict_type=ConflictType.SECURITY,
                agent_a="reviewer",
                agent_b="writer",
                description="SQL injection found",
                details={"priority_a": 10, "priority_b": 0},
            )
            resolved = await resolver.resolve(conflict)
            return resolved

        resolved = asyncio.get_event_loop().run_until_complete(run())
        assert resolved.status == "resolved"
        assert resolved.resolution_strategy == ResolutionStrategy.HIGHER_PRIORITY_WINS

    def test_auto_resolve_style_conflict(self, resolver):
        async def run():
            conflict = resolver.register_conflict(
                conflict_type=ConflictType.STYLE,
                agent_a="pm",
                agent_b="writer",
                description="Inconsistent indentation",
            )
            resolved = await resolver.resolve(conflict)
            return resolved

        resolved = asyncio.get_event_loop().run_until_complete(run())
        assert resolved.status == "resolved"
        assert resolved.resolution_strategy == ResolutionStrategy.AUTO_RESOLVE

    def test_escalate_architecture_conflict(self, resolver):
        async def run():
            conflict = resolver.register_conflict(
                conflict_type=ConflictType.ARCHITECTURE,
                agent_a="writer",
                agent_b="reviewer",
                description="Architecture pattern disagreement",
                details={"role_a": "code_writer", "role_b": "code_reviewer"},
            )
            resolved = await resolver.resolve(conflict)
            return resolved

        resolved = asyncio.get_event_loop().run_until_complete(run())
        assert resolved.status == "escalated"
        assert resolved.resolution_strategy == ResolutionStrategy.ESCALATE_TO_HUMAN

    def test_get_unresolved(self, resolver):
        resolver.register_conflict(
            conflict_type=ConflictType.STYLE,
            agent_a="a",
            agent_b="b",
            description="test",
        )
        unresolved = resolver.get_unresolved()
        assert len(unresolved) == 1

    def test_get_summary(self, resolver):
        async def run():
            c1 = resolver.register_conflict(ConflictType.STYLE, "a", "b", "test1")
            resolver.register_conflict(ConflictType.STYLE, "c", "d", "test2")
            await resolver.resolve(c1)
            return resolver.get_summary()

        summary = asyncio.get_event_loop().run_until_complete(run())
        assert summary["total_conflicts"] == 2
        assert summary["resolved"] >= 1

    def test_resolution_log_tracks_resolutions(self, resolver):
        async def run():
            conflict = resolver.register_conflict(ConflictType.STYLE, "a", "b", "test")
            await resolver.resolve(conflict)
            log = resolver.get_resolution_log()
            return log

        log = asyncio.get_event_loop().run_until_complete(run())
        assert len(log) >= 1
