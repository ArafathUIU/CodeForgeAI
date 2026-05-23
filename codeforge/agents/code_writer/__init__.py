"""Code Writer Agent: implements software from technical specifications."""

from codeforge.agents.code_writer.agent import CodeWriterAgent
from codeforge.agents.code_writer.batch_implementer import BatchImplementer, BatchResult
from codeforge.agents.code_writer.dependency_analyzer import DependencyAnalyzer, FileDependency
from codeforge.agents.code_writer.skeleton_builder import SkeletonBuilder, SkeletonResult
from codeforge.agents.code_writer.structured_editor import EditOp, StructuredEditor
from codeforge.agents.code_writer.symbol_tracker import Symbol, SymbolTracker
from codeforge.agents.code_writer.syntax_validator import (
    SyntaxValidator,
    ValidationIssue,
    ValidationReport,
)

__all__ = [
    "BatchImplementer",
    "BatchResult",
    "CodeWriterAgent",
    "DependencyAnalyzer",
    "EditOp",
    "FileDependency",
    "SkeletonBuilder",
    "SkeletonResult",
    "StructuredEditor",
    "Symbol",
    "SymbolTracker",
    "SyntaxValidator",
    "ValidationIssue",
    "ValidationReport",
]
