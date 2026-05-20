"""Tests for Product Manager Agent components."""

from codeforge.agents.product_manager.clarification import ClarificationEngine
from codeforge.agents.product_manager.intent_parser import IntentParser
from codeforge.agents.product_manager.prd_generator import PRDGenerator


def test_intent_parser_extracts_product_name_and_features():
    parser = IntentParser()
    intent = parser.parse("Build an expense tracker with dashboard, export, and login")

    assert "Expense Tracker" in intent.product_name
    assert "dashboard view" in intent.inferred_features
    assert "data export" in intent.inferred_features
    assert "user authentication" in intent.inferred_features


def test_clarification_engine_detects_short_request():
    intent = IntentParser().parse("Build app")
    clarifications = ClarificationEngine().analyze(intent)

    assert clarifications.needs_human_input
    assert clarifications.questions


def test_prd_generator_creates_user_stories_and_criteria():
    intent = IntentParser().parse("Build a todo app with search and export")
    clarifications = ClarificationEngine().analyze(intent)
    prd = PRDGenerator().generate(intent, clarifications)

    assert prd.title
    assert prd.user_stories
    assert prd.acceptance_criteria_count() >= 2


def test_prd_generator_sets_scope_boundaries():
    intent = IntentParser().parse("Build an admin dashboard")
    prd = PRDGenerator().generate(intent, ClarificationEngine().analyze(intent))

    assert prd.scope.in_scope
    assert "enterprise scaling" in prd.scope.out_of_scope
