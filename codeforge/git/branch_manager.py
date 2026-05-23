"""Branch manager: creates and manages Git branches.

Supports feature branching, branch switching, merging, and
list operations for the multi-agent workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


class BranchManager:
    def __init__(self, repo_path: str):
        self._repo_path = Path(repo_path)

    def create_branch(
        self, branch_name: str, switch: bool = True
    ) -> dict[str, Any]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            current = repo.active_branch
            new_branch = repo.create_head(branch_name)

            if switch:
                new_branch.checkout()

            logger.info(f"Branch created: {branch_name}")
            return {
                "branch": branch_name,
                "created": True,
                "switched": switch,
                "previous": current.name,
            }
        except Exception as e:
            logger.error(f"Branch creation failed: {e}")
            return {"error": str(e)}

    def switch_branch(self, branch_name: str) -> dict[str, Any]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            branch = getattr(repo.heads, branch_name.replace("-", "_"), None)
            if branch is None:
                branch = repo.create_head(branch_name)

            previous = repo.active_branch.name
            branch.checkout()
            logger.info(f"Switched to branch: {branch_name}")
            return {
                "branch": branch_name,
                "switched": True,
                "previous": previous,
            }
        except Exception as e:
            logger.error(f"Branch switch failed: {e}")
            return {"error": str(e)}

    def list_branches(self) -> list[dict[str, Any]]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            branches = []
            active = repo.active_branch.name if not repo.head.is_detached else ""

            for b in repo.heads:
                branches.append({
                    "name": b.name,
                    "is_active": b.name == active,
                    "commit": b.commit.hexsha[:8],
                })
            return branches
        except Exception:
            return []

    def merge_branch(
        self, source_branch: str, message: str = ""
    ) -> dict[str, Any]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            source = getattr(repo.heads, source_branch.replace("-", "_"), None)

            if source is None:
                return {"error": f"Branch not found: {source_branch}"}

            current = repo.active_branch.name
            merge_base = repo.merge_base(current, source_branch)

            repo.git.merge(source_branch, m=message or f"Merge {source_branch}")

            logger.info(f"Merged {source_branch} into {current}")
            return {
                "merged": True,
                "source": source_branch,
                "target": current,
            }
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return {"error": str(e)}

    def delete_branch(
        self, branch_name: str, force: bool = False
    ) -> dict[str, Any]:
        import git

        try:
            repo = git.Repo(self._repo_path)
            branch = getattr(repo.heads, branch_name.replace("-", "_"), None)

            if branch is None:
                return {"error": f"Branch not found: {branch_name}"}

            repo.delete_head(branch_name, force=force)
            logger.info(f"Branch deleted: {branch_name}")
            return {"deleted": True, "branch": branch_name}
        except Exception as e:
            logger.error(f"Branch deletion failed: {e}")
            return {"error": str(e)}
