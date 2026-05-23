"""Review analyzers: six-layer code review system.

1. Syntax Analysis
2. Security Scanning
3. Style Compliance
4. Performance Analysis
5. Maintainability Assessment
6. Architecture Compliance
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from codeforge.agents.code_reviewer.severity import (
    ReviewFinding,
    Severity,
    SeverityClassifier,
)


@dataclass
class AnalysisResult:
    layer: str
    findings: list[ReviewFinding] = field(default_factory=list)
    score: float = 1.0

    @property
    def has_blockers(self) -> bool:
        classifier = SeverityClassifier()
        return any(classifier.is_blocking(f.severity) for f in self.findings)


class ReviewAnalyzers:
    SECURITY_PATTERNS: list[tuple[str, str]] = [
        (r"os\.system\(", "command_injection"),
        (r"subprocess\.call\(", "command_injection"),
        (r"password\s*=\s*[\"'][^\"']+[\"']", "hardcoded_secret"),
        (r"secret\s*=\s*[\"'][^\"']+[\"']", "hardcoded_secret"),
        (r"api_key\s*=\s*[\"'][^\"']+[\"']", "hardcoded_secret"),
        (r"\.execute\s*\(\s*f[\"']", "sql_injection"),
    ]

    STYLE_PATTERNS: list[tuple[str, str]] = [
        (r"\t", "tabs_found"),
        (r"def [a-z]", "naming"),
        (r"class [A-Z][a-z]", "naming"),
    ]

    PERFORMANCE_PATTERNS: list[tuple[str, str]] = [
        (r"for .+ in range\(len\(", "inefficient_loop"),
        (r"\.copy\(\)", "unnecessary_copy"),
    ]

    def __init__(self):
        self._classifier = SeverityClassifier()

    def analyze_syntax(
        self, file_path: str, content: str
    ) -> AnalysisResult:
        result = AnalysisResult(layer="syntax")
        try:
            ast.parse(content, filename=file_path)
        except SyntaxError as e:
            result.findings.append(ReviewFinding(
                layer="syntax",
                severity=Severity.CRITICAL,
                message=f"Syntax error: {e.msg}",
                file_path=file_path,
                line=e.lineno or 0,
            ))
            result.score = 0.0
        return result

    def analyze_security(
        self, file_path: str, content: str
    ) -> AnalysisResult:
        result = AnalysisResult(layer="security")
        for pattern, issue_type in self.SECURITY_PATTERNS:
            for m in re.finditer(pattern, content, re.IGNORECASE):
                line_no = content[: m.start()].count("\n") + 1
                severity = self._classifier.classify(issue_type, "security")
                result.findings.append(ReviewFinding(
                    layer="security",
                    severity=severity,
                    message=f"Potential {issue_type} detected",
                    file_path=file_path,
                    line=line_no,
                ))
        if result.findings:
            result.score = max(0.0, 1.0 - len(result.findings) * 0.2)
        return result

    def analyze_style(
        self, file_path: str, content: str
    ) -> AnalysisResult:
        result = AnalysisResult(layer="style")
        issues = 0
        for pattern, issue_type in self.STYLE_PATTERNS:
            for m in re.finditer(pattern, content):
                if m.group().startswith("\t"):
                    line_no = content[: m.start()].count("\n") + 1
                    result.findings.append(ReviewFinding(
                        layer="style",
                        severity=Severity.LOW,
                        message="Tab character found; use spaces",
                        file_path=file_path,
                        line=line_no,
                        auto_fixable=True,
                    ))
                    issues += 1
        if issues:
            result.score = max(0.0, 1.0 - issues * 0.1)
        return result

    def analyze_performance(
        self, file_path: str, content: str
    ) -> AnalysisResult:
        result = AnalysisResult(layer="performance")
        for pattern, issue_type in self.PERFORMANCE_PATTERNS:
            for m in re.finditer(pattern, content):
                line_no = content[: m.start()].count("\n") + 1
                result.findings.append(ReviewFinding(
                    layer="performance",
                    severity=Severity.MEDIUM,
                    message=f"Performance concern: {issue_type}",
                    file_path=file_path,
                    line=line_no,
                ))
        return result

    def analyze_maintainability(
        self, file_path: str, content: str
    ) -> AnalysisResult:
        result = AnalysisResult(layer="maintainability")
        lines = content.split("\n")
        for i, line in enumerate(lines, start=1):
            if len(line) > 120:
                result.findings.append(ReviewFinding(
                    layer="maintainability",
                    severity=Severity.LOW,
                    message="Line exceeds 120 characters",
                    file_path=file_path,
                    line=i,
                ))
        if result.findings:
            result.score = max(0.0, 1.0 - len(result.findings) * 0.05)
        return result

    def analyze_architecture(
        self, file_path: str, content: str, expected_structure: dict | None = None
    ) -> AnalysisResult:
        result = AnalysisResult(layer="architecture")
        if not expected_structure:
            return result
        return result

    def run_all(
        self, file_path: str, content: str
    ) -> list[AnalysisResult]:
        return [
            self.analyze_syntax(file_path, content),
            self.analyze_security(file_path, content),
            self.analyze_style(file_path, content),
            self.analyze_performance(file_path, content),
            self.analyze_maintainability(file_path, content),
            self.analyze_architecture(file_path, content),
        ]

    def aggregate_findings(
        self, results: list[AnalysisResult]
    ) -> list[ReviewFinding]:
        all_findings: list[ReviewFinding] = []
        for r in results:
            all_findings.extend(r.findings)
        return self._classifier.sort_by_severity(all_findings)

    def overall_score(self, results: list[AnalysisResult]) -> float:
        if not results:
            return 1.0
        return sum(r.score for r in results) / len(results)
