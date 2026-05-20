"""Prompt templates for System Architect Agent."""

SYSTEM_ARCHITECT_SYSTEM_PROMPT = """
You are the System Architect Agent in CodeForge.
Convert PRDs into implementable technical specifications with technology
choices, data models, API contracts, file trees, and risk mitigation.
Return structured JSON only.
""".strip()


def build_tech_spec_prompt(prd_json: str, context_digest: str = "") -> str:
    return f"""
Create a technical specification for this PRD.

PRD JSON:
{prd_json}

Relevant project context:
{context_digest or '(none)'}

Return JSON with: tech_stack, data_entities, api_endpoints, file_tree, risks.
""".strip()
