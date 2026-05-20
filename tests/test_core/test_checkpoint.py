"""Tests for the checkpoint system."""

from codeforge.core.checkpoint import CheckpointManager


class TestCheckpointManager:
    def test_create_checkpoint(self, checkpoint_manager):
        cp = checkpoint_manager.create_checkpoint(
            name="Test Checkpoint",
            phase="requirements",
            description="Testing checkpoint",
            artifacts={"prd": {"version": "1.0"}},
        )
        assert cp.name == "Test Checkpoint"
        assert cp.phase == "requirements"
        assert cp.artifacts == {"prd": {"version": "1.0"}}

    def test_get_checkpoint(self, checkpoint_manager):
        cp = checkpoint_manager.create_checkpoint(name="CP1")
        retrieved = checkpoint_manager.get_checkpoint(cp.id)
        assert retrieved.id == cp.id
        assert retrieved.name == "CP1"

    def test_get_latest(self, checkpoint_manager):
        cp1 = checkpoint_manager.create_checkpoint(name="First")
        cp2 = checkpoint_manager.create_checkpoint(name="Second")
        latest = checkpoint_manager.get_latest()
        assert latest.id == cp2.id

    def test_list_checkpoints(self, checkpoint_manager):
        checkpoint_manager.create_checkpoint(name="CP1")
        checkpoint_manager.create_checkpoint(name="CP2")
        all_cps = checkpoint_manager.list_checkpoints()
        assert len(all_cps) == 2

    def test_get_history_returns_ordered_chain(self, checkpoint_manager):
        cp1 = checkpoint_manager.create_checkpoint(name="CP1")
        cp2 = checkpoint_manager.create_checkpoint(name="CP2")
        history = checkpoint_manager.get_history()
        assert len(history) == 2
        assert history[0].id == cp1.id
        assert history[1].id == cp2.id

    def test_parent_child_relationship(self, checkpoint_manager):
        cp1 = checkpoint_manager.create_checkpoint(name="Parent")
        cp2 = checkpoint_manager.create_checkpoint(name="Child")
        parent = checkpoint_manager.get_parent(cp2.id)
        assert parent is not None
        assert parent.id == cp1.id

    def test_diff_between_checkpoints(self, checkpoint_manager):
        cp1 = checkpoint_manager.create_checkpoint(
            name="CP1",
            artifacts={"a": {"v": 1}, "b": {"v": 2}},
        )
        cp2 = checkpoint_manager.create_checkpoint(
            name="CP2",
            artifacts={"a": {"v": 1}, "c": {"v": 3}},
        )
        diff = checkpoint_manager.diff(cp2.id, cp1.id)
        assert "c" in diff["added_artifacts"]
        assert "b" in diff["removed_artifacts"]

    def test_rollback_changes_current(self, checkpoint_manager):
        cp1 = checkpoint_manager.create_checkpoint(name="CP1")
        cp2 = checkpoint_manager.create_checkpoint(name="CP2")
        checkpoint_manager.rollback_to(cp1.id)
        latest = checkpoint_manager.get_latest()
        assert latest.id == cp1.id

    def test_delete_checkpoint(self, checkpoint_manager):
        cp = checkpoint_manager.create_checkpoint(name="ToDelete")
        cp2 = checkpoint_manager.create_checkpoint(name="Keep")
        checkpoint_manager.delete_checkpoint(cp.id)
        all_cps = checkpoint_manager.list_checkpoints()
        assert len(all_cps) == 1
        assert all_cps[0].id == cp2.id

    def test_cleanup_old_checkpoints(self, checkpoint_manager):
        for i in range(15):
            checkpoint_manager.create_checkpoint(name=f"CP{i}")
        removed = checkpoint_manager.cleanup_old_checkpoints(keep_count=5)
        assert removed == 10
        remaining = checkpoint_manager.list_checkpoints()
        assert len(remaining) >= 5

    def test_get_summary(self, checkpoint_manager):
        checkpoint_manager.create_checkpoint(name="CP1")
        summary = checkpoint_manager.get_summary()
        assert summary["total_checkpoints"] == 1
        assert summary["current_checkpoint_id"] is not None
