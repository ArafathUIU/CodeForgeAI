"""Skeleton builder: generates empty file structure from file tree.

Creates the directory layout and empty files specified by the
System Architect's file tree before code implementation begins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from codeforge.agents.code_writer.structured_editor import StructuredEditor
from codeforge.artifacts.tech_spec import FileTreeNode


@dataclass
class SkeletonResult:
    files_created: list[str] = field(default_factory=list)
    directories_created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class SkeletonBuilder:
    def __init__(self, editor: StructuredEditor):
        self._editor = editor

    def build(self, file_tree: list[FileTreeNode]) -> SkeletonResult:
        result = SkeletonResult()
        dirs = set()

        for node in file_tree:
            try:
                if node.node_type == "directory":
                    self._editor._resolve(node.path)
                    import os
                    os.makedirs(self._editor._resolve(node.path), exist_ok=True)
                    dirs.add(node.path)
                    result.directories_created.append(node.path)
                elif node.node_type == "file":
                    parent = "/".join(node.path.split("/")[:-1])
                    if parent:
                        dirs.add(parent)
                        import os
                        os.makedirs(self._editor._resolve(parent), exist_ok=True)
                    header = f"# {node.path}\n# Purpose: {node.purpose}\n\n"
                    self._editor.create_file(node.path, header)
                    result.files_created.append(node.path)
            except Exception as e:
                result.errors.append(f"{node.path}: {e}")

        return result

    def generate_default_tree(
        self, project_name: str = "app"
    ) -> list[FileTreeNode]:
        nodes = [
            FileTreeNode(
                path=f"{project_name}/__init__.py",
                node_type="file",
                purpose="Package init",
            ),
            FileTreeNode(
                path=f"{project_name}/models.py",
                node_type="file",
                purpose="Data models",
            ),
            FileTreeNode(
                path=f"{project_name}/routes.py",
                node_type="file",
                purpose="API routes",
            ),
            FileTreeNode(
                path=f"{project_name}/services.py",
                node_type="file",
                purpose="Business logic",
            ),
            FileTreeNode(path="tests/__init__.py", node_type="file", purpose="Test package"),
            FileTreeNode(path="tests/test_models.py", node_type="file", purpose="Model tests"),
            FileTreeNode(path="tests/test_routes.py", node_type="file", purpose="Route tests"),
            FileTreeNode(path="requirements.txt", node_type="file", purpose="Dependencies"),
            FileTreeNode(path="README.md", node_type="file", purpose="Project docs"),
        ]
        return nodes
