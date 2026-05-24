"""CI/CD generator: produces GitHub Actions workflow files.

Generates complete CI/CD pipeline configurations with linting,
testing, building, and deployment stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CICDConfig:
    project_name: str = "app"
    python_versions: list[str] = field(default_factory=lambda: ["3.11", "3.12"])
    test_command: str = "pytest"
    lint_command: str = "ruff check ."
    docker_build: bool = True
    deploy_branch: str = "main"


class CICDGenerator:
    def generate_github_actions(self, config: CICDConfig) -> str:
        lines = [
            "name: CI/CD",
            "",
            "on:",
            "  push:",
            f"    branches: [{config.deploy_branch}]",
            "  pull_request:",
            f"    branches: [{config.deploy_branch}]",
            "",
            "jobs:",
            "  test:",
            "    name: Test",
            "    runs-on: ubuntu-latest",
            "    strategy:",
            "      fail-fast: false",
            "      matrix:",
            "        python-version:",
        ]

        for v in config.python_versions:
            lines.append(f"          - '{v}'")

        lines.extend([
            "",
            "    steps:",
            "      - uses: actions/checkout@v4",
            "",
            "      - name: Set up Python ${{ matrix.python-version }}",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: ${{ matrix.python-version }}",
            "          cache: pip",
            "",
            "      - name: Install dependencies",
            "        run: |",
            "          python -m pip install --upgrade pip",
            '          python -m pip install -e ".[dev]"',
            "",
            "      - name: Lint",
            f"        run: {config.lint_command}",
            "",
            "      - name: Test",
            f"        run: {config.test_command}",
        ])

        if config.docker_build:
            lines.extend([
                "",
                "  build:",
                "    name: Build Docker image",
                "    runs-on: ubuntu-latest",
                "    needs: test",
                "    if: github.ref == 'refs/heads/main'",
                "",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "",
                "      - name: Build image",
                f"        run: docker build -t {config.project_name} .",
            ])

        return "\n".join(lines) + "\n"

    def generate_env_template(self) -> str:
        return (
            "# Environment Configuration\n"
            "APP_NAME=app\n"
            "APP_PORT=8000\n"
            "DEBUG=false\n"
            "LOG_LEVEL=info\n"
            "\n"
            "# Database\n"
            "DATABASE_URL=sqlite:///./app.db\n"
            "\n"
            "# Secrets (set these in your environment, never commit)\n"
            "SECRET_KEY=change-me-in-production\n"
            "API_KEY=\n"
        )
