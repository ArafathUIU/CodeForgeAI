"""Shared project memory: episodic and semantic state store.

All agents share access to a centralized state store recording every
decision, artifact, and conversation. Provides query interfaces and
context digest generation for fitting within LLM context windows.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codeforge.utils.config import get_config
from codeforge.utils.exceptions import StateNotFoundError, StateStoreError
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EpisodicEntry:
    """A single entry in episodic memory - a timestamped project event."""

    id: str
    type: str
    content: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    agent_id: str = ""
    phase: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class SemanticEntry:
    """A single entry in semantic memory - a reusable pattern or lesson."""

    id: str
    pattern: str
    description: str
    category: str
    confidence: float = 1.0
    source_project: str = ""
    usage_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EpisodicStore:
    """Stores and queries project-specific events and decisions."""

    def __init__(self, storage_path: str | None = None):
        self._entries: dict[str, EpisodicEntry] = {}
        self._lock = threading.Lock()
        self._storage_path = storage_path

    def add(
        self,
        entry_id: str,
        entry_type: str,
        content: dict[str, Any],
        *,
        agent_id: str = "",
        phase: str = "",
        tags: list[str] | None = None,
    ) -> EpisodicEntry:
        """Add a new entry to episodic memory."""
        entry = EpisodicEntry(
            id=entry_id,
            type=entry_type,
            content=content,
            agent_id=agent_id,
            phase=phase,
            tags=tags or [],
        )
        with self._lock:
            self._entries[entry_id] = entry
        logger.debug(
            f"Episodic entry added: {entry_id} ({entry_type})",
            extra={"entry_id": entry_id, "type": entry_type},
        )
        return entry

    def get(self, entry_id: str) -> EpisodicEntry:
        """Retrieve a specific entry by ID."""
        with self._lock:
            if entry_id not in self._entries:
                raise StateNotFoundError(
                    f"Episodic entry not found: {entry_id}",
                    code="ENTRY_NOT_FOUND",
                )
            return self._entries[entry_id]

    def query(
        self,
        *,
        entry_type: str | None = None,
        agent_id: str | None = None,
        phase: str | None = None,
        tags: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[EpisodicEntry]:
        """Query entries with optional filters."""
        with self._lock:
            results = list(self._entries.values())

            if entry_type:
                results = [e for e in results if e.type == entry_type]
            if agent_id:
                results = [e for e in results if e.agent_id == agent_id]
            if phase:
                results = [e for e in results if e.phase == phase]
            if tags:
                results = [e for e in results if any(t in e.tags for t in tags)]
            if since:
                results = [e for e in results if e.timestamp >= since]
            if until:
                results = [e for e in results if e.timestamp <= until]

            return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def get_all(self) -> list[EpisodicEntry]:
        """Get all entries sorted by timestamp (newest first)."""
        with self._lock:
            return sorted(
                self._entries.values(),
                key=lambda e: e.timestamp,
                reverse=True,
            )

    def delete(self, entry_id: str) -> None:
        """Delete an entry from memory."""
        with self._lock:
            if entry_id in self._entries:
                del self._entries[entry_id]

    def clear(self) -> None:
        """Clear all episodic entries."""
        with self._lock:
            self._entries.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize all entries to a dictionary."""
        with self._lock:
            return {
                eid: {
                    "id": entry.id,
                    "type": entry.type,
                    "content": entry.content,
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_id": entry.agent_id,
                    "phase": entry.phase,
                    "tags": entry.tags,
                }
                for eid, entry in self._entries.items()
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodicStore:
        """Deserialize an EpisodicStore from a dictionary."""
        store = cls()
        for entry_data in data.values():
            entry = EpisodicEntry(
                id=entry_data["id"],
                type=entry_data["type"],
                content=entry_data["content"],
                timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                agent_id=entry_data.get("agent_id", ""),
                phase=entry_data.get("phase", ""),
                tags=entry_data.get("tags", []),
            )
            store._entries[entry.id] = entry
        return store

    @property
    def count(self) -> int:
        return len(self._entries)


class SemanticStore:
    """Stores and queries cross-project patterns and lessons."""

    def __init__(self, storage_path: str | None = None):
        self._entries: dict[str, SemanticEntry] = {}
        self._lock = threading.Lock()
        self._storage_path = storage_path

    def add(
        self,
        entry_id: str,
        pattern: str,
        description: str,
        category: str,
        *,
        confidence: float = 1.0,
        source_project: str = "",
    ) -> SemanticEntry:
        """Add a new semantic pattern or lesson."""
        entry = SemanticEntry(
            id=entry_id,
            pattern=pattern,
            description=description,
            category=category,
            confidence=confidence,
            source_project=source_project,
        )
        with self._lock:
            self._entries[entry_id] = entry
        return entry

    def get(self, entry_id: str) -> SemanticEntry:
        """Retrieve a specific semantic entry."""
        with self._lock:
            if entry_id not in self._entries:
                raise StateNotFoundError(
                    f"Semantic entry not found: {entry_id}",
                    code="ENTRY_NOT_FOUND",
                )
            return self._entries[entry_id]

    def query(
        self,
        *,
        category: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[SemanticEntry]:
        """Query semantic entries with filters."""
        with self._lock:
            results = list(self._entries.values())
            if category:
                results = [e for e in results if e.category == category]
            if min_confidence > 0:
                results = [e for e in results if e.confidence >= min_confidence]
            return sorted(results, key=lambda e: e.usage_count, reverse=True)

    def search(self, query: str) -> list[SemanticEntry]:
        """Simple keyword search over patterns and descriptions."""
        query_lower = query.lower()
        with self._lock:
            return [
                e
                for e in self._entries.values()
                if query_lower in e.pattern.lower()
                or query_lower in e.description.lower()
            ]

    def increment_usage(self, entry_id: str) -> None:
        """Increment the usage counter for a semantic entry."""
        with self._lock:
            if entry_id in self._entries:
                self._entries[entry_id].usage_count += 1

    def get_all(self) -> list[SemanticEntry]:
        """Get all semantic entries."""
        with self._lock:
            return list(self._entries.values())

    def delete(self, entry_id: str) -> None:
        """Delete a semantic entry."""
        with self._lock:
            self._entries.pop(entry_id, None)

    def clear(self) -> None:
        """Clear all semantic entries."""
        with self._lock:
            self._entries.clear()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        with self._lock:
            return {
                eid: {
                    "id": entry.id,
                    "pattern": entry.pattern,
                    "description": entry.description,
                    "category": entry.category,
                    "confidence": entry.confidence,
                    "source_project": entry.source_project,
                    "usage_count": entry.usage_count,
                    "created_at": entry.created_at.isoformat(),
                }
                for eid, entry in self._entries.items()
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticStore:
        """Deserialize from dictionary."""
        store = cls()
        for entry_data in data.values():
            entry = SemanticEntry(
                id=entry_data["id"],
                pattern=entry_data["pattern"],
                description=entry_data["description"],
                category=entry_data["category"],
                confidence=entry_data.get("confidence", 1.0),
                source_project=entry_data.get("source_project", ""),
                usage_count=entry_data.get("usage_count", 0),
                created_at=datetime.fromisoformat(entry_data["created_at"]),
            )
            store._entries[entry.id] = entry
        return store

    @property
    def count(self) -> int:
        return len(self._entries)


class ContextDigestBuilder:
    """Builds condensed context digests for LLM context windows.

    Extracts the most relevant information from episodic and semantic
    stores, formatting it compactly for inclusion in agent prompts.
    """

    MAX_ENTRIES_PER_TYPE = 30
    MAX_TOTAL_CHARS = 8000

    def __init__(
        self,
        episodic: EpisodicStore,
        semantic: SemanticStore,
    ):
        self.episodic = episodic
        self.semantic = semantic

    def build_episodic_digest(
        self,
        *,
        phase: str | None = None,
        agent_id: str | None = None,
        entry_types: list[str] | None = None,
    ) -> str:
        """Build a condensed summary of relevant episodic entries."""
        entries = self.episodic.query(
            phase=phase,
            agent_id=agent_id,
        )

        if entry_types:
            entries = [e for e in entries if e.type in entry_types]

        entries = entries[: self.MAX_ENTRIES_PER_TYPE]

        if not entries:
            return "(No relevant project history)"

        lines = ["## Project History\n"]
        for entry in entries:
            ts = entry.timestamp.strftime("%H:%M:%S")
            content_summary = json.dumps(entry.content, default=str)[:200]
            lines.append(
                f"- [{ts}] [{entry.type}] {entry.agent_id}: {content_summary}"
            )

        digest = "\n".join(lines)
        if len(digest) > self.MAX_TOTAL_CHARS:
            digest = digest[: self.MAX_TOTAL_CHARS] + "\n... (truncated)"
        return digest

    def build_semantic_digest(self, *, query: str = "", category: str | None = None) -> str:
        """Build a summary of relevant semantic patterns."""
        if query:
            entries = self.semantic.search(query)
        else:
            entries = self.semantic.query(category=category)

        entries = entries[:10]

        if not entries:
            return "(No relevant patterns found)"

        lines = ["## Relevant Patterns\n"]
        for entry in entries:
            lines.append(
                f"- [{entry.category}] {entry.pattern}: {entry.description[:150]}"
                f" (confidence: {entry.confidence:.0%})"
            )

        return "\n".join(lines)

    def build_full_digest(
        self,
        *,
        phase: str | None = None,
        agent_id: str | None = None,
        include_semantic: bool = True,
        semantic_query: str = "",
    ) -> str:
        """Build a complete context digest for an agent's LLM prompt."""
        parts = []

        episodic = self.build_episodic_digest(phase=phase, agent_id=agent_id)
        parts.append(episodic)

        if include_semantic:
            parts.append("")
            semantic = self.build_semantic_digest(query=semantic_query)
            parts.append(semantic)

        return "\n".join(parts)
