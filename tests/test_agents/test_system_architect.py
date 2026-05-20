"""Tests for System Architect Agent components."""

from codeforge.agents.system_architect.api_designer import APIContractDesigner
from codeforge.agents.system_architect.data_model import DataModelDesigner
from codeforge.agents.system_architect.file_tree import FileTreeGenerator
from codeforge.agents.system_architect.risk_assessor import RiskAssessor
from codeforge.agents.system_architect.tech_stack import TechStackSelector
from codeforge.artifacts.prd import PRD, ScopeBoundary, UserStory


def sample_prd() -> PRD:
    return PRD(
        id="prd-1",
        title="Expense Tracker",
        summary="Track personal spending",
        scope=ScopeBoundary(in_scope=["user authentication", "data export"]),
        user_stories=[UserStory("US-001", "user", "add expenses", "track spending")],
    )


def test_stack_selector_returns_default_stack():
    stack = TechStackSelector().select(sample_prd())

    choices = {decision.choice for decision in stack}
    assert "FastAPI" in choices
    assert "SQLite" in choices


def test_data_model_designer_adds_user_and_feature_entity():
    entities = DataModelDesigner().design(sample_prd())

    names = {entity.name for entity in entities}
    assert "User" in names
    assert "Expense" in names


def test_api_designer_creates_crud_and_export_endpoints():
    prd = sample_prd()
    entities = DataModelDesigner().design(prd)
    endpoints = APIContractDesigner().design(prd, entities)
    paths = {endpoint.path for endpoint in endpoints}

    assert "/expenses" in paths
    assert "/export" in paths


def test_file_tree_generator_contains_backend_and_frontend_files():
    nodes = FileTreeGenerator().generate()
    paths = {node.path for node in nodes}

    assert "app/main.py" in paths
    assert "frontend/app.py" in paths


def test_risk_assessor_adds_auth_risk():
    risks = RiskAssessor().assess(sample_prd())

    assert any(risk.severity == "high" for risk in risks)
