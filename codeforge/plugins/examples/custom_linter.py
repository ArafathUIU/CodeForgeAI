"""[7.12] Plugin: Add example custom linter plugin."""

PLUGIN_MANIFEST = {
    "name": "custom_linter",
    "version": "1.0.0",
    "author": "CodeForge Community",
    "description": "Example linter plugin that checks code for custom rules",
    "entry_point": "plugins.custom_linter.main",
}


def analyze_file(file_path: str, content: str) -> list[dict]:
    issues = []
    lines = content.split("\n")
    for i, line in enumerate(lines, start=1):
        if len(line) > 120:
            issues.append({
                "file": file_path,
                "line": i,
                "severity": "warning",
                "message": "Line exceeds 120 characters",
            })
        if "TODO" in line:
            issues.append({
                "file": file_path,
                "line": i,
                "severity": "info",
                "message": "TODO comment found",
            })
    return issues


def get_rules() -> list[dict]:
    return [
        {"id": "L001", "name": "max-line-length", "config": {"max": 120}},
        {"id": "L002", "name": "no-todo", "config": {}},
    ]
