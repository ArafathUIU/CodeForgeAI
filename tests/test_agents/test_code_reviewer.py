"""Tests for Code Reviewer Agent components."""

import pytest

from codeforge.agents.code_reviewer.analyzers import ReviewAnalyzers
from codeforge.agents.code_reviewer.auto_fixer import AutoFixer
from codeforge.agents.code_reviewer.severity import (
    ReviewFinding,
    Severity,
    SeverityClassifier,
)


class TestSeverityClassifier:
    @pytest.fixture
    def classifier(self):
        return SeverityClassifier()

    def test_classify_security_critical(self, classifier):
        severity = classifier.classify("sql_injection detected", "security")
        assert severity == Severity.CRITICAL

    def test_classify_style_low(self, classifier):
        severity = classifier.classify("naming convention", "style")
        assert severity == Severity.LOW

    def test_classify_fallback_info(self, classifier):
        severity = classifier.classify("some unknown thing", "unknown")
        assert severity == Severity.INFO

    def test_is_blocking(self, classifier):
        assert classifier.is_blocking(Severity.CRITICAL)
        assert classifier.is_blocking(Severity.HIGH)
        assert not classifier.is_blocking(Severity.MEDIUM)
        assert not classifier.is_blocking(Severity.LOW)

    def test_sort_by_severity(self, classifier):
        findings = [
            ReviewFinding("style", Severity.LOW, "low issue"),
            ReviewFinding("security", Severity.CRITICAL, "critical issue"),
            ReviewFinding("perf", Severity.MEDIUM, "medium issue"),
        ]
        sorted_findings = classifier.sort_by_severity(findings)
        assert sorted_findings[0].severity == Severity.CRITICAL
        assert sorted_findings[-1].severity == Severity.LOW


class TestReviewAnalyzers:
    @pytest.fixture
    def analyzers(self):
        return ReviewAnalyzers()

    def test_syntax_valid(self, analyzers):
        result = analyzers.analyze_syntax("test.py", "x = 1\ny = 2\n")
        assert not result.has_blockers
        assert result.score == 1.0

    def test_syntax_error(self, analyzers):
        result = analyzers.analyze_syntax("test.py", "def broken(\n")
        assert result.has_blockers
        assert result.score == 0.0

    def test_security_scan(self, analyzers):
        result = analyzers.analyze_security(
            "config.py", 'password = "admin123"\n'
        )
        assert len(result.findings) > 0

    def test_security_clean(self, analyzers):
        result = analyzers.analyze_security(
            "safe.py", "x = 1\ny = 2\n"
        )
        assert len(result.findings) == 0

    def test_style_tabs(self, analyzers):
        result = analyzers.analyze_style("test.py", "\tdef foo():\n\t\tpass\n")
        assert len(result.findings) > 0
        assert any(f.auto_fixable for f in result.findings)

    def test_performance_analysis(self, analyzers):
        result = analyzers.analyze_performance(
            "slow.py", "for i in range(len(items)):\n    pass\n"
        )
        assert len(result.findings) > 0

    def test_maintainability_long_lines(self, analyzers):
        long_line = "x = " + "a" * 130
        result = analyzers.analyze_maintainability("test.py", long_line)
        assert len(result.findings) > 0

    def test_run_all(self, analyzers):
        results = analyzers.run_all("test.py", "def foo():\n    return 1\n")
        assert len(results) == 6

    def test_aggregate_findings(self, analyzers):
        results = analyzers.run_all(
            "test.py",
            'password = "secret123"\n\tdef foo():\n\t\tpass\n'
        )
        findings = analyzers.aggregate_findings(results)
        assert len(findings) > 0

    def test_overall_score(self, analyzers):
        results = analyzers.run_all("clean.py", "x = 1\n")
        score = analyzers.overall_score(results)
        assert 0.0 <= score <= 1.0


class TestAutoFixer:
    @pytest.fixture
    def fixer(self):
        return AutoFixer()

    def test_fix_tabs(self, fixer):
        findings = [
            ReviewFinding(
                "style", Severity.LOW, "Tab character found",
                file_path="test.py", auto_fixable=True,
            ),
        ]
        contents = {"test.py": "\tdef foo():\n\t\tpass\n"}
        fixed = fixer.fix_findings(findings, contents)
        assert "\t" not in fixed["test.py"]

    def test_no_auto_fix_for_non_fixable(self, fixer):
        findings = [
            ReviewFinding(
                "security", Severity.CRITICAL, "SQL injection",
                file_path="test.py", auto_fixable=False,
            ),
        ]
        contents = {"test.py": "original"}
        fixed = fixer.fix_findings(findings, contents)
        assert fixed["test.py"] == "original"

    def test_get_fix_report(self, fixer):
        findings = [
            ReviewFinding("style", Severity.LOW, "tab", auto_fixable=True),
            ReviewFinding("security", Severity.CRITICAL, "injection", auto_fixable=False),
        ]
        report = fixer.get_fix_report(findings, fixed=True)
        assert report.fixed_count == 1
        assert report.unfixable_count == 1
