"""Dockerfile generator: produces multi-stage Dockerfiles.

Generates optimized Dockerfiles with separate build and production
stages, non-root users, and health check configurations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DockerfileConfig:
    base_image: str = "python:3.11-slim"
    app_name: str = "app"
    port: int = 8000
    build_deps: list[str] = field(default_factory=list)
    run_deps: list[str] = field(default_factory=list)
    non_root_user: str = "appuser"
    health_check_endpoint: str = "/health"


class DockerfileGenerator:
    def generate(self, config: DockerfileConfig) -> str:
        lines = [
            "# Stage 1: Build",
            f"FROM {config.base_image} AS builder",
            "",
            "WORKDIR /build",
            "COPY requirements.txt .",
            "RUN pip install --user --no-cache-dir -r requirements.txt",
            "",
            "# Stage 2: Production",
            f"FROM {config.base_image} AS production",
            "",
            "RUN groupadd -r appgroup && useradd -r -g appgroup appuser",
            "",
            "WORKDIR /app",
            "",
            "COPY --from=builder /root/.local /home/appuser/.local",
            "COPY . .",
            "",
            "ENV PATH=/home/appuser/.local/bin:$PATH",
            "ENV PYTHONUNBUFFERED=1",
            "",
            f"EXPOSE {config.port}",
            "",
            "HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\",
            f"  CMD curl -f http://localhost:{config.port}{config.health_check_endpoint} || exit 1",
            "",
            f"USER {config.non_root_user}",
            "",
            f'CMD ["uvicorn", "{config.app_name}.main:app", '
            f'"--host", "0.0.0.0", "--port", "{config.port}"]',
        ]
        return "\n".join(lines) + "\n"

    def generate_simple(self, app_name: str = "app") -> str:
        return self.generate(DockerfileConfig(app_name=app_name))
