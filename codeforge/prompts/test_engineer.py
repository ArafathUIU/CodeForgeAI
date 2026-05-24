"""Prompt templates for Test Engineer Agent."""

TEST_ENGINEER_SYSTEM_PROMPT = """
You are the Test Engineer Agent in CodeForge.
Generate comprehensive test suites with five test patterns:
1. Happy path testing  2. Boundary case testing  3. Error handling testing
4. Concurrency testing  5. Security testing
Target 85% code coverage. Return Python code with pytest.
""".strip()


def build_test_prompt(source_code: str, entity_name: str) -> str:
    return f"""
Generate a pytest test suite for this code entity `{entity_name}`:

Source code:
{source_code}

Include all 5 test patterns: happy path, boundary, error handling,
concurrency, and security. Use pytest fixtures where appropriate.
Return complete, runnable Python test code.
""".strip()
