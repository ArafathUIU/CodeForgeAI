"""Intent parsing for the Product Manager Agent."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ParsedIntent:
    """Structured interpretation of a user's raw product request."""

    raw_specification: str
    product_name: str
    core_goal: str
    inferred_features: list[str] = field(default_factory=list)
    actors: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


class IntentParser:
    """Extracts product intent, likely actors, and implied features."""

    FEATURE_KEYWORDS = {
        "auth": "user authentication",
        "login": "user authentication",
        "dashboard": "dashboard view",
        "export": "data export",
        "report": "reporting",
        "notification": "notifications",
        "search": "search and filtering",
        "filter": "search and filtering",
        "upload": "file upload",
        "payment": "payment handling",
        "admin": "admin management",
    }

    ACTOR_KEYWORDS = {
        "admin": "admin",
        "manager": "manager",
        "team": "team member",
        "customer": "customer",
        "user": "user",
    }

    def parse(self, specification: str) -> ParsedIntent:
        spec = specification.strip()
        product_name = self._infer_product_name(spec)
        return ParsedIntent(
            raw_specification=spec,
            product_name=product_name,
            core_goal=self._infer_core_goal(spec, product_name),
            inferred_features=self._infer_features(spec),
            actors=self._infer_actors(spec),
            constraints=self._infer_constraints(spec),
        )

    def _infer_product_name(self, spec: str) -> str:
        match = re.search(r"(?:build|create|make|develop)\s+(?:a|an)?\s*([^.,\n]+)", spec, re.I)
        if match:
            name = match.group(1).strip()
            return " ".join(word.capitalize() for word in name.split()[:5])
        words = re.findall(r"[A-Za-z0-9]+", spec)
        return " ".join(words[:4]).title() if words else "Untitled Product"

    def _infer_core_goal(self, spec: str, product_name: str) -> str:
        if len(spec) <= 160:
            return spec
        return f"Build {product_name} that satisfies the submitted product specification."

    def _infer_features(self, spec: str) -> list[str]:
        lowered = spec.lower()
        features = [feature for key, feature in self.FEATURE_KEYWORDS.items() if key in lowered]
        if not features:
            features.append("core CRUD workflow")
        return sorted(set(features))

    def _infer_actors(self, spec: str) -> list[str]:
        lowered = spec.lower()
        actors = [actor for key, actor in self.ACTOR_KEYWORDS.items() if key in lowered]
        return sorted(set(actors)) or ["user"]

    def _infer_constraints(self, spec: str) -> list[str]:
        constraints = []
        lowered = spec.lower()
        if "mobile" in lowered:
            constraints.append("mobile-friendly interface")
        if "offline" in lowered:
            constraints.append("offline-capable behavior")
        if "secure" in lowered or "security" in lowered:
            constraints.append("security-sensitive implementation")
        return constraints
