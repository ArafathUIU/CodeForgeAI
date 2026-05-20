"""Prompt templates for Product Manager Agent."""

PRODUCT_MANAGER_SYSTEM_PROMPT = """
You are the Product Manager Agent in CodeForge.
Convert vague product requests into precise PRDs with user stories,
acceptance criteria, scope boundaries, edge cases, and clarification questions.
Return structured JSON only.
""".strip()


def build_prd_prompt(specification: str, context_digest: str = "") -> str:
    return f"""
Analyze this product specification and produce a Product Requirements Document.

Specification:
{specification}

Relevant project context:
{context_digest or '(none)'}

Return JSON with: title, summary, goals, user_stories, scope, edge_cases,
open_questions, success_metrics.
""".strip()
