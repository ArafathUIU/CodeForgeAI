"""Docker Compose generator: produces multi-service configurations.

Generates Docker Compose files with service definitions, networking,
volume mounts, environment variables, and health checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ServiceConfig:
    name: str
    image: str = ""
    build_context: str = "."
    port: int = 8000
    depends_on: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    health_check: str = ""


@dataclass
class ComposeConfig:
    project_name: str = "app"
    version: str = "3.8"
    services: list[ServiceConfig] = field(default_factory=list)
    volumes: dict[str, dict] = field(default_factory=dict)
    networks: list[str] = field(default_factory=list)


class ComposeGenerator:
    def generate(self, config: ComposeConfig) -> str:
        lines = [f'version: "{config.version}"', "", "services:"]

        for svc in config.services:
            lines.append(f"  {svc.name}:")
            if svc.build_context:
                lines.append(f"    build: {svc.build_context}")
            if svc.image:
                lines.append(f"    image: {svc.image}")
            lines.append('    ports:')
            lines.append(f'      - "{svc.port}:{svc.port}"')

            if svc.depends_on:
                lines.append("    depends_on:")
                for dep in svc.depends_on:
                    lines.append(f"      - {dep}")

            if svc.environment:
                lines.append("    environment:")
                for key, value in svc.environment.items():
                    lines.append(f"      - {key}={value}")

            if svc.volumes:
                lines.append("    volumes:")
                for vol in svc.volumes:
                    lines.append(f"      - {vol}")

            if svc.health_check:
                lines.append("    healthcheck:")
                lines.append(f"      test: {svc.health_check}")
                lines.append("      interval: 30s")
                lines.append("      timeout: 10s")
                lines.append("      retries: 3")

            lines.append("")

        if config.volumes:
            lines.append("volumes:")
            for name, cfg in config.volumes.items():
                lines.append(f"  {name}:")

        if config.networks:
            lines.append("networks:")
            for net in config.networks:
                lines.append(f"  {net}:")
                lines.append("    driver: bridge")

        return "\n".join(lines) + "\n"

    def generate_web_app(
        self, app_name: str = "app", port: int = 8000
    ) -> str:
        return self.generate(
            ComposeConfig(
                project_name=app_name,
                services=[
                    ServiceConfig(
                        name="web",
                        build_context=".",
                        port=port,
                        environment={
                            "ENV": "production",
                            "PORT": str(port),
                        },
                        health_check=f'["CMD", "curl", "-f", "http://localhost:{port}/health"]',
                    ),
                ],
                networks=["app-network"],
            )
        )
