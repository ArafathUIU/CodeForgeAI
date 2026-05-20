"""Checkpoint and recovery system for project state persistence.

Every significant state change is persisted as a checkpoint - a complete
snapshot of the entire project state including artifacts, agent memories,
and decision history. Enables rollback to any previous state.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codeforge.utils.exceptions import CheckpointError
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Checkpoint:
    """A single checkpoint representing a complete project snapshot."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    phase: str = ""
    description: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    parent_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    episodic_memory: dict[str, Any] = field(default_factory=dict)
    semantic_memory: dict[str, Any] = field(default_factory=dict)
    agent_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    pipeline_state: dict[str, Any] = field(default_factory=dict)
    file_workspace_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "phase": self.phase,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
            "metadata": self.metadata,
            "artifacts": self.artifacts,
            "episodic_memory": self.episodic_memory,
            "semantic_memory": self.semantic_memory,
            "agent_states": self.agent_states,
            "pipeline_state": self.pipeline_state,
            "file_workspace_path": self.file_workspace_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            phase=data.get("phase", ""),
            description=data.get("description", ""),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(UTC),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {}),
            artifacts=data.get("artifacts", {}),
            episodic_memory=data.get("episodic_memory", {}),
            semantic_memory=data.get("semantic_memory", {}),
            agent_states=data.get("agent_states", {}),
            pipeline_state=data.get("pipeline_state", {}),
            file_workspace_path=data.get("file_workspace_path", ""),
        )


class CheckpointManager:
    """Manages creation, storage, listing, and restoration of checkpoints.

    Checkpoints are stored as JSON files in a configurable directory.
    Each checkpoint captures the complete project state at a point in time.
    """

    def __init__(self, storage_path: str | Path | None = None):
        if storage_path is None:
            from codeforge.utils.config import get_config
            storage_path = get_config().storage.checkpoint_path

        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._current_checkpoint_id: str | None = None
        self._checkpoints: dict[str, Checkpoint] = {}

    def create_checkpoint(
        self,
        name: str,
        *,
        phase: str = "",
        description: str = "",
        artifacts: dict[str, dict[str, Any]] | None = None,
        episodic_memory: dict[str, Any] | None = None,
        semantic_memory: dict[str, Any] | None = None,
        agent_states: dict[str, dict[str, Any]] | None = None,
        pipeline_state: dict[str, Any] | None = None,
        file_workspace_path: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint capturing current project state.

        Args:
            name: Human-readable name for this checkpoint.
            phase: Current pipeline phase when checkpoint was created.
            description: What changed since the last checkpoint.
            artifacts: Current state of all artifacts.
            episodic_memory: Current episodic memory state.
            semantic_memory: Current semantic memory state.
            agent_states: Current state of all agents.
            pipeline_state: Current pipeline execution state.
            file_workspace_path: Path to the file workspace snapshot.
            metadata: Additional custom metadata.

        Returns:
            The created Checkpoint object.
        """
        checkpoint = Checkpoint(
            name=name,
            phase=phase,
            description=description,
            parent_id=self._current_checkpoint_id,
            artifacts=artifacts or {},
            episodic_memory=episodic_memory or {},
            semantic_memory=semantic_memory or {},
            agent_states=agent_states or {},
            pipeline_state=pipeline_state or {},
            file_workspace_path=file_workspace_path,
            metadata=metadata or {},
        )

        self._checkpoints[checkpoint.id] = checkpoint
        self._current_checkpoint_id = checkpoint.id

        self._write_checkpoint(checkpoint)
        logger.info(
            f"Checkpoint created: {checkpoint.name} ({checkpoint.id[:8]})",
            extra={"checkpoint_id": checkpoint.id, "phase": phase},
        )

        return checkpoint

    def _write_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist a checkpoint to disk."""
        filepath = self._storage_path / f"{checkpoint.id}.json"
        data = checkpoint.to_dict()
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _read_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        """Load a checkpoint from disk."""
        filepath = self._storage_path / f"{checkpoint_id}.json"
        if not filepath.exists():
            raise CheckpointError(
                f"Checkpoint file not found: {filepath}",
                code="CHECKPOINT_FILE_MISSING",
            )
        with open(filepath) as f:
            data = json.load(f)
        return Checkpoint.from_dict(data)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        """Retrieve a checkpoint by ID."""
        if checkpoint_id in self._checkpoints:
            return self._checkpoints[checkpoint_id]
        checkpoint = self._read_checkpoint(checkpoint_id)
        self._checkpoints[checkpoint_id] = checkpoint
        return checkpoint

    def get_latest(self) -> Checkpoint | None:
        """Get the most recent checkpoint."""
        if not self._current_checkpoint_id:
            return None
        return self.get_checkpoint(self._current_checkpoint_id)

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints sorted by timestamp (newest first)."""
        checkpoints = [self._read_checkpoint(f.stem)
                       for f in self._storage_path.glob("*.json")
                       if f.stem not in self._checkpoints]

        for cp in checkpoints:
            if cp.id not in self._checkpoints:
                self._checkpoints[cp.id] = cp

        all_cps = list(self._checkpoints.values())
        return sorted(all_cps, key=lambda c: c.timestamp, reverse=True)

    def get_history(self) -> list[Checkpoint]:
        """Get the chain of checkpoints from earliest to latest."""
        if not self._current_checkpoint_id:
            return []

        history: list[Checkpoint] = []
        current_id = self._current_checkpoint_id

        while current_id:
            cp = self.get_checkpoint(current_id)
            history.append(cp)
            current_id = cp.parent_id

        return list(reversed(history))

    def get_parent(self, checkpoint_id: str) -> Checkpoint | None:
        """Get the parent checkpoint of a given checkpoint."""
        cp = self.get_checkpoint(checkpoint_id)
        if cp.parent_id:
            return self.get_checkpoint(cp.parent_id)
        return None

    def diff(
        self, checkpoint_a: str, checkpoint_b: str | None = None
    ) -> dict[str, Any]:
        """Compute the differences between two checkpoints.

        If checkpoint_b is None, compares checkpoint_a with its parent.
        """
        cp_a = self.get_checkpoint(checkpoint_a)
        cp_b = self.get_checkpoint(
            checkpoint_b or cp_a.parent_id or ""
        ) if checkpoint_b or cp_a.parent_id else None

        if cp_b is None:
            return {
                "from": None,
                "to": cp_a.id,
                "added_artifacts": list(cp_a.artifacts.keys()),
                "removed_artifacts": [],
                "modified_artifacts": [],
                "agent_changes": list(cp_a.agent_states.keys()),
            }

        diff_result: dict[str, Any] = {
            "from": cp_b.id,
            "to": cp_a.id,
            "added_artifacts": [],
            "removed_artifacts": [],
            "modified_artifacts": [],
            "agent_changes": [],
        }

        all_artifact_keys = set(cp_a.artifacts.keys()) | set(cp_b.artifacts.keys())
        for key in all_artifact_keys:
            in_a = key in cp_a.artifacts
            in_b = key in cp_b.artifacts
            if in_a and not in_b:
                diff_result["added_artifacts"].append(key)
            elif not in_a and in_b:
                diff_result["removed_artifacts"].append(key)
            elif cp_a.artifacts.get(key) != cp_b.artifacts.get(key):
                diff_result["modified_artifacts"].append(key)

        all_agent_keys = set(cp_a.agent_states.keys()) | set(cp_b.agent_states.keys())
        for key in all_agent_keys:
            if cp_a.agent_states.get(key) != cp_b.agent_states.get(key):
                diff_result["agent_changes"].append(key)

        return diff_result

    def rollback_to(self, checkpoint_id: str) -> Checkpoint:
        """Roll back the current state to a previous checkpoint.

        This sets the current checkpoint pointer to the specified checkpoint.
        The actual restoration of file workspace and agent states is handled
        by the Orchestrator using the checkpoint data.
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        self._current_checkpoint_id = checkpoint_id

        logger.info(
            f"Rolled back to checkpoint: {checkpoint.name} ({checkpoint_id[:8]})",
            extra={"checkpoint_id": checkpoint_id},
        )

        return checkpoint

    def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint and its file from disk."""
        filepath = self._storage_path / f"{checkpoint_id}.json"
        if filepath.exists():
            filepath.unlink()
        self._checkpoints.pop(checkpoint_id, None)

        if self._current_checkpoint_id == checkpoint_id:
            remaining = self.list_checkpoints()
            self._current_checkpoint_id = remaining[0].id if remaining else None

    def cleanup_old_checkpoints(
        self, keep_count: int = 10, older_than_hours: int | None = None
    ) -> int:
        """Remove old checkpoints, keeping the most recent ones.

        Args:
            keep_count: Number of recent checkpoints to preserve.
            older_than_hours: Also remove checkpoints older than this.

        Returns:
            Number of checkpoints removed.
        """
        all_cps = self.list_checkpoints()
        removed = 0

        to_remove = all_cps[keep_count:]
        now = datetime.now(UTC)

        if older_than_hours is not None:
            older = [
                cp for cp in all_cps
                if (now - cp.timestamp).total_seconds() > older_than_hours * 3600
            ]
            to_remove = list({cp.id: cp for cp in to_remove + older}.values())

        for cp in to_remove:
            if cp.id != self._current_checkpoint_id:
                self.delete_checkpoint(cp.id)
                removed += 1

        return removed

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the checkpoint system state."""
        all_cps = self.list_checkpoints()
        return {
            "total_checkpoints": len(all_cps),
            "current_checkpoint_id": self._current_checkpoint_id,
            "latest_checkpoint": (
                self._current_checkpoint_id[:8]
                if self._current_checkpoint_id
                else None
            ),
            "oldest_timestamp": all_cps[-1].timestamp.isoformat() if all_cps else None,
            "newest_timestamp": all_cps[0].timestamp.isoformat() if all_cps else None,
        }
