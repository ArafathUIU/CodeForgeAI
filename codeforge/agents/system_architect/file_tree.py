"""File tree generation for System Architect Agent."""

from codeforge.artifacts.tech_spec import FileTreeNode


class FileTreeGenerator:
    """Plans a FastAPI + Streamlit project layout."""

    def generate(self) -> list[FileTreeNode]:
        return [
            FileTreeNode("app/", "directory", "Application package"),
            FileTreeNode("app/main.py", "file", "FastAPI app entrypoint"),
            FileTreeNode("app/models.py", "file", "Data models"),
            FileTreeNode("app/schemas.py", "file", "Request and response schemas"),
            FileTreeNode("app/database.py", "file", "SQLite connection/session management"),
            FileTreeNode("app/routes.py", "file", "API route definitions"),
            FileTreeNode("frontend/", "directory", "Streamlit frontend"),
            FileTreeNode("frontend/app.py", "file", "Human-facing Streamlit UI"),
            FileTreeNode("tests/", "directory", "Automated tests"),
            FileTreeNode("tests/test_api.py", "file", "API behavior tests"),
            FileTreeNode("Dockerfile", "file", "Container build instructions"),
            FileTreeNode("docker-compose.yml", "file", "Local service orchestration"),
            FileTreeNode("README.md", "file", "Generated project documentation"),
        ]

    def render_tree(self, nodes: list[FileTreeNode]) -> str:
        lines = []
        for node in nodes:
            lines.append(f"{node.path} - {node.purpose}")
        return "\n".join(lines)
