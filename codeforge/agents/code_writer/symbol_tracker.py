"""Symbol tracker: cross-file symbol reference tracking.

Tracks classes, functions, and variables across files to ensure
cross-file consistency during implementation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Symbol:
    name: str
    kind: str  # class, function, variable, import
    file_path: str
    line: int = 0
    exported: bool = True


class SymbolTracker:
    CLASS_RE = re.compile(r"^class\s+(\w+)", re.MULTILINE)
    FUNC_RE = re.compile(r"^(?:async\s+)?def\s+(\w+)", re.MULTILINE)
    VAR_RE = re.compile(r"^(\w+)\s*[:=]", re.MULTILINE)

    def __init__(self):
        self._symbols: dict[str, list[Symbol]] = {}  # file_path -> symbols
        self._name_index: dict[str, list[Symbol]] = {}  # symbol_name -> definitions
        self._references: dict[str, list[tuple[str, int]]] = {}  # file -> [(symbol, line)]

    def scan_file(self, file_path: str, content: str) -> list[Symbol]:
        symbols: list[Symbol] = []
        lines = content.split("\n")

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""'):
                continue

            class_match = self.CLASS_RE.match(stripped)
            if class_match:
                sym = Symbol(name=class_match.group(1), kind="class", file_path=file_path, line=i)
                symbols.append(sym)
                continue

            func_match = self.FUNC_RE.match(stripped)
            if func_match:
                sym = Symbol(name=func_match.group(1), kind="function", file_path=file_path, line=i)
                symbols.append(sym)

        for sym in symbols:
            self._name_index.setdefault(sym.name, []).append(sym)

        self._symbols[file_path] = symbols
        return symbols

    def resolve_reference(self, symbol_name: str, referencing_file: str) -> Symbol | None:
        candidates = self._name_index.get(symbol_name, [])
        if not candidates:
            return None

        same_file = [s for s in candidates if s.file_path == referencing_file]
        if same_file:
            return same_file[0]

        return candidates[0]

    def get_unresolved(
        self, file_contents: dict[str, str]
    ) -> list[tuple[str, str, int]]:
        unresolved: list[tuple[str, str, int]] = []
        ref_re = re.compile(r"\b([A-Z]\w+|[a-z_]\w+)\s*\(")

        for file_path, content in file_contents.items():
            for m in ref_re.finditer(content):
                name = m.group(1)
                if not self._is_builtin(name):
                    if name not in self._name_index:
                        unresolved.append((file_path, name, 0))
        return unresolved

    def get_file_symbols(self, file_path: str) -> list[Symbol]:
        return self._symbols.get(file_path, [])

    def get_definition(self, symbol_name: str) -> Symbol | None:
        defs = self._name_index.get(symbol_name, [])
        return defs[0] if defs else None

    def get_all_symbols(self) -> dict[str, list[Symbol]]:
        return dict(self._name_index)

    @staticmethod
    def _is_builtin(name: str) -> bool:
        builtins = {
            "print", "len", "range", "int", "str", "float", "bool",
            "list", "dict", "set", "tuple", "type", "isinstance",
            "open", "enumerate", "zip", "map", "filter", "sorted",
            "super", "any", "all", "min", "max", "sum", "abs",
            "hasattr", "getattr", "setattr", "issubclass", "Exception",
            "ValueError", "TypeError", "KeyError", "IndexError",
            "AttributeError", "RuntimeError", "os", "sys", "json",
            "datetime", "re", "uuid", "asyncio", "pathlib",
        }
        return name in builtins or name.startswith("__")
