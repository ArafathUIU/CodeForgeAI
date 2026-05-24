"""Session manager for the CodeForge pipeline.

Manages the lifecycle of orchestrator instances, agent registration,
and shared state for the dashboard API.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from codeforge.agents.code_reviewer.agent import CodeReviewerAgent
from codeforge.agents.code_writer.agent import CodeWriterAgent
from codeforge.agents.devops.agent import DevOpsAgent
from codeforge.agents.product_manager.agent import ProductManagerAgent
from codeforge.agents.system_architect.agent import SystemArchitectAgent
from codeforge.agents.test_engineer.agent import TestEngineerAgent
from codeforge.core.agent_registry import AgentRegistry
from codeforge.core.checkpoint import CheckpointManager
from codeforge.core.llm_client import LlmClient
from codeforge.core.message_bus import MessageBus
from codeforge.core.orchestrator import Orchestrator
from codeforge.core.state_store import EpisodicStore, SemanticStore
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionState:
    project_id: str = ""
    specification: str = ""
    output_dir: str = ""
    phase: str = "init"
    started_at: str = ""
    errors: list[str] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    artifacts: dict[str, dict] = field(default_factory=dict)
    agents: list[dict] = field(default_factory=list)


class PipelineSession:
    def __init__(self, storage_path: str = ".codeforge"):
        self._bus = MessageBus()
        self._episodic = EpisodicStore()
        self._semantic = SemanticStore()
        self._registry = AgentRegistry()
        self._checkpoint_mgr = CheckpointManager(storage_path=storage_path)
        self._orchestrator = Orchestrator(
            self._bus, self._registry, self._checkpoint_mgr,
            self._episodic, self._semantic,
        )
        self._messages: list[dict] = []
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

        try:
            from codeforge.utils.config import get_config
            self._llm = LlmClient(get_config().llm)
        except Exception:
            self._llm = None

        self._bus.subscribe("all", self._capture_message)

    def _capture_message(self, message) -> None:
        msg_type = getattr(message, "type", "")
        type_str = msg_type.value if hasattr(msg_type, "value") else str(msg_type)
        self._messages.append({
            "id": getattr(message, "id", ""),
            "type": type_str,
            "sender": getattr(message, "sender", ""),
            "recipient": getattr(message, "recipient", ""),
            "payload": dict(getattr(message, "payload", {})),
            "timestamp": str(getattr(message, "timestamp", "")),
        })
        if len(self._messages) > 500:
            self._messages = self._messages[-300:]

    def register_agents(self, output_dir: str = "") -> None:
        pm = ProductManagerAgent(
            agent_id="product_manager", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            llm_client=self._llm,
        )
        sa = SystemArchitectAgent(
            agent_id="system_architect", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            llm_client=self._llm,
        )
        cw = CodeWriterAgent(
            agent_id="code_writer", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            output_dir=output_dir,
        )
        te = TestEngineerAgent(
            agent_id="test_engineer", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            output_dir=output_dir,
        )
        cr = CodeReviewerAgent(
            agent_id="code_reviewer", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
        )
        ops = DevOpsAgent(
            agent_id="devops", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            output_dir=output_dir,
        )

        for agent in [pm, sa, cw, te, cr, ops]:
            self._registry.register(agent)
            self._bus.register_agent(agent.agent_id, agent.handle_message)

    async def start(self, specification: str, output_dir: str = "") -> str:
        output_dir = output_dir or ".codeforge/output"
        self.register_agents(output_dir)
        project_id = await self._orchestrator.start_project(specification, output_dir)
        return project_id

    def get_state(self) -> dict[str, Any]:
        summary = self._orchestrator.get_pipeline_summary()
        agents_status = self._registry.get_status_report()
        return {
            "project_id": summary.get("project_id", ""),
            "phase": summary.get("phase", "init"),
            "is_complete": summary.get("is_complete", False),
            "errors": summary.get("errors", []),
            "approval_gates": summary.get("approval_gates", []),
            "agents": agents_status.get("agents", []),
            "agent_summary": agents_status.get("by_state", {}),
            "artifacts": self._orchestrator._artifacts,
            "messages": self._messages[-50:],
            "message_count": len(self._messages),
        }

    def run_sync(self, specification: str, output_dir: str = "") -> dict:
        async def _run():
            await self.start(specification, output_dir)
            return self.get_state()

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
