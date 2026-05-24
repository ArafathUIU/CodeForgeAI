"""Prompt templates for Code Reviewer Agent."""

CODE_REVIEWER_SYSTEM_PROMPT = """
You are the Code Reviewer Agent in CodeForge.
Perform a six-layer code review:
1. Syntax Analysis  2. Security Scanning  3. Style Compliance
4. Performance Analysis  5. Maintainability Assessment  6. Architecture Compliance

Return structured JSON with findings, severity, and fix suggestions.
""".strip()


def build_review_prompt(source_code: str, file_path: str) -> str:
    return f"""
Review this code file `{file_path}`:

```python
{source_code}
```

Analyze across all 6 layers. Return JSON with: overall_score (0-1),
findings list (each with layer, severity, message, line, auto_fixable, suggestion).
""".strip()
