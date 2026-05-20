"""Central orchestrator coordinating the multi-agent pipeline.

The Orchestrator is the brain of CodeForge. It builds and executes
a DAG of phases, manages transitions, routes messages, and ensures
the pipeline flows from requirements to deployment.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from codeforge.core.agent_registry import AgentRegistry, BaseAgent, AgentState
from codeforge.core.checkpoint import CheckpointManager
from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import (
    Message,
    MessageType,
    Priority,
    create_system_event,
    create_task_assignment,
)
from codeforge.core.state_store import EpisodicStore, SemanticStore
from codeforge.utils.config import get_config
from codeforge.utils.exceptions import (
    AgentNotFoundError,
    PhaseTransitionError,
    PipelineError,
)
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


class Phase(str, Enum):
    INIT = "init"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    COMPLETE = "complete"
    FAILED = "failed"


PHASE_ORDER: list[Phase] = [
    Phase.INIT,
    Phase.REQUIREMENTS,
    Phase.ARCHITECTURE,
    Phase.IMPLEMENTATION,
    Phase.TESTING,
    Phase.REVIEW,
    Phase.DEPLOYMENT,
    Phase.COMPLETE,
]

VALID_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.INIT: [Phase.REQUIREMENTS],
    Phase.REQUIREMENTS: [Phase.ARCHITECTURE, Phase.FAILED],
    Phase.ARCHITECTURE: [Phase.IMPLEMENTATION, Phase.REQUIREMENTS, Phase.FAILED],
    Phase.IMPLEMENTATION: [Phase.TESTING, Phase.ARCHITECTURE, Phase.FAILED],
    Phase.TESTING: [Phase.REVIEW, Phase.IMPLEMENTATION, Phase.FAILED],
    Phase.REVIEW: [Phase.DEPLOYMENT, Phase.IMPLEMENTATION, Phase.FAILED],
    Phase.DEPLOYMENT: [Phase.COMPLETE, Phase.REVIEW, Phase.FAILED],
    Phase.COMPLETE: [Phase.REQUIREMENTS],
    Phase.FAILED: [Phase.INIT],
}

PHASE_AGENTS: dict[Phase, list[str]] = {
    Phase.REQUIREMENTS: ["product_manager"],
    Phase.ARCHITECTURE: ["system_architect"],
    Phase.IMPLEMENTATION: ["code_writer"],
    Phase.TESTING: ["test_engineer"],
    Phase.REVIEW: ["code_reviewer"],
    Phase.DEPLOYMENT: ["devops"],
}


@dataclass
class ApprovalGate:
    id: str
    phase: Phase
    description: str
    artifact_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"
    decision: str | None = None
    comments: str = ""


@dataclass
class PipelineState:
    phase: Phase = Phase.INIT
    sub_step: int = 0
    total_steps: int = 0
    errors: list[str] = field(default_factory=list)
    approval_gates: list[ApprovalGate] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Orchestrator:
    def __init__(
        self,
        message_bus: MessageBus,
        agent_registry: AgentRegistry,
        checkpoint_manager: CheckpointManager,
        episodic_store: EpisodicStore,
        semantic_store: SemanticStore,
    ):
        self._message_bus = message_bus
        self._agent_registry = agent_registry
        self._checkpoint_mgr = checkpoint_manager
        self._episodic_store = episodic_store
        self._semantic_store = semantic_store

        self._pipeline = PipelineState()
        self._project_id: str | None = None
        self._output_directory: str = ""
        self._input_spec: str = ""

    @property
    def current_phase(self) -> Phase:
        return self._pipeline.phase

    @property
    def is_complete(self) -> bool:
        return self._pipeline.phase in (Phase.COMPLETE, Phase.FAILED)

    async def start_project(self, specification: str, output_directory: str = "") -> str:
        self._project_id = str(uuid.uuid4())
        self._output_directory = output_directory or f"./codeforge_project_{self._project_id[:8]}"
        self._input_spec = specification
        self._pipeline = PipelineState(
            phase=Phase.INIT,
            started_at=datetime.now(timezone.utc),
        )

        self._episodic_store.add(
            entry_id=f"project_start_{self._project_id}",
            entry_type="project_start",
            content={
                "project_id": self._project_id,
                "specification": specification,
                "output_directory": self._output_directory,
            },
            phase=self._pipeline.phase.value,
        )

        logger.info(f"Project started: {self._project_id[:8]}")

        await self._emit_system_event(
            "project_started",
            f"Project {self._project_id[:8]} started",
            {"project_id": self._project_id, "spec_length": len(specification)},
        )

        await self._checkpoint_mgr.create_checkpoint(
            name="Project Start",
            phase=self._pipeline.phase.value,
            description="Initial project setup",
        )

        await self.transition_to(Phase.REQUIREMENTS)
        return self._project_id

    async def transition_to(self, target_phase: Phase) -> None:
        current = self._pipeline.phase

        if target_phase not in VALID_TRANSITIONS.get(current, []):
            raise PhaseTransitionError(
                f"Cannot transition from {current.value} to {target_phase.value}",
                code="INVALID_TRANSITION",
                details={"from": current.value, "to": target_phase.value},
            )

        old_phase = current
        self._pipeline.phase = target_phase

        self._episodic_store.add(
            entry_id=f"phase_transition_{uuid.uuid4()}",
            entry_type="phase_transition",
            content={"from": old_phase.value, "to": target_phase.value},
            phase=target_phase.value,
        )

        logger.info(f"Phase transition: {old_phase.value} -> {target_phase.value}")

        await self._emit_system_event(
            "phase_transition",
            f"Pipeline moved from {old_phase.value} to {target_phase.value}",
            {"from_phase": old_phase.value, "to_phase": target_phase.value},
        )

        await self._checkpoint_mgr.create_checkpoint(
            name=f"Enter {target_phase.value}",
            phase=target_phase.value,
            description=f"Transitioned from {old_phase.value} to {target_phase.value}",
            pipeline_state={"phase": target_phase.value},
        )

        if target_phase == Phase.COMPLETE:
            self._pipeline.completed_at = datetime.now(timezone.utc)
            await self._emit_system_event(
                "project_complete",
                f"Project {self._project_id[:8]} completed successfully",
            )
            return

        if target_phase == Phase.FAILED:
            await self._emit_system_event(
                "project_failed",
                f"Project {self._project_id[:8]} failed",
                {"errors": self._pipeline.errors},
            )
            return

        agent_names = PHASE_AGENTS.get(target_phase, [])
        if agent_names:
            await self._dispatch_phase_tasks(target_phase, agent_names)

    async def _dispatch_phase_tasks(self, phase: Phase, agent_names: list[str]) -> None:
        for agent_name in agent_names:
            try:
                agent = self._agent_registry.get_agent(agent_name)
                task_id = f"{phase.value}_{agent_name}_{uuid.uuid4().hex[:8]}"
                description = self._build_task_description(phase, agent_name)

                message = create_task_assignment(
                    task_id=task_id,
                    description=description,
                    agent_role=agent.role,
                    sender="orchestrator",
                    recipient=agent_name,
                    context={"project_id": self._project_id, "specification": self._input_spec},
                )

                await self._message_bus.publish(message)
                logger.info(f"Dispatched {phase.value} task to {agent_name}")

            except AgentNotFoundError:
                logger.warning(f"Agent {agent_name} not found, skipping {phase.value}")

    def _build_task_description(self, phase: Phase, agent_name: str) -> str:
        descriptions = {
            Phase.REQUIREMENTS: (
                f"Analyze the following specification and produce a formal PRD:\n\n"
                f"{self._input_spec}\n\n"
                f"Identify core goals, detect ambiguities, define scope boundaries, "
                f"probe edge cases, and formulate clarification questions if needed."
            ),
            Phase.ARCHITECTURE: (
                f"Based on the PRD, design the technical architecture including:\n"
                f"- Technology stack selection with justification\n"
                f"- Data model design\n"
                f"- API contract design\n"
                f"- Complete folder/file tree\n"
                f"- Risk assessment"
            ),
            Phase.IMPLEMENTATION: (
                f"Implement the software based on the technical specification.\n"
                f"Create all necessary files, follow the folder structure, and ensure\n"
                f"cross-file consistency. Use structured edits, not full file regeneration."
            ),
            Phase.TESTING: (
                f"Generate a comprehensive test suite following five patterns:\n"
                f"1. Happy path testing\n"
                f"2. Boundary case testing\n"
                f"3. Error handling testing\n"
                f"4. Concurrency testing\n"
                f"5. Security testing\n"
                f"Target 85% code coverage. Map tests to PRD acceptance criteria."
            ),
            Phase.REVIEW: (
                f"Perform a six-layer code review:\n"
                f"1. Syntax analysis\n"
                f"2. Security scanning\n"
                f"3. Style compliance\n"
                f"4. Performance analysis\n"
                f"5. Maintainability assessment\n"
                f"6. Architecture compliance\n"
                f"Auto-fix style issues. Report critical findings for human approval."
            ),
            Phase.DEPLOYMENT: (
                f"Prepare deployment artifacts:\n"
                f"- Multi-stage Dockerfile\n"
                f"- Docker Compose configuration\n"
                f"- CI/CD pipeline (GitHub Actions)\n"
                f"- Environment template\n"
                f"- Deployment documentation"
            ),
        }
        return descriptions.get(phase, f"Execute {phase.value} phase tasks for {agent_name}")

    async def handle_artifact_submission(self, message: Message) -> None:
        artifact_id = message.payload.get("artifact_id", "unknown")
        artifact_type = message.payload.get("artifact_type", "unknown")

        self._episodic_store.add(
            entry_id=f"artifact_{artifact_id}",
            entry_type="artifact_received",
            content={
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "sender": message.sender,
                "version": message.payload.get("version", "1.0"),
            },
            agent_id=message.sender,
            phase=self._pipeline.phase.value,
        )

        logger.info(f"Received artifact: {artifact_id} ({artifact_type}) from {message.sender}")

        if self._requires_approval(self._pipeline.phase):
            await self._create_approval_gate(artifact_id, self._pipeline.phase)

    def _requires_approval(self, phase: Phase) -> bool:
        return phase in {
            Phase.REQUIREMENTS,
            Phase.ARCHITECTURE,
            Phase.DEPLOYMENT,
        }

    async def _create_approval_gate(self, artifact_id: str, phase: Phase) -> None:
        gate = ApprovalGate(
            id=str(uuid.uuid4()),
            phase=phase,
            description=f"Review {phase.value} artifact: {artifact_id}",
            artifact_id=artifact_id,
        )
        self._pipeline.approval_gates.append(gate)

        message = Message(
            sender="orchestrator",
            recipient="human_operator",
            type=MessageType.APPROVAL_REQUEST,
            payload={
                "approval_id": gate.id,
                "artifact_id": artifact_id,
                "description": gate.description,
                "phase": phase.value,
            },
            priority=Priority.HIGH,
            requires_response=True,
        )
        await self._message_bus.publish(message)

        logger.info(f"Approval gate created: {gate.id} for {artifact_id}")

    async def handle_approval_response(self, message: Message) -> None:
        approval_id = message.payload.get("approval_id", "")
        decision = message.payload.get("decision", "reject")

        for gate in self._pipeline.approval_gates:
            if gate.id == approval_id:
                gate.status = "resolved"
                gate.decision = decision
                gate.comments = message.payload.get("comments", "")
                break

        if decision == "approve":
            next_phase_map = {
                Phase.REQUIREMENTS: Phase.ARCHITECTURE,
                Phase.ARCHITECTURE: Phase.IMPLEMENTATION,
                Phase.DEPLOYMENT: Phase.COMPLETE,
            }
            next_phase = next_phase_map.get(self._pipeline.phase)
            if next_phase:
                await self.transition_to(next_phase)
        elif decision == "reject":
            logger.info(f"Approval rejected for {approval_id}, requesting revision")
            revision_message = Message(
                sender="orchestrator",
                recipient=self._get_phase_agent(),
                type=MessageType.REVISION_REQUEST,
                payload={
                    "artifact_id": gate.artifact_id,
                    "revision_notes": message.payload.get("comments", "Revision requested"),
                    "requested_by": "human_operator",
                },
            )
            await self._message_bus.publish(revision_message)

    def _get_phase_agent(self) -> str:
        agents = PHASE_AGENTS.get(self._pipeline.phase, [])
        return agents[0] if agents else "unknown"

    async def handle_blockage(self, message: Message) -> None:
        reason = message.payload.get("blockage_reason", "Unknown")
        blocked_by = message.payload.get("blocked_by", "Unknown")
        logger.warning(f"Agent {message.sender} blocked: {reason} (by {blocked_by})")

        self._episodic_store.add(
            entry_id=f"blockage_{message.id}",
            entry_type="blockage",
            content={"reason": reason, "blocked_by": blocked_by, "agent": message.sender},
            agent_id=message.sender,
            phase=self._pipeline.phase.value,
        )

    async def fail_pipeline(self, reason: str) -> None:
        self._pipeline.errors.append(reason)
        await self.transition_to(Phase.FAILED)

    async def rollback_to_phase(self, phase: Phase) -> None:
        latest = self._checkpoint_mgr.get_latest()
        if latest:
            self._checkpoint_mgr.rollback_to(latest.id)
        self._pipeline.phase = phase
        logger.warning(f"Pipeline rolled back to phase: {phase.value}")

    async def _emit_system_event(
        self, event_type: str, description: str, extra: dict[str, Any] | None = None
    ) -> None:
        payload = {"event_type": event_type, "description": description}
        if extra:
            payload.update(extra)
        message = create_system_event(
            event_type=event_type,
            description=description,
        )
        message.payload.update(payload)
        await self._message_bus.publish(message)

    async def run_pipeline(self) -> PipelineState:
        if self._pipeline.phase == Phase.COMPLETE:
            return self._pipeline

        try:
            await self._message_bus.process_queue()
        except Exception as e:
            await self.fail_pipeline(str(e))

        return self._pipeline

    def get_pipeline_summary(self) -> dict[str, Any]:
        return {
            "project_id": self._project_id,
            "phase": self._pipeline.phase.value,
            "is_complete": self.is_complete,
            "errors": self._pipeline.errors,
            "approval_gates": [
                {"id": g.id, "status": g.status, "decision": g.decision}
                for g in self._pipeline.approval_gates
            ],
            "started_at": (
                self._pipeline.started_at.isoformat() if self._pipeline.started_at else None
            ),
            "completed_at": (
                self._pipeline.completed_at.isoformat() if self._pipeline.completed_at else None
            ),
        }
