"""Auto-fixer: automatically fixes common style issues.

Handles automatic corrections for low-severity, auto-fixable
review findings like tab characters, trailing whitespace, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from codeforge.agents.code_reviewer.severity import ReviewFinding


@dataclass
class FixResult:
    file_path: str
    fixed_count: int = 0
    unfixable_count: int = 0
    details: list[str] = field(default_factory=list)


class AutoFixer:
    def fix_findings(
        self, findings: list[ReviewFinding], file_contents: dict[str, str]
    ) -> dict[str, str]:
        result: dict[str, str] = dict(file_contents)
        fixes_by_file: dict[str, list[ReviewFinding]] = {}

        for f in findings:
            if f.auto_fixable and f.file_path:
                fixes_by_file.setdefault(f.file_path, []).append(f)

        for file_path, file_findings in fixes_by_file.items():
            if file_path in result:
                content = result[file_path]
                for finding in file_findings:
                    if "tab" in finding.message.lower():
                        content = content.replace("\t", "    ")
                    elif "trailing" in finding.message.lower():
                        lines = content.split("\n")
                        lines = [line.rstrip() for line in lines]
                        content = "\n".join(lines)
                result[file_path] = content

        return result

    def get_fix_report(
        self, findings: list[ReviewFinding], fixed: bool
    ) -> FixResult:
        auto_fixable = [f for f in findings if f.auto_fixable]
        return FixResult(
            file_path="",
            fixed_count=len(auto_fixable) if fixed else 0,
            unfixable_count=len([f for f in findings if not f.auto_fixable]),
            details=[f.message for f in auto_fixable],
        )
