"""Severity classifier for code review findings.

Classifies issues into: critical, high, medium, low, info.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewFinding:
    layer: str
    severity: Severity
    message: str
    file_path: str = ""
    line: int = 0
    auto_fixable: bool = False
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
            "auto_fixable": self.auto_fixable,
            "suggestion": self.suggestion,
        }


class SeverityClassifier:
    SEVERITY_PATTERNS: dict[str, Severity] = {
        "injection": Severity.CRITICAL,
        "xss": Severity.CRITICAL,
        "hardcoded_secret": Severity.CRITICAL,
        "sql_injection": Severity.CRITICAL,
        "command_injection": Severity.CRITICAL,
        "data_loss": Severity.HIGH,
        "race_condition": Severity.HIGH,
        "memory_leak": Severity.HIGH,
        "performance": Severity.MEDIUM,
        "complexity": Severity.MEDIUM,
        "duplication": Severity.MEDIUM,
        "style": Severity.LOW,
        "naming": Severity.LOW,
        "documentation": Severity.INFO,
        "convention": Severity.INFO,
    }

    def classify(
        self, finding: str, layer: str, context: str = ""
    ) -> Severity:
        lowered = (finding + " " + context).lower()
        for pattern, severity in self.SEVERITY_PATTERNS.items():
            if pattern in lowered:
                return severity
        return Severity.INFO

    def is_blocking(self, severity: Severity) -> bool:
        return severity in (Severity.CRITICAL, Severity.HIGH)

    def sort_by_severity(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        return sorted(findings, key=lambda f: order.get(f.severity, 99))
