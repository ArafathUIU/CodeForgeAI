"""Tests for Phase 2 artifact models."""

from codeforge.artifacts.prd import AcceptanceCriterion, PRD, ScopeBoundary, UserStory
from codeforge.artifacts.tech_spec import APIEndpoint, DataEntity, DataField, FileTreeNode, TechSpec, TechStackDecision


def test_user_story_statement_and_serialization():
    story = UserStory(
        id="US-001",
        actor="user",
        capability="track expenses",
        benefit="I can understand spending",
        acceptance_criteria=[AcceptanceCriterion("AC-001", "Expense is saved")],
    )

    assert story.statement.startswith("As a user")
    assert story.to_dict()["acceptance_criteria"][0]["id"] == "AC-001"


def test_prd_ready_requires_no_open_questions():
    prd = PRD(
        id="prd-1",
        title="Expense Tracker",
        summary="Track expenses",
        user_stories=[
            UserStory("US-001", "user", "add expenses", "I can track spending")
        ],
        open_questions=[],
    )

    assert prd.is_ready_for_architecture()


def test_prd_roundtrip_from_dict():
    prd = PRD(
        id="prd-1",
        title="Todo App",
        summary="Manage tasks",
        scope=ScopeBoundary(in_scope=["task creation"]),
        user_stories=[UserStory("US-001", "user", "create tasks", "I stay organized")],
    )

    restored = PRD.from_dict(prd.to_dict())
    assert restored.title == "Todo App"
    assert restored.user_stories[0].capability == "create tasks"


def test_tech_spec_ready_for_implementation():
    spec = TechSpec(
        id="ts-1",
        title="Tech Spec",
        overview="Build app",
        tech_stack=[TechStackDecision("backend", "FastAPI", "Typed APIs")],
        file_tree=[FileTreeNode("app/main.py", "file", "Entrypoint")],
    )

    assert spec.is_ready_for_implementation()


def test_data_entity_and_endpoint_serialization():
    entity = DataEntity("Expense", fields=[DataField("amount", "float")])
    endpoint = APIEndpoint("post", "/expenses", "Create expense")

    assert entity.to_dict()["fields"][0]["name"] == "amount"
    assert endpoint.to_dict()["method"] == "POST"
