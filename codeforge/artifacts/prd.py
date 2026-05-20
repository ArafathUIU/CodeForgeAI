"""Product Requirements Document artifact models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AcceptanceCriterion:
    """A testable condition for accepting a user story."""

    id: str
    description: str
    testable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "testable": self.testable,
        }


@dataclass
class UserStory:
    """A user story with acceptance criteria."""

    id: str
    actor: str
    capability: str
    benefit: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    priority: str = "medium"

    @property
    def statement(self) -> str:
        return f"As a {self.actor}, I want {self.capability}, so that {self.benefit}."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "capability": self.capability,
            "benefit": self.benefit,
            "statement": self.statement,
            "priority": self.priority,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
        }


@dataclass
class ScopeBoundary:
    """Explicit in-scope and out-of-scope boundaries."""

    in_scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_scope": self.in_scope,
            "out_of_scope": self.out_of_scope,
            "assumptions": self.assumptions,
        }


@dataclass
class PRD:
    """Formal Product Requirements Document produced by Product Manager Agent."""

    id: str
    title: str
    summary: str
    goals: list[str] = field(default_factory=list)
    user_stories: list[UserStory] = field(default_factory=list)
    scope: ScopeBoundary = field(default_factory=ScopeBoundary)
    edge_cases: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_user_story(self, story: UserStory) -> None:
        self.user_stories.append(story)

    def acceptance_criteria_count(self) -> int:
        return sum(len(story.acceptance_criteria) for story in self.user_stories)

    def is_ready_for_architecture(self) -> bool:
        return bool(self.title and self.summary and self.user_stories and not self.open_questions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "goals": self.goals,
            "user_stories": [story.to_dict() for story in self.user_stories],
            "scope": self.scope.to_dict(),
            "edge_cases": self.edge_cases,
            "open_questions": self.open_questions,
            "success_metrics": self.success_metrics,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PRD:
        stories = []
        for story_data in data.get("user_stories", []):
            criteria = [
                AcceptanceCriterion(
                    id=c["id"],
                    description=c["description"],
                    testable=c.get("testable", True),
                )
                for c in story_data.get("acceptance_criteria", [])
            ]
            stories.append(
                UserStory(
                    id=story_data["id"],
                    actor=story_data["actor"],
                    capability=story_data["capability"],
                    benefit=story_data["benefit"],
                    acceptance_criteria=criteria,
                    priority=story_data.get("priority", "medium"),
                )
            )

        scope_data = data.get("scope", {})
        return cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            goals=data.get("goals", []),
            user_stories=stories,
            scope=ScopeBoundary(
                in_scope=scope_data.get("in_scope", []),
                out_of_scope=scope_data.get("out_of_scope", []),
                assumptions=scope_data.get("assumptions", []),
            ),
            edge_cases=data.get("edge_cases", []),
            open_questions=data.get("open_questions", []),
            success_metrics=data.get("success_metrics", []),
            version=data.get("version", "1.0"),
        )
