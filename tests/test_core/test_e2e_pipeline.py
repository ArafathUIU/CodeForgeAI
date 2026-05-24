"""End-to-end integration test for the full CodeForge pipeline."""

import asyncio
import os
import tempfile


class TestEndToEndPipeline:
    def test_session_creates_all_agents(self):
        from codeforge.api.session import PipelineSession

        with tempfile.TemporaryDirectory() as tmpdir:
            session = PipelineSession(storage_path=os.path.join(tmpdir, ".codeforge"))
            session.register_agents(output_dir=os.path.join(tmpdir, "out"))
            state = session.get_state()
            agents = state.get("agents", [])
            assert len(agents) >= 6

    def test_start_project_initializes_pipeline(self):
        from codeforge.api.session import PipelineSession

        async def run():
            with tempfile.TemporaryDirectory() as tmpdir:
                session = PipelineSession(storage_path=os.path.join(tmpdir, ".codeforge"))
                pid = await session.start(
                    "Build a todo app",
                    output_dir=os.path.join(tmpdir, "output"),
                )
                assert pid
                state = session.get_state()
                assert state["phase"] in ("requirements", "architecture",
                                          "implementation", "init")
                assert state["message_count"] > 0
                return pid

        pid = asyncio.get_event_loop().run_until_complete(run())
        assert pid

    def test_full_pipeline_flow(self):
        from codeforge.api.session import PipelineSession

        async def run():
            with tempfile.TemporaryDirectory() as tmpdir:
                out = os.path.join(tmpdir, "output")
                session = PipelineSession(storage_path=os.path.join(tmpdir, ".codeforge"))
                pid = await session.start("Build a todo app", output_dir=out)

                state = session.get_state()
                assert state["message_count"] > 0
                assert state["agents"] or state["agent_summary"]

                messages = state.get("messages", [])
                artifact_msgs = [m for m in messages if "artifact" in m.get("type", "")]
                task_msgs = [m for m in messages if "task" in m.get("type", "")]

                return {
                    "project_id": pid,
                    "phase": state["phase"],
                    "artifacts": len(artifact_msgs),
                    "tasks": len(task_msgs),
                }

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["project_id"]
        assert result["phase"] != "failed"

    def test_agent_registration_and_communication(self):
        from codeforge.agents.product_manager.agent import ProductManagerAgent
        from codeforge.core.agent_registry import AgentRegistry
        from codeforge.core.message_bus import MessageBus
        from codeforge.core.message_protocol import (
            MessageType,
            create_task_assignment,
        )
        from codeforge.core.state_store import EpisodicStore, SemanticStore

        bus = MessageBus()
        registry = AgentRegistry()
        episodic = EpisodicStore()
        semantic = SemanticStore()

        pm = ProductManagerAgent(
            agent_id="pm-test",
            message_bus=bus,
            episodic_store=episodic,
            semantic_store=semantic,
        )
        registry.register(pm)
        bus.register_agent("pm-test", pm.handle_message)

        artifacts_received = []

        async def capture(m):
            artifacts_received.append(m)

        bus.subscribe("orchestrator", capture)

        async def run():
            await pm.initialize()
            msg = create_task_assignment(
                task_id="task-1",
                description="Build a todo app",
                agent_role="product_manager",
                sender="orchestrator",
                recipient="pm-test",
                context={"specification": "Build a todo app"},
            )
            await pm.handle_message(msg)

            assert len(artifacts_received) > 0
            art = [m for m in artifacts_received
                   if m.type == MessageType.ARTIFACT_SUBMISSION][0]
            assert art.type == MessageType.ARTIFACT_SUBMISSION

        asyncio.get_event_loop().run_until_complete(run())
