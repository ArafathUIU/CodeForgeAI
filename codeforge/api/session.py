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
        self._bus.register_agent("human_operator", self._noop)  # silence dead-letter warnings

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

    @staticmethod
    def _noop(_message) -> None:
        pass

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
            output_dir=output_dir, llm_client=self._llm,
        )
        te = TestEngineerAgent(
            agent_id="test_engineer", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            output_dir=output_dir, llm_client=self._llm,
        )
        cr = CodeReviewerAgent(
            agent_id="code_reviewer", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            llm_client=self._llm,
        )
        ops = DevOpsAgent(
            agent_id="devops", message_bus=self._bus,
            episodic_store=self._episodic, semantic_store=self._semantic,
            output_dir=output_dir, llm_client=self._llm,
        )

        for agent in [pm, sa, cw, te, cr, ops]:
            self._registry.register(agent)
            self._bus.register_agent(agent.agent_id, agent.handle_message)
            self._bus.subscribe(agent.agent_id, self._capture_message)
        self._bus.subscribe("orchestrator", self._capture_message)
        self._bus.subscribe("human_operator", self._capture_message)

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
            "dialogue": self._synthesize_dialogue(),
            "decisions": self._synthesize_decisions(),
        }

    def _synthesize_dialogue(self) -> list[dict]:
        dialogue: list[dict] = []
        for msg in self._messages:
            entry = self._message_to_dialogue(msg)
            if entry:
                dialogue.append(entry)
        return dialogue

    @staticmethod
    def _message_to_dialogue(msg: dict) -> dict | None:
        msg_type = PipelineSession._normalize_type(msg.get("type", ""))
        sender = msg.get("sender", "")
        payload = msg.get("payload", {})
        recipient = msg.get("recipient", "")

        agent_names: dict[str, str] = {
            "product_manager": "Product Manager",
            "system_architect": "System Architect",
            "code_writer": "Code Writer",
            "test_engineer": "Test Engineer",
            "code_reviewer": "Code Reviewer",
            "devops": "DevOps",
            "orchestrator": "Orchestrator",
        }
        avatar_map: dict[str, str] = {
            "product_manager": "\U0001f4cb",
            "system_architect": "\U0001f3d7\ufe0f",
            "code_writer": "\U0001f4bb",
            "test_engineer": "\U0001f9ea",
            "code_reviewer": "\U0001f50d",
            "devops": "\U0001f680",
            "orchestrator": "\U0001f504",
        }
        name = agent_names.get(sender, sender.capitalize() if sender else "System")
        avatar = avatar_map.get(sender, "\U0001f916")

        if msg_type == "task_assignment":
            r_name = agent_names.get(recipient, recipient.capitalize())
            r_avatar = avatar_map.get(recipient, "\U0001f916")
            desc = payload.get("description", "")
            phase = ""
            phase_words = [
                "requirements", "architecture", "implementation",
                "testing", "review", "deployment",
            ]
            for word in phase_words:
                if word in desc.lower():
                    phase = word
                    break
            role_actions: dict[str, str] = {
                "product_manager": (
                    "analyzing the specification and drafting the PRD"
                ),
                "system_architect": (
                    "designing the system architecture and tech stack"
                ),
                "code_writer": (
                    "implementing the code based on the technical spec"
                ),
                "test_engineer": "generating comprehensive test suites",
                "code_reviewer": (
                    "reviewing code quality and architecture compliance"
                ),
                "devops": (
                    "preparing Docker, Compose, and CI/CD configurations"
                ),
            }
            action = role_actions.get(recipient, f"working on the {phase} phase")
            return {
                "avatar": r_avatar,
                "name": r_name,
                "text": f"Task received \u2014 {action}.",
                "kind": "task",
                "phase": phase,
                "timestamp": msg.get("timestamp", ""),
            }

        if msg_type == "artifact_submission":
            art_type = payload.get("artifact_type", "artifact")
            notes = payload.get("notes", "")
            art_labels: dict[str, str] = {
                "prd": "PRD",
                "tech_spec": "Technical Specification",
                "source_code": "Source Code",
                "test_suite": "Test Suite",
                "review_report": "Review Report",
                "deployment_config": "Deployment Configuration",
            }
            label = art_labels.get(art_type, art_type)
            text = f"I have completed the {label} and submitted it for review."
            if notes:
                text += f"  {notes}"
            return {
                "avatar": avatar,
                "name": name,
                "text": text,
                "kind": "artifact",
                "phase": art_type,
                "timestamp": msg.get("timestamp", ""),
            }

        if msg_type == "status_update":
            status = payload.get("status", "")
            progress = payload.get("progress", 0)
            pct = (
                f" ({int(progress * 100)}%)"
                if isinstance(progress, (int, float)) and progress > 0
                else ""
            )
            return {
                "avatar": avatar,
                "name": name,
                "text": f"{status}{pct}",
                "kind": "status",
                "phase": "",
                "timestamp": msg.get("timestamp", ""),
            }

        if msg_type == "approval_request":
            art_id = payload.get("artifact_id", "")
            return {
                "avatar": "\U0001f504",
                "name": "Orchestrator",
                "text": (
                    f"Approval requested for artifact {art_id}. "
                    f"Awaiting human review."
                ),
                "kind": "approval",
                "phase": "",
                "timestamp": msg.get("timestamp", ""),
            }

        if msg_type == "approval_response":
            decision = payload.get("decision", "")
            return {
                "avatar": "\U0001f464",
                "name": "Human Operator",
                "text": f"Approval gate resolved: {decision.upper()}.",
                "kind": "approval",
                "phase": "",
                "timestamp": msg.get("timestamp", ""),
            }

        if msg_type == "system_event":
            event_type = payload.get("event_type", "")
            desc = payload.get("description", "")
            if "phase_transition" in event_type:
                return {
                    "avatar": "\U0001f504",
                    "name": "Orchestrator",
                    "text": f"Pipeline advancing: {desc}",
                    "kind": "system",
                    "phase": "",
                    "timestamp": msg.get("timestamp", ""),
                }
            if "project_started" in event_type:
                return {
                    "avatar": "\U0001f504",
                    "name": "Orchestrator",
                    "text": desc,
                    "kind": "system",
                    "phase": "init",
                    "timestamp": msg.get("timestamp", ""),
                }
            if "project_complete" in event_type:
                return {
                    "avatar": "\U0001f504",
                    "name": "Orchestrator",
                    "text": desc,
                    "kind": "system",
                    "phase": "complete",
                    "timestamp": msg.get("timestamp", ""),
                }
            return {
                "avatar": "\U0001f504",
                "name": "Orchestrator",
                "text": desc,
                "kind": "system",
                "phase": "",
                "timestamp": msg.get("timestamp", ""),
            }

        # fallback: never return None when a message exists
        short_payload = str(payload)[:120]
        fallback_text = f"[{msg_type}] {short_payload}" if short_payload else f"[{msg_type}]"
        return {
            "avatar": avatar,
            "name": name or sender or "Agent",
            "text": fallback_text,
            "kind": "raw",
            "phase": "",
            "timestamp": msg.get("timestamp", ""),
        }

    @staticmethod
    def _normalize_type(raw: str) -> str:
        if not raw:
            return ""
        for suffix in (
            "task_assignment", "artifact_submission", "status_update",
            "approval_request", "approval_response", "system_event",
            "clarification_request", "clarification_response",
            "blockage_report", "revision_request", "conflict_escalation",
        ):
            if raw.endswith(suffix):
                return suffix
        return raw

    def _synthesize_decisions(self) -> list[dict]:
        decisions: list[dict] = []
        artifacts = self._orchestrator._artifacts

        prd = artifacts.get("prd", {})
        if prd:
            goals = prd.get("goals", [])
            decisions.append({
                "phase": "requirements",
                "icon": "📋",
                "title": "Product Scope Defined",
                "detail": f"{len(goals)} goal(s) identified and {prd.get('title', '')} scoped.",
            })

        ts = artifacts.get("tech_spec", {})
        if ts:
            stack = ts.get("tech_stack", [])
            entities = ts.get("data_entities", [])
            decisions.append({
                "phase": "architecture",
                "icon": "🏗️",
                "title": f"Tech Stack: {stack[0].get('choice', 'N/A') if stack else 'N/A'}",
                "detail": (
                    f"{len(stack)} component(s) selected. "
                    f"{len(entities)} data entity/entities designed."
                ),
            })

        sc = artifacts.get("source_code", {})
        if sc:
            report = sc.get("validation_report", "")
            files = sc.get("files", [])
            decisions.append({
                "phase": "implementation",
                "icon": "💻",
                "title": f"{len(files)} File(s) Implemented",
                "detail": report,
            })

        tst = artifacts.get("test_suite", {})
        if tst:
            cov = tst.get("coverage_report", "")
            patterns = tst.get("patterns_generated", 0)
            decisions.append({
                "phase": "testing",
                "icon": "🧪",
                "title": f"{patterns} Test Pattern(s) Applied",
                "detail": cov,
            })

        rev = artifacts.get("review_report", {})
        if rev:
            score = rev.get("overall_score", 0)
            findings = rev.get("total_findings", 0)
            decisions.append({
                "phase": "review",
                "icon": "🔍",
                "title": (
                    f"Review Score: {score:.1%}" if isinstance(score, float)
                    else "Review Done"
                ),
                "detail": f"{findings} finding(s). No critical blockers.",
            })

        dep = artifacts.get("deployment_config", {})
        if dep:
            files = dep.get("files_generated", [])
            decisions.append({
                "phase": "deployment",
                "icon": "🚀",
                "title": f"{len(files)} Deployment File(s) Generated",
                "detail": "Docker, Compose, CI/CD, and env template ready.",
            })

        return decisions

    def run_sync(self, specification: str, output_dir: str = "") -> dict:
        async def _run():
            await self.start(specification, output_dir)
            return self.get_state()

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
