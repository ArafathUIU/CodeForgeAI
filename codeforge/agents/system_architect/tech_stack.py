"""Technology stack selection for System Architect Agent."""

from codeforge.artifacts.prd import PRD
from codeforge.artifacts.tech_spec import TechStackDecision


class TechStackSelector:
    """Selects an MVP-friendly stack with explicit rationale."""

    def select(self, prd: PRD) -> list[TechStackDecision]:
        return [
            TechStackDecision(
                category="backend",
                choice="FastAPI",
                rationale=(
                    "FastAPI provides typed request/response validation "
                    "and async APIs with minimal boilerplate."
                ),
                alternatives_considered=["Flask", "Django"],
            ),
            TechStackDecision(
                category="database",
                choice="SQLite",
                rationale=(
                    "SQLite is sufficient for local MVPs and demos while "
                    "keeping setup friction low."
                ),
                alternatives_considered=["PostgreSQL", "MySQL"],
            ),
            TechStackDecision(
                category="frontend",
                choice="Streamlit",
                rationale=(
                    f"Streamlit can quickly expose the core workflows for {prd.title} "
                    "without a separate build pipeline."
                ),
                alternatives_considered=["React", "Vue"],
            ),
            TechStackDecision(
                category="testing",
                choice="pytest",
                rationale=(
                    "pytest has concise fixtures, async support, and "
                    "strong ecosystem compatibility."
                ),
                alternatives_considered=["unittest"],
            ),
        ]
