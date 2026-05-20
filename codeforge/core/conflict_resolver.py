"""Conflict resolution system for mediating disagreements between agents.

When agents disagree, the Conflict Resolver steps in as an automated mediator.
It analyzes disagreement types and resolves them based on a priority hierarchy,
escalating only fundamental disagreements to the human operator.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from codeforge.core.state_store import EpisodicStore
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


class ConflictType(str, Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    STYLE = "style"
    NAMING = "naming"
    DEPENDENCY = "dependency"
    OTHER = "other"


CONFLICT_PRIORITY: dict[ConflictType, int] = {
    ConflictType.SECURITY: 0,
    ConflictType.PERFORMANCE: 1,
    ConflictType.ARCHITECTURE: 2,
    ConflictType.DEPENDENCY: 3,
    ConflictType.STYLE: 4,
    ConflictType.NAMING: 5,
    ConflictType.OTHER: 6,
}


class ResolutionStrategy(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    HIGHER_PRIORITY_WINS = "higher_priority_wins"
    MERGE_BOTH = "merge_both"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    ROLLBACK = "rollback"


@dataclass
class Conflict:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conflict_type: ConflictType = ConflictType.OTHER
    agent_a: str = ""
    agent_b: str = ""
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    proposal_a: Any = None
    proposal_b: Any = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "unresolved"
    resolution_strategy: ResolutionStrategy | None = None
    resolution_result: dict[str, Any] = field(default_factory=dict)


class ConflictClassifier:
    KEYWORDS = {
        ConflictType.SECURITY: [
            "password", "token", "auth", "encryption", "ssl", "tls",
            "vulnerability", "injection", "sanitize", "csrf", "xss",
            "credential", "secret", "hash", "salt",
        ],
        ConflictType.PERFORMANCE: [
            "n+1", "performance", "slow", "optimize", "cache", "index",
            "query", "bottleneck", "latency", "throughput", "memory",
            "thread", "async", "concurrent",
        ],
        ConflictType.ARCHITECTURE: [
            "architecture", "design", "pattern", "separation", "layer",
            "module", "microservice", "monolith", "dependency injection",
            "interface", "abstract", "component",
        ],
        ConflictType.STYLE: [
            "style", "format", "pep", "naming", "indent", "spacing",
            "line length", "comment", "docstring", "import order",
        ],
        ConflictType.NAMING: [
            "name", "rename", "naming convention", "variable name",
            "function name", "class name",
        ],
        ConflictType.DEPENDENCY: [
            "dependency", "import", "library", "package", "version",
            "compatibility", "breaking change",
        ],
    }

    @classmethod
    def classify(cls, description: str, details: dict[str, Any] | None = None) -> ConflictType:
        text = description.lower()
        if details:
            text += " " + " ".join(str(v) for v in details.values()).lower()

        for ctype, keywords in cls.KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return ctype

        return ConflictType.OTHER


class ConflictResolver:
    def __init__(self, episodic_store: EpisodicStore):
        self._episodic_store = episodic_store
        self._conflicts: dict[str, Conflict] = {}
        self._resolution_log: list[dict[str, Any]] = []

    def register_conflict(
        self,
        conflict_type: ConflictType,
        agent_a: str,
        agent_b: str,
        description: str,
        proposal_a: Any = None,
        proposal_b: Any = None,
        details: dict[str, Any] | None = None,
    ) -> Conflict:
        conflict = Conflict(
            conflict_type=conflict_type,
            agent_a=agent_a,
            agent_b=agent_b,
            description=description,
            proposal_a=proposal_a,
            proposal_b=proposal_b,
            details=details or {},
        )
        self._conflicts[conflict.id] = conflict

        self._episodic_store.add(
            entry_id=f"conflict_{conflict.id}",
            entry_type="conflict_registered",
            content={
                "conflict_id": conflict.id,
                "type": conflict_type.value,
                "agents": [agent_a, agent_b],
                "description": description,
            },
            tags=["conflict", conflict_type.value],
        )

        logger.info(f"Conflict registered: {conflict.id[:8]} ({conflict_type.value})")
        return conflict

    async def resolve(self, conflict: Conflict) -> Conflict:
        strategy = self._determine_strategy(conflict)

        logger.info(
            f"Resolving conflict {conflict.id[:8]} with strategy: {strategy.value}"
        )

        if strategy == ResolutionStrategy.AUTO_RESOLVE:
            self._auto_resolve(conflict)
        elif strategy == ResolutionStrategy.HIGHER_PRIORITY_WINS:
            self._priority_resolve(conflict)
        elif strategy == ResolutionStrategy.MERGE_BOTH:
            self._merge_resolve(conflict)
        elif strategy == ResolutionStrategy.ESCALATE_TO_HUMAN:
            self._escalate(conflict)
        elif strategy == ResolutionStrategy.ROLLBACK:
            self._rollback_resolve(conflict)

        self._log_resolution(conflict)
        return conflict

    def _determine_strategy(self, conflict: Conflict) -> ResolutionStrategy:
        priority = CONFLICT_PRIORITY[conflict.conflict_type]

        if conflict.conflict_type == ConflictType.SECURITY:
            return ResolutionStrategy.HIGHER_PRIORITY_WINS

        if conflict.conflict_type == ConflictType.PERFORMANCE:
            if self._is_trivial_style_related(conflict):
                return ResolutionStrategy.AUTO_RESOLVE
            return ResolutionStrategy.HIGHER_PRIORITY_WINS

        if conflict.conflict_type == ConflictType.ARCHITECTURE:
            agent_a_role = conflict.details.get("role_a", "")
            agent_b_role = conflict.details.get("role_b", "")
            if "architect" in agent_a_role.lower():
                return ResolutionStrategy.HIGHER_PRIORITY_WINS
            return ResolutionStrategy.ESCALATE_TO_HUMAN

        if conflict.conflict_type in (ConflictType.STYLE, ConflictType.NAMING):
            return ResolutionStrategy.AUTO_RESOLVE

        if conflict.conflict_type == ConflictType.DEPENDENCY:
            return ResolutionStrategy.MERGE_BOTH

        return ResolutionStrategy.ESCALATE_TO_HUMAN

    def _is_trivial_style_related(self, conflict: Conflict) -> bool:
        style_keywords = ["format", "naming", "spacing", "indent", "comment"]
        desc = conflict.description.lower()
        return any(kw in desc for kw in style_keywords)

    def _auto_resolve(self, conflict: Conflict) -> None:
        if conflict.conflict_type == ConflictType.STYLE:
            conflict.resolution_result = {
                "winner": "auto_fixer",
                "decision": "Apply automated style fix",
                "note": "Style conflicts resolved automatically per configuration",
            }
        elif conflict.conflict_type == ConflictType.NAMING:
            conflict.resolution_result = {
                "winner": "auto_fixer",
                "decision": "Apply standard naming convention",
                "note": "Naming conflicts resolved using PEP 8 conventions",
            }
        else:
            conflict.resolution_result = {
                "winner": "auto_fixer",
                "decision": "Auto-resolved",
            }

        conflict.status = "resolved"
        conflict.resolution_strategy = ResolutionStrategy.AUTO_RESOLVE

    def _priority_resolve(self, conflict: Conflict) -> None:
        priority_a = conflict.details.get("priority_a", 0)
        priority_b = conflict.details.get("priority_b", 0)

        if priority_a >= priority_b:
            winner = conflict.agent_a
            chosen = conflict.proposal_a
        else:
            winner = conflict.agent_b
            chosen = conflict.proposal_b

        conflict.resolution_result = {
            "winner": winner,
            "decision": f"Agent {winner} priority ({max(priority_a, priority_b)})",
            "chosen_proposal": chosen,
        }
        conflict.status = "resolved"
        conflict.resolution_strategy = ResolutionStrategy.HIGHER_PRIORITY_WINS

    def _merge_resolve(self, conflict: Conflict) -> None:
        conflict.resolution_result = {
            "winner": "both",
            "decision": "Merge both proposals",
            "merged": {"a": conflict.proposal_a, "b": conflict.proposal_b},
            "note": "Both agents contributions accepted where non-conflicting",
        }
        conflict.status = "resolved"
        conflict.resolution_strategy = ResolutionStrategy.MERGE_BOTH

    def _escalate(self, conflict: Conflict) -> None:
        conflict.resolution_result = {
            "decision": "Escalated to human operator",
            "reason": "Conflict requires human judgment",
            "agent_a": conflict.agent_a,
            "agent_b": conflict.agent_b,
            "proposal_a": conflict.proposal_a,
            "proposal_b": conflict.proposal_b,
        }
        conflict.status = "escalated"
        conflict.resolution_strategy = ResolutionStrategy.ESCALATE_TO_HUMAN

        logger.warning(
            f"Conflict {conflict.id[:8]} escalated to human",
            extra={"type": conflict.conflict_type.value},
        )

    def _rollback_resolve(self, conflict: Conflict) -> None:
        conflict.resolution_result = {
            "decision": "Rollback to previous checkpoint",
            "reason": "Conflict cannot be resolved, rolling back",
        }
        conflict.status = "resolved_by_rollback"
        conflict.resolution_strategy = ResolutionStrategy.ROLLBACK

    def _log_resolution(self, conflict: Conflict) -> None:
        log_entry = {
            "conflict_id": conflict.id,
            "type": conflict.conflict_type.value,
            "resolution_strategy": (
                conflict.resolution_strategy.value
                if conflict.resolution_strategy
                else None
            ),
            "result": conflict.resolution_result,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._resolution_log.append(log_entry)

        self._episodic_store.add(
            entry_id=f"conflict_resolved_{conflict.id}",
            entry_type="conflict_resolved",
            content=log_entry,
            tags=["conflict", "resolved"],
        )

    def get_unresolved(self) -> list[Conflict]:
        return [c for c in self._conflicts.values() if c.status == "unresolved"]

    def get_escalated(self) -> list[Conflict]:
        return [c for c in self._conflicts.values() if c.status == "escalated"]

    def get_resolution_log(self) -> list[dict[str, Any]]:
        return list(self._resolution_log)

    def get_summary(self) -> dict[str, Any]:
        total = len(self._conflicts)
        resolved = len([c for c in self._conflicts.values() if c.status == "resolved"])
        escalated = len([c for c in self._conflicts.values() if c.status == "escalated"])
        return {
            "total_conflicts": total,
            "resolved": resolved,
            "escalated": escalated,
            "unresolved": total - resolved - escalated,
        }
