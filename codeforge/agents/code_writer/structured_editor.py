"""Structured file editor using search-and-replace operations.

Instead of regenerating entire files, uses precise edit operations
to minimize disruption and preserve human-authored content.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class EditOp:
    type: str  # create, modify, delete, move, rename
    path: str
    content: str = ""
    new_path: str = ""
    old_string: str = ""
    new_string: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "path": self.path,
            "content": self.content[:200],
            "new_path": self.new_path,
        }


class FileOperationError(Exception):
    pass


class StructuredEditor:
    def __init__(self, base_dir: str = ""):
        self._base_dir = base_dir
        self._operations: list[EditOp] = []
        self._files_written: set[str] = set()
        self._files_deleted: set[str] = set()

    @property
    def operations(self) -> list[EditOp]:
        return list(self._operations)

    @property
    def files_created(self) -> list[str]:
        return sorted(self._files_written)

    def _resolve(self, path: str) -> str:
        if self._base_dir:
            return os.path.join(self._base_dir, path)
        return path

    def create_file(self, path: str, content: str) -> EditOp:
        resolved = self._resolve(path)
        os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        op = EditOp(type="create", path=path, content=content)
        self._operations.append(op)
        self._files_written.add(path)
        return op

    def modify_file(self, path: str, old_string: str, new_string: str) -> EditOp:
        resolved = self._resolve(path)
        if not os.path.exists(resolved):
            raise FileOperationError(f"File not found for modify: {path}")
        with open(resolved, encoding="utf-8") as f:
            content = f.read()
        if old_string not in content:
            raise FileOperationError(f"Search string not found in {path}")
        updated = content.replace(old_string, new_string, 1)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(updated)
        op = EditOp(
            type="modify",
            path=path,
            old_string=old_string[:200],
            new_string=new_string[:200],
        )
        self._operations.append(op)
        return op

    def delete_file(self, path: str) -> EditOp:
        resolved = self._resolve(path)
        if os.path.exists(resolved):
            os.remove(resolved)
        op = EditOp(type="delete", path=path)
        self._operations.append(op)
        self._files_deleted.add(path)
        return op

    def move_file(self, source: str, dest: str) -> EditOp:
        resolved_src = self._resolve(source)
        resolved_dst = self._resolve(dest)
        if not os.path.exists(resolved_src):
            raise FileOperationError(f"Source not found for move: {source}")
        os.makedirs(os.path.dirname(resolved_dst) or ".", exist_ok=True)
        os.replace(resolved_src, resolved_dst)
        op = EditOp(type="move", path=source, new_path=dest)
        self._operations.append(op)
        if source in self._files_written:
            self._files_written.discard(source)
        self._files_written.add(dest)
        return op

    def file_exists(self, path: str) -> bool:
        return os.path.exists(self._resolve(path))

    def read_file(self, path: str) -> str:
        resolved = self._resolve(path)
        if not os.path.exists(resolved):
            raise FileOperationError(f"File not found: {path}")
        with open(resolved, encoding="utf-8") as f:
            return f.read()

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_operations": len(self._operations),
            "files_created": sorted(self._files_written),
            "files_deleted": sorted(self._files_deleted),
            "operations": [op.to_dict() for op in self._operations],
        }
