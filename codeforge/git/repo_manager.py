"""Repository manager: initializes and manages Git repositories.

Handles repo creation, remote configuration, status checks,
and provides the foundation for all Git operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RepoInfo:
    path: str
    branch: str = "main"
    remote_url: str = ""
    is_dirty: bool = False
    file_count: int = 0
    last_commit: str = ""


class RepoManager:
    def __init__(self, repo_path: str):
        self._repo_path = Path(repo_path)
        self._initialized = False

    @property
    def path(self) -> str:
        return str(self._repo_path)

    def initialize(
        self,
        author_name: str = "CodeForge AI",
        author_email: str = "codeforge@ai.local",
        remote_url: str = "",
    ) -> dict[str, Any]:
        if not self._repo_path.exists():
            self._repo_path.mkdir(parents=True)

        git_dir = self._repo_path / ".git"
        if not git_dir.exists():
            import git

            repo = git.Repo.init(self._repo_path)

            with repo.config_writer() as config:
                config.set_value("user", "name", author_name)
                config.set_value("user", "email", author_email)

            if remote_url:
                try:
                    repo.create_remote("origin", remote_url)
                except Exception:
                    pass

            self._initialized = True
            logger.info(f"Git repo initialized at {self._repo_path}")
            return {"status": "created", "path": str(self._repo_path)}

        self._initialized = True
        return {"status": "exists", "path": str(self._repo_path)}

    def get_status(self) -> dict[str, Any]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            try:
                branch_name = repo.active_branch.name if not repo.head.is_detached else "detached"
            except (TypeError, ValueError):
                branch_name = "main"

            untracked = repo.untracked_files
            changed = [item.a_path for item in repo.index.diff(None)]
            try:
                staged = [item.a_path for item in repo.index.diff("HEAD")]
            except Exception:
                staged = []

            return {
                "branch": branch_name,
                "untracked_files": untracked,
                "changed_files": changed,
                "staged_files": staged,
                "is_dirty": bool(untracked or changed or staged),
            }
        except Exception:
            return {
                "branch": "unknown",
                "is_dirty": False,
                "error": "Not a valid git repository",
            }

    def create_gitignore(self, patterns: list[str] | None = None) -> str:
        defaults = [
            "__pycache__/",
            "*.pyc",
            ".env",
            ".codeforge/",
            "*.egg-info/",
            "dist/",
            "build/",
            ".pytest_cache/",
        ]
        all_patterns = defaults + (patterns or [])
        gitignore_path = self._repo_path / ".gitignore"
        content = "\n".join(all_patterns) + "\n"
        gitignore_path.write_text(content, encoding="utf-8")
        logger.info("Created .gitignore")
        return str(gitignore_path)

    def is_git_repo(self) -> bool:
        return (self._repo_path / ".git").exists()

    def get_repo_info(self) -> RepoInfo:
        status = self.get_status()
        return RepoInfo(
            path=str(self._repo_path),
            branch=status.get("branch", "main"),
            is_dirty=status.get("is_dirty", False),
            file_count=len(list(self._repo_path.rglob("*"))),
        )
