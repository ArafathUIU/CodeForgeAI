"""Coverage analyzer: estimates and reports code coverage.

Analyzes symbol usage and test completeness to estimate
code coverage when full instrumentation isn't available.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CoverageReport:
    total_symbols: int = 0
    tested_symbols: int = 0
    untested_symbols: int = 0
    coverage_percent: float = 0.0
    details: list[dict] = field(default_factory=list)

    @property
    def meets_threshold(self, target: float = 0.85) -> bool:
        return self.coverage_percent >= target

    def summary(self) -> str:
        return (
            f"Coverage: {self.coverage_percent:.1%} "
            f"({self.tested_symbols}/{self.total_symbols} symbols tested)"
        )


class CoverageAnalyzer:
    TARGET_COVERAGE = 0.85

    def __init__(self, target_coverage: float = 0.85):
        self.TARGET_COVERAGE = target_coverage

    def analyze(
        self,
        symbols: list,
        test_modules: list[str],
        test_content: dict[str, str] | None = None,
    ) -> CoverageReport:
        report = CoverageReport()
        report.total_symbols = len(symbols)

        test_text = ""
        if test_content:
            test_text = " ".join(test_content.values()).lower()

        for sym in symbols:
            name = getattr(sym, "name", sym)
            is_tested = name.lower() in test_text

            if is_tested:
                report.tested_symbols += 1
            else:
                report.untested_symbols += 1

            report.details.append({
                "symbol": name,
                "tested": is_tested,
            })

        if report.total_symbols > 0:
            report.coverage_percent = report.tested_symbols / report.total_symbols

        return report

    def suggest_missing_tests(self, report: CoverageReport) -> list[str]:
        suggestions: list[str] = []
        for detail in report.details:
            if not detail["tested"]:
                suggestions.append(
                    f"Add test for symbol: {detail['symbol']}"
                )
        return suggestions
