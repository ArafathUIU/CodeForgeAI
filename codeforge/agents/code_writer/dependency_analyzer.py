"""Dependency analyzer: determines correct file build order.

Analyzes import statements and type references to figure out
which files must be implemented before others.
"""

from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class FileDependency:
    file_path: str
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    rank: int = 0


class DependencyAnalyzer:
    IMPORT_RE = re.compile(
        r"^(?:from\s+(\S+)\s+import|import\s+(\S+))", re.MULTILINE
    )

    def __init__(self, project_root: str = ""):
        self._project_root = project_root
        self._dependencies: dict[str, FileDependency] = {}
        self._build_order: list[str] = []

    def analyze(
        self, file_list: list[str], file_contents: dict[str, str] | None = None
    ) -> list[str]:
        self._dependencies.clear()
        graph: dict[str, list[str]] = defaultdict(list)
        indegree: dict[str, int] = defaultdict(int)

        for file_path in file_list:
            if file_path not in graph:
                graph[file_path] = []
            indegree.setdefault(file_path, 0)

            content = (file_contents or {}).get(file_path, "")
            imports = self._extract_imports(content, file_path)

            dep = FileDependency(file_path=file_path, imports=imports)
            self._dependencies[file_path] = dep

            for imp in imports:
                parts = imp.lstrip(".")
                normalized = self._normalize_path(parts, file_path)
                if normalized and normalized in file_list and normalized != file_path:
                    graph[normalized].append(file_path)
                    indegree[file_path] += 1

        queue: deque[str] = deque()
        for f in file_list:
            if indegree.get(f, 0) == 0:
                queue.append(f)

        result: list[str] = []
        while queue:
            current = queue.popleft()
            result.append(current)
            for dependent in graph.get(current, []):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(file_list):
            remaining = set(file_list) - set(result)
            result.extend(sorted(remaining))

        for i, f in enumerate(result):
            if f in self._dependencies:
                self._dependencies[f].rank = i

        self._build_order = result
        return result

    @property
    def build_order(self) -> list[str]:
        return list(self._build_order)

    def get_dependency(self, file_path: str) -> FileDependency | None:
        return self._dependencies.get(file_path)

    def _extract_imports(self, content: str, source_file: str) -> list[str]:
        imports: list[str] = []
        for m in self.IMPORT_RE.finditer(content):
            resolved = m.group(1) or m.group(2)
            if resolved:
                imports.append(resolved.strip())
        return imports

    def _normalize_path(self, import_path: str, source_file: str) -> str | None:
        if import_path.startswith("."):
            return None
        as_file = import_path.replace(".", "/") + ".py"
        return as_file
