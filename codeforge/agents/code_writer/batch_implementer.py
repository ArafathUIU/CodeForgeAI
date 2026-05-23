"""Batch implementer: generates code in structured chunks.

Orchestrates the core code generation by implementing files
in dependency order, validating each batch, and tracking
cross-file symbol references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codeforge.agents.code_writer.dependency_analyzer import DependencyAnalyzer
from codeforge.agents.code_writer.structured_editor import StructuredEditor
from codeforge.agents.code_writer.symbol_tracker import SymbolTracker
from codeforge.agents.code_writer.syntax_validator import SyntaxValidator, ValidationReport


@dataclass
class BatchResult:
    files_written: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)
    validation_report: ValidationReport | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.files_failed) == 0 and len(self.errors) == 0


class BatchImplementer:
    def __init__(
        self,
        editor: StructuredEditor,
        analyzer: DependencyAnalyzer,
        tracker: SymbolTracker,
        validator: SyntaxValidator,
    ):
        self._editor = editor
        self._analyzer = analyzer
        self._tracker = tracker
        self._validator = validator

    def implement(
        self,
        file_contents: dict[str, str],
        build_order: list[str] | None = None,
        batch_size: int = 5,
    ) -> BatchResult:
        result = BatchResult()

        if not build_order:
            all_files = list(file_contents.keys())
            build_order = self._analyzer.analyze(all_files, {})

        for i in range(0, len(build_order), batch_size):
            batch = build_order[i : i + batch_size]
            for file_path in batch:
                content = file_contents.get(file_path, "")
                if content:
                    try:
                        self._editor.create_file(file_path, content)
                        self._tracker.scan_file(file_path, content)
                        result.files_written.append(file_path)
                    except Exception as e:
                        result.files_failed.append(file_path)
                        result.errors.append(f"{file_path}: {e}")

        report = self._validator.validate_batch(result.files_written)
        result.validation_report = report

        if report.has_errors:
            for issue in report.issues:
                if issue.severity == "error":
                    result.errors.append(f"{issue.file_path}:{issue.line}: {issue.message}")

        return result

    def get_implementation_summary(self) -> dict[str, Any]:
        return {
            "editor": self._editor.get_summary(),
            "build_order": self._analyzer.build_order,
            "symbols": {
                name: [s.name for s in syms]
                for name, syms in self._tracker.get_all_symbols().items()
            },
        }
