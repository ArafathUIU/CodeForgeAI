"""PRD generation for Product Manager Agent."""

from __future__ import annotations

import uuid

from codeforge.agents.product_manager.clarification import ClarificationSet
from codeforge.agents.product_manager.intent_parser import ParsedIntent
from codeforge.artifacts.prd import PRD, AcceptanceCriterion, ScopeBoundary, UserStory


class PRDGenerator:
    """Builds a formal PRD from parsed intent and clarification results."""

    def generate(self, intent: ParsedIntent, clarifications: ClarificationSet) -> PRD:
        prd = PRD(
            id=f"prd-{uuid.uuid4().hex[:8]}",
            title=intent.product_name,
            summary=intent.core_goal,
            goals=[intent.core_goal],
            scope=ScopeBoundary(
                in_scope=intent.inferred_features,
                out_of_scope=["enterprise scaling", "paid subscription handling"],
                assumptions=intent.constraints or ["single-tenant MVP deployment"],
            ),
            edge_cases=self._edge_cases(intent),
            open_questions=clarifications.questions,
            success_metrics=[
                "All high-priority user stories have acceptance criteria.",
                "Generated implementation passes automated tests.",
            ],
        )

        for index, feature in enumerate(intent.inferred_features, start=1):
            story = UserStory(
                id=f"US-{index:03d}",
                actor=intent.actors[0],
                capability=feature,
                benefit=f"I can accomplish the primary goal of {intent.product_name}",
                priority="high" if index == 1 else "medium",
                acceptance_criteria=[
                    AcceptanceCriterion(
                        id=f"AC-{index:03d}-1",
                        description=f"The {feature} flow works with valid input.",
                    ),
                    AcceptanceCriterion(
                        id=f"AC-{index:03d}-2",
                        description=f"The {feature} flow rejects invalid input clearly.",
                    ),
                ],
            )
            prd.add_user_story(story)

        return prd

    def _edge_cases(self, intent: ParsedIntent) -> list[str]:
        cases = [
            "User submits incomplete or malformed data.",
            "User refreshes or repeats an action during submission.",
        ]
        if "data export" in intent.inferred_features:
            cases.append("User exports an empty data set.")
        if "user authentication" in intent.inferred_features:
            cases.append("Unauthenticated user attempts protected actions.")
        return cases

    def generate_from_dict(self, data: dict, specification: str) -> PRD:
        scope_data = data.get("scope", {})
        if isinstance(scope_data, dict):
            in_scope = scope_data.get("in_scope", [])
            out_scope = scope_data.get("out_of_scope", [])
            assumptions = scope_data.get("assumptions", [])
        else:
            in_scope, out_scope, assumptions = [], [], []

        prd = PRD(
            id=f"prd-{uuid.uuid4().hex[:8]}",
            title=data.get("title", "Untitled App"),
            summary=data.get("summary", specification[:120]),
            goals=data.get("goals", [specification]),
            scope=ScopeBoundary(
                in_scope=in_scope,
                out_of_scope=out_scope,
                assumptions=assumptions,
            ),
            edge_cases=data.get("edge_cases", []),
            open_questions=data.get("open_questions", []),
            success_metrics=data.get("success_metrics", []),
        )

        stories_data = data.get("user_stories", [])
        for idx, story in enumerate(stories_data, start=1):
            if isinstance(story, str):
                criteria = [
                    AcceptanceCriterion(
                        id=f"AC-{idx:03d}-1",
                        description=story,
                    ),
                ]
                us = UserStory(
                    id=f"US-{idx:03d}",
                    actor="User",
                    capability=story[:60],
                    benefit=story[:60],
                    acceptance_criteria=criteria,
                    priority="medium",
                )
                prd.add_user_story(us)
                continue

            criteria_data = story.get("acceptance_criteria", [])
            criteria = [
                AcceptanceCriterion(
                    id=(
                        c.get("id", f"AC-{idx:03d}-{j}")
                        if isinstance(c, dict)
                        else f"AC-{idx:03d}-{j}"
                    ),
                    description=(
                        c.get("description", "")
                        if isinstance(c, dict)
                        else str(c)
                    ),
                )
                for j, c in enumerate(criteria_data, start=1)
            ]
            us = UserStory(
                id=story.get("id", f"US-{idx:03d}"),
                actor=story.get("actor", "User"),
                capability=story.get("capability", ""),
                benefit=story.get("benefit", ""),
                acceptance_criteria=criteria,
                priority=story.get("priority", "medium"),
            )
            prd.add_user_story(us)

        return prd
