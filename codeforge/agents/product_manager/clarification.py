"""Clarification and ambiguity detection for Product Manager Agent."""

from __future__ import annotations

from dataclasses import dataclass, field

from codeforge.agents.product_manager.intent_parser import ParsedIntent


@dataclass
class ClarificationSet:
    """Ambiguities and questions discovered during requirements analysis."""

    ambiguities: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)

    @property
    def needs_human_input(self) -> bool:
        return bool(self.questions)


class ClarificationEngine:
    """Detects unclear requirements and generates targeted questions."""

    def analyze(self, intent: ParsedIntent) -> ClarificationSet:
        ambiguities: list[str] = []
        questions: list[str] = []
        spec = intent.raw_specification.lower()

        if len(intent.raw_specification.split()) < 8:
            ambiguities.append("The product request is very short.")
            questions.append("What are the top 3 features that must exist in version 1?")

        if "auth" not in spec and "login" not in spec and "user" in intent.actors:
            ambiguities.append("Authentication requirements are not explicit.")
            questions.append("Should the application require user login and account management?")

        if not any(word in spec for word in ("database", "store", "save", "persist")):
            ambiguities.append("Data persistence expectations are unclear.")
            questions.append("What information must be saved permanently?")

        if "admin" in intent.actors and "role" not in spec:
            ambiguities.append("Admin permissions are mentioned but not defined.")
            questions.append("What can admins do that normal users cannot?")

        return ClarificationSet(ambiguities=ambiguities, questions=questions)
