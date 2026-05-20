"""Technical risk assessment for System Architect Agent."""

from codeforge.artifacts.prd import PRD
from codeforge.artifacts.tech_spec import TechnicalRisk


class RiskAssessor:
    """Produces implementation risks and mitigations."""

    def assess(self, prd: PRD) -> list[TechnicalRisk]:
        risks = [
            TechnicalRisk(
                description="Requirements may still contain unresolved ambiguity.",
                severity="medium" if prd.open_questions else "low",
                mitigation="Hold approval gate until Product Manager questions are resolved.",
            ),
            TechnicalRisk(
                description="Generated code may drift from API contracts across files.",
                severity="medium",
                mitigation="Use Code Writer symbol tracking and syntax validation after each batch.",
            ),
        ]
        if any("authentication" in feature for feature in prd.scope.in_scope):
            risks.append(
                TechnicalRisk(
                    description="Authentication and authorization bugs can expose private data.",
                    severity="high",
                    mitigation="Require auth tests and security review before deployment.",
                )
            )
        return risks
