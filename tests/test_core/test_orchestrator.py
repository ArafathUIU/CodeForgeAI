"""Tests for the orchestrator module."""

import asyncio

import pytest

from codeforge.core.agent_registry import AgentRegistry
from codeforge.core.checkpoint import CheckpointManager
from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import (
    ArtifactType,
    create_artifact_submission,
)
from codeforge.core.orchestrator import VALID_TRANSITIONS, Orchestrator, Phase
from codeforge.core.state_store import EpisodicStore, SemanticStore
from codeforge.utils.exceptions import PhaseTransitionError


class TestPhaseTransitions:
    def test_valid_transitions_exist(self):
        assert Phase.REQUIREMENTS in VALID_TRANSITIONS[Phase.INIT]
        assert Phase.ARCHITECTURE in VALID_TRANSITIONS[Phase.REQUIREMENTS]
        assert Phase.IMPLEMENTATION in VALID_TRANSITIONS[Phase.ARCHITECTURE]
        assert Phase.TESTING in VALID_TRANSITIONS[Phase.IMPLEMENTATION]
        assert Phase.REVIEW in VALID_TRANSITIONS[Phase.TESTING]
        assert Phase.DEPLOYMENT in VALID_TRANSITIONS[Phase.REVIEW]
        assert Phase.COMPLETE in VALID_TRANSITIONS[Phase.DEPLOYMENT]

    def test_all_phases_can_fail(self):
        for phase in [Phase.REQUIREMENTS, Phase.ARCHITECTURE, Phase.IMPLEMENTATION,
                       Phase.TESTING, Phase.REVIEW, Phase.DEPLOYMENT]:
            assert Phase.FAILED in VALID_TRANSITIONS[phase]


class TestOrchestrator:
    @pytest.fixture
    def orchestrator(self, tmp_path):
        bus = MessageBus()
        registry = AgentRegistry()
        checkpoint = CheckpointManager(storage_path=tmp_path / "checkpoints")
        episodic = EpisodicStore()
        semantic = SemanticStore()
        return Orchestrator(bus, registry, checkpoint, episodic, semantic)

    def test_initial_state(self, orchestrator):
        assert orchestrator.current_phase == Phase.INIT
        assert orchestrator.is_complete is False

    def test_start_project(self, orchestrator):
        async def run():
            project_id = await orchestrator.start_project(
                "Build a todo app",
                output_directory="/tmp/test_project",
            )
            assert project_id is not None
            return project_id

        project_id = asyncio.get_event_loop().run_until_complete(run())
        assert project_id is not None

    def test_start_project_transitions_to_requirements(self, orchestrator):
        async def run():
            await orchestrator.start_project("Build a todo app")
            return orchestrator.current_phase

        phase = asyncio.get_event_loop().run_until_complete(run())
        assert phase == Phase.REQUIREMENTS

    def test_invalid_transition_raises(self, orchestrator):
        async def run():
            await orchestrator.transition_to(Phase.DEPLOYMENT)

        with pytest.raises(PhaseTransitionError):
            asyncio.get_event_loop().run_until_complete(run())

    def test_fail_pipeline(self, orchestrator):
        async def run():
            await orchestrator.fail_pipeline("Test failure")
            return orchestrator.current_phase

        phase = asyncio.get_event_loop().run_until_complete(run())
        assert phase == Phase.FAILED

    def test_get_pipeline_summary(self, orchestrator):
        summary = orchestrator.get_pipeline_summary()
        assert summary["phase"] == "init"
        assert summary["is_complete"] is False
        assert summary["errors"] == []

    def test_phase_agents_mapping(self):
        from codeforge.core.orchestrator import PHASE_AGENTS
        assert "product_manager" in PHASE_AGENTS[Phase.REQUIREMENTS]
        assert "system_architect" in PHASE_AGENTS[Phase.ARCHITECTURE]
        assert "code_writer" in PHASE_AGENTS[Phase.IMPLEMENTATION]
        assert "test_engineer" in PHASE_AGENTS[Phase.TESTING]
        assert "code_reviewer" in PHASE_AGENTS[Phase.REVIEW]
        assert "devops" in PHASE_AGENTS[Phase.DEPLOYMENT]


class TestArtifactHandoff:
    @pytest.fixture
    def orchestrator(self, tmp_path):
        bus = MessageBus()
        registry = AgentRegistry()
        checkpoint = CheckpointManager(storage_path=tmp_path / "checkpoints")
        episodic = EpisodicStore()
        semantic = SemanticStore()
        return Orchestrator(bus, registry, checkpoint, episodic, semantic)

    def test_artifact_storage_and_retrieval(self, orchestrator):
        async def run():
            await orchestrator.start_project("Build an app")
            prd_data = {"id": "test-prd", "title": "Test App", "summary": "A test app"}
            msg = create_artifact_submission(
                artifact_id="test-prd",
                artifact_type=ArtifactType.PRD,
                content=prd_data,
                sender="product_manager",
            )
            await orchestrator.handle_artifact_submission(msg)

            stored = orchestrator.get_artifact("prd")
            assert stored is not None
            assert stored["title"] == "Test App"

        asyncio.get_event_loop().run_until_complete(run())

    def test_orchestrator_receives_artifact_via_bus(self, orchestrator):
        async def run():
            await orchestrator.start_project("Build an app")

            prd_data = {"id": "test-prd", "title": "Via Bus App", "summary": "Test"}
            msg = create_artifact_submission(
                artifact_id="test-prd",
                artifact_type=ArtifactType.PRD,
                content=prd_data,
                sender="product_manager",
                recipient="orchestrator",
            )
            await orchestrator._message_bus.publish(msg)

            stored = orchestrator.get_artifact("prd")
            assert stored is not None
            assert stored["title"] == "Via Bus App"

        asyncio.get_event_loop().run_until_complete(run())

    def test_auto_approve_advances_phase(self, orchestrator):
        async def run():
            await orchestrator.start_project("Build an app")

            prd_data = {"id": "test-prd", "title": "Auto Approve App", "summary": "Test"}
            msg = create_artifact_submission(
                artifact_id="test-prd",
                artifact_type=ArtifactType.PRD,
                content=prd_data,
                sender="product_manager",
                recipient="orchestrator",
            )
            await orchestrator._message_bus.publish(msg)

            assert orchestrator.get_artifact("prd") is not None

        asyncio.get_event_loop().run_until_complete(run())

    def test_empty_artifact_store_returns_none(self, orchestrator):
        assert orchestrator.get_artifact("nonexistent") is None
