"""Prompt templates for Code Writer Agent."""

CODE_WRITER_SYSTEM_PROMPT = """
You are the Code Writer Agent in CodeForge.
Implement clean, well-structured Python code from technical specifications.
Follow best practices: type hints, docstrings, error handling, PEP 8.
Return executable Python code wrapped in markdown code blocks per file.
""".strip()


def build_code_prompt(tech_spec_json: str, file_path: str) -> str:
    return f"""
Implement the file `{file_path}` based on this technical specification:

{tech_spec_json}

Write complete, production-ready Python code for this file.
Include imports, type hints, docstrings, and proper error handling.
""".strip()


def build_full_implementation_prompt(tech_spec_json: str) -> str:
    return f"""
Implement ALL files from this technical specification:

{tech_spec_json}

For each file listed in the file_tree, write complete Python code.
Return a JSON object mapping file paths to their code content.
Format: {{"file_path.py": "code content here", ...}}
""".strip()
