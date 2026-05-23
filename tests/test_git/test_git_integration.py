"""Tests for Git integration modules."""

import pytest

from codeforge.git.repo_manager import RepoManager
from codeforge.git.commit_manager import CommitManager
from codeforge.git.branch_manager import BranchManager


class TestRepoManager:
    @pytest.fixture
    def repo_manager(self, tmp_path):
        return RepoManager(str(tmp_path / "test_repo"))

    def test_initialize_creates_git_repo(self, repo_manager):
        result = repo_manager.initialize()
        assert result["status"] in ("created", "exists")
        assert repo_manager.is_git_repo()

    def test_initialize_twice_is_idempotent(self, repo_manager):
        repo_manager.initialize()
        result = repo_manager.initialize()
        assert result["status"] == "exists"

    def test_get_status_on_clean_repo(self, repo_manager):
        repo_manager.initialize()
        status = repo_manager.get_status()
        assert "branch" in status
        assert status["is_dirty"] is False

    def test_create_gitignore(self, repo_manager):
        repo_manager.initialize()
        path = repo_manager.create_gitignore()
        assert ".gitignore" in path
        import os
        content = open(path).read()
        assert "__pycache__" in content

    def test_get_repo_info(self, repo_manager):
        repo_manager.initialize()
        repo_manager.create_gitignore()
        cm = CommitManager(str(repo_manager._repo_path))
        cm.commit("Initial commit", agent="test")
        info = repo_manager.get_repo_info()
        assert info.branch in ("main", "master")


class TestCommitManager:
    @pytest.fixture
    def commit_manager(self, tmp_path):
        repo_path = tmp_path / "commit_test"
        rm = RepoManager(str(repo_path))
        rm.initialize()
        return CommitManager(str(repo_path))

    def test_commit_creates_sha(self, commit_manager):
        import os
        test_file = os.path.join(
            str(commit_manager._repo_path), "test.py"
        )
        with open(test_file, "w") as f:
            f.write("# test file\n")
        result = commit_manager.commit(
            "Initial commit", files=["test.py"],
            phase="testing", agent="test_engineer",
        )
        assert result["sha"]
        assert len(result["short_sha"]) == 8

    def test_get_commit_history_empty(self, commit_manager):
        history = commit_manager.get_commit_history()
        assert isinstance(history, list)

    def test_commit_without_specific_files(self, commit_manager):
        result = commit_manager.commit("Empty commit")
        assert isinstance(result, dict)


class TestBranchManager:
    @pytest.fixture
    def branch_manager(self, tmp_path):
        repo_path = tmp_path / "branch_test"
        rm = RepoManager(str(repo_path))
        rm.initialize()
        rm.create_gitignore()
        cm = CommitManager(str(repo_path))
        cm.commit("Initial commit", agent="test")
        return BranchManager(str(repo_path))

    def test_create_branch(self, branch_manager):
        result = branch_manager.create_branch("feature/test")
        assert result["branch"] == "feature/test"
        assert result["created"]

    def test_list_branches(self, branch_manager):
        branch_manager.create_branch("feature/a")
        branch_manager.create_branch("feature/b")
        branches = branch_manager.list_branches()
        assert len(branches) >= 3

    def test_switch_branch(self, branch_manager):
        branch_manager.create_branch("feature/x")
        branch_manager.create_branch("feature/y")
        result = branch_manager.switch_branch("feature/x")
        assert result["branch"] == "feature/x"
