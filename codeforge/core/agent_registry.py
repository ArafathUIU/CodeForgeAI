"""Agent base class and registry for the CodeForge agent system.

Provides the abstract base class that all agents must implement,
along with a registry for discoverability, lifecycle management,
and health monitoring.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import Message, MessageType, Priority
from codeforge.core.state_store import ContextDigestBuilder, EpisodicStore, SemanticStore
from codeforge.utils.config import get_config
from codeforge.utils.exceptions import AgentNotFoundError, AgentTimeoutError
from codeforge.utils.logging import get_agent_logger, get_logger

logger = get_logger(__name__)


class AgentState(StrEnum):
    INITIALIZED = "initialized"
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    BLOCKED = "blocked"
    ERROR = "error"
    TERMINATED = "terminated"


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    artifact_type: str = ""
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deadline: datetime | None = None
    status: str = "pending"


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        episodic_store: EpisodicStore | None = None,
        semantic_store: SemanticStore | None = None,
    ):
        self._agent_id = agent_id
        self._message_bus = message_bus
        self._state = AgentState.INITIALIZED
        self._progress = 0.0
        self._current_task: AgentTask | None = None
        self._task_history: list[AgentTask] = []
        self._started_at: datetime | None = None

        self._episodic_store = episodic_store
        self._semantic_store = semantic_store
        self._digest_builder: ContextDigestBuilder | None = None

        if episodic_store and semantic_store:
            self._digest_builder = ContextDigestBuilder(episodic_store, semantic_store)

        self._log = get_agent_logger(agent_id)
        self._log.info(f"Agent initialized: {agent_id}")

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> str:
        return type(self).__name__.lower()

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def current_task(self) -> AgentTask | None:
        return self._current_task

    def get_context_digest(self, phase: str = "") -> str:
        if self._digest_builder:
            return self._digest_builder.build_full_digest(
                phase=phase,
                agent_id=self._agent_id,
            )
        return ""

    async def initialize(self) -> None:
        self._state = AgentState.IDLE
        self._log.info("Agent ready")

    @abstractmethod
    async def process_message(self, message: Message) -> None:
        pass

    async def handle_message(self, message: Message) -> None:
        if message.is_expired():
            self._log.warning(f"Ignoring expired message: {message.id}")
            return

        timeout = get_config().agent.timeout_seconds

        try:
            self._state = AgentState.WORKING
            self._started_at = datetime.now(UTC)
            self._progress = 0.0

            await asyncio.wait_for(
                self.process_message(message),
                timeout=timeout,
            )

            self._progress = 1.0
            self._state = AgentState.IDLE

        except TimeoutError:
            self._state = AgentState.ERROR
            raise AgentTimeoutError(
                f"Agent {self._agent_id} timed out after {timeout}s",
                code="AGENT_TIMEOUT",
            )
        except Exception as e:
            self._state = AgentState.ERROR
            self._log.error(f"Agent error: {e}")
            raise

    async def send_message(self, message: Message) -> None:
        await self._message_bus.publish(message)
        self._log.debug(f"Sent {message.type.value} to {message.recipient}")

    async def send_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        content: dict[str, Any],
        version: str = "1.0",
    ) -> None:
        from codeforge.core.message_protocol import create_artifact_submission

        message = create_artifact_submission(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=content,
            version=version,
            sender=self._agent_id,
        )
        await self.send_message(message)

    async def request_clarification(self, question: str, context: str) -> None:
        from codeforge.core.message_protocol import create_clarification_request

        message = create_clarification_request(
            question=question,
            context=context,
            sender=self._agent_id,
        )
        await self.send_message(message)
        self._state = AgentState.WAITING

    async def report_blockage(self, reason: str, blocked_by: str) -> None:
        message = Message(
            sender=self._agent_id,
            recipient="orchestrator",
            type=MessageType.BLOCKAGE_REPORT,
            payload={
                "blockage_reason": reason,
                "blocked_by": blocked_by,
                "suggestions": [],
            },
            priority=Priority.HIGH,
        )
        await self.send_message(message)
        self._state = AgentState.BLOCKED

    async def discuss_with(
        self,
        target_agent: str,
        thought: str,
        reasoning: str = "",
        plan_snippet: str = "",
        decision: str = "",
    ) -> None:
        """Send a natural collaboration note to another agent."""
        final_thought = thought
        if hasattr(self, "generate_collab_message"):
            context = f"Thought: {thought}\nReasoning: {reasoning}\nPlan: {plan_snippet}"
            natural = await self.generate_collab_message(
                my_role=self.role,
                target_role=target_agent,
                context=context,
            )
            if natural:
                final_thought = natural
        message = Message(
            sender=self._agent_id,
            recipient=target_agent,
            type=MessageType.COLLABORATION_NOTE,
            payload={
                "thought": final_thought,
                "mentions": [target_agent],
                "reasoning": reasoning,
                "plan_snippet": plan_snippet,
                "decision": decision,
            },
            priority=Priority.NORMAL,
        )
        await self.send_message(message)

    async def announce_to_group(self, thought: str, reasoning: str = "") -> None:
        """Broadcast a decision or insight to all agents."""
        for agent_id in ("product_manager", "system_architect", "code_writer",
                         "test_engineer", "code_reviewer", "devops"):
            if agent_id != self._agent_id:
                message = Message(
                    sender=self._agent_id,
                    recipient=agent_id,
                    type=MessageType.COLLABORATION_NOTE,
                    payload={
                        "thought": thought,
                        "mentions": [agent_id],
                        "reasoning": reasoning,
                    },
                    priority=Priority.NORMAL,
                )
                await self.send_message(message)

    async def update_status(
        self, status: str, progress: float = 0.0, thinking: bool = False
    ) -> None:
        message = Message(
            sender=self._agent_id,
            recipient="orchestrator",
            type=MessageType.STATUS_UPDATE,
            payload={
                "agent_id": self._agent_id,
                "status": status,
                "progress": progress,
                "thinking": thinking,
            },
            priority=Priority.LOW,
        )
        await self.send_message(message)
        self._progress = progress

    async def shutdown(self) -> None:
        self._state = AgentState.TERMINATED
        self._log.info("Agent shut down")

    def get_status_report(self) -> dict[str, Any]:
        return {
            "agent_id": self._agent_id,
            "role": self.role,
            "state": self._state.value,
            "progress": self._progress,
            "current_task": self._current_task.description if self._current_task else None,
            "task_history_count": len(self._task_history),
            "uptime_seconds": (
                (datetime.now(UTC) - self._started_at).total_seconds()
                if self._started_at
                else 0
            ),
        }


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._agent_infos: dict[str, dict[str, Any]] = {}

    def register(self, agent: BaseAgent, metadata: dict[str, Any] | None = None) -> None:
        if agent.agent_id in self._agents:
            logger.warning(f"Agent {agent.agent_id} already registered, replacing")

        self._agents[agent.agent_id] = agent
        self._agent_infos[agent.agent_id] = {
            "agent_id": agent.agent_id,
            "role": agent.role,
            "state": agent.state.value,
            "metadata": metadata or {},
            "registered_at": datetime.now(UTC).isoformat(),
        }
        logger.info(f"Agent registered: {agent.agent_id} ({agent.role})")

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._agent_infos.pop(agent_id, None)
        logger.info(f"Agent unregistered: {agent_id}")

    def get_agent(self, agent_id: str) -> BaseAgent:
        if agent_id not in self._agents:
            raise AgentNotFoundError(
                f"Agent not found: {agent_id}",
                code="AGENT_NOT_FOUND",
            )
        return self._agents[agent_id]

    def get_by_role(self, role: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.role == role]

    def list_agents(self) -> list[dict[str, Any]]:
        return [
            {
                "agent_id": agent.agent_id,
                "role": agent.role,
                "state": agent.state.value,
                "progress": agent.progress,
                "current_task": agent.current_task.description if agent.current_task else None,
            }
            for agent in self._agents.values()
        ]

    async def initialize_all(self) -> None:
        for agent in self._agents.values():
            await agent.initialize()

    async def shutdown_all(self) -> None:
        for agent in self._agents.values():
            await agent.shutdown()

    @property
    def count(self) -> int:
        return len(self._agents)

    def get_status_report(self) -> dict[str, Any]:
        states = {}
        for agent in self._agents.values():
            state = agent.state.value
            states[state] = states.get(state, 0) + 1

        return {
            "total_agents": self.count,
            "by_state": states,
            "agents": self.list_agents(),
        }
