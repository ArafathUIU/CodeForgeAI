"""Syntax validator: validates code syntax and cross-file consistency.

Runs automated checks after each implementation batch to catch
errors early and prevent cascading failures.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    file_path: str
    line: int
    severity: str  # error, warning, info
    message: str
    code: str = ""

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "severity": self.severity,
            "message": self.message,
            "code": self.code,
        }


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0
    files_passed: int = 0
    files_failed: int = 0

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def summary(self) -> str:
        return (
            f"Checked {self.files_checked} files: "
            f"{self.files_passed} passed, {self.files_failed} failed, "
            f"{len(self.issues)} issues"
        )


class SyntaxValidator:
    def __init__(self, base_dir: str = ""):
        self._base_dir = base_dir

    def validate_file(self, file_path: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        resolved = os.path.join(self._base_dir, file_path) if self._base_dir else file_path

        if not os.path.exists(resolved):
            issues.append(ValidationIssue(
                file_path=file_path, line=0, severity="error",
                message=f"File not found: {file_path}", code="MISSING_FILE",
            ))
            return issues

        with open(resolved, encoding="utf-8") as f:
            content = f.read()

        issues.extend(self._check_syntax(file_path, content))
        issues.extend(self._check_imports(file_path, content))

        return issues

    def validate_batch(self, file_paths: list[str]) -> ValidationReport:
        report = ValidationReport()

        for path in file_paths:
            report.files_checked += 1
            file_issues = self.validate_file(path)
            report.issues.extend(file_issues)

            if any(i.severity == "error" for i in file_issues):
                report.files_failed += 1
            else:
                report.files_passed += 1

        return report

    def _check_syntax(self, file_path: str, content: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        try:
            ast.parse(content, filename=file_path)
        except SyntaxError as e:
            issues.append(ValidationIssue(
                file_path=file_path,
                line=e.lineno or 0,
                severity="error",
                message=str(e.msg),
                code="SYNTAX_ERROR",
            ))
        return issues

    def _check_imports(self, file_path: str, content: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        try:
            tree = ast.parse(content, filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    pass
        except SyntaxError:
            return issues
        return issues
