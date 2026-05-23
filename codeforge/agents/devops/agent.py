"""DevOps Agent: prepares applications for deployment.

Generates Dockerfiles, Docker Compose configurations, CI/CD
pipelines, and environment templates for production readiness.
"""

from __future__ import annotations

import os
import uuid

from codeforge.agents.devops.cicd_generator import CICDGenerator, CICDConfig
from codeforge.agents.devops.compose_generator import ComposeGenerator, ComposeConfig, ServiceConfig
from codeforge.agents.devops.docker_generator import DockerfileGenerator, DockerfileConfig
from codeforge.core.agent_registry import BaseAgent
from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageType,
    create_artifact_submission,
)


class DevOpsAgent(BaseAgent):
    """Prepares deployment artifacts: Docker, Compose, CI/CD, env templates."""

    def __init__(self, *args, output_dir: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._output_dir = output_dir
        self._docker_gen = DockerfileGenerator()
        self._compose_gen = ComposeGenerator()
        self._cicd_gen = CICDGenerator()

    @property
    def role(self) -> str:
        return "devops"

    async def process_message(self, message: Message) -> None:
        if message.type != MessageType.TASK_ASSIGNMENT:
            return

        context = message.payload.get("context", {})
        tech_spec = context.get("tech_spec", {})

        app_name = tech_spec.get("title", "app").lower().replace(" ", "-")
        base = self._output_dir or "."

        await self.update_status("Generating Dockerfile", 0.2)

        dockerfile = self._docker_gen.generate_simple(app_name)
        dockerfile_path = os.path.join(base, "Dockerfile")
        os.makedirs(base, exist_ok=True)
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile)

        await self.update_status("Generating Docker Compose", 0.4)

        compose = self._compose_gen.generate_web_app(app_name, 8000)
        compose_path = os.path.join(base, "docker-compose.yml")
        with open(compose_path, "w", encoding="utf-8") as f:
            f.write(compose)

        await self.update_status("Generating CI/CD pipeline", 0.6)

        ci_config = CICDConfig(project_name=app_name)
        ci_workflow = self._cicd_gen.generate_github_actions(ci_config)

        github_dir = os.path.join(base, ".github", "workflows")
        os.makedirs(github_dir, exist_ok=True)
        ci_path = os.path.join(github_dir, "ci-cd.yml")
        with open(ci_path, "w", encoding="utf-8") as f:
            f.write(ci_workflow)

        await self.update_status("Generating environment template", 0.8)

        env_template = self._cicd_gen.generate_env_template()
        env_path = os.path.join(base, ".env.example")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_template)

        await self.update_status("Submitting deployment config", 0.95)

        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"

        artifact_msg = create_artifact_submission(
            artifact_id=deployment_id,
            artifact_type=ArtifactType.DEPLOYMENT_CONFIG,
            content={
                "dockerfile": dockerfile_path,
                "compose_file": compose_path,
                "ci_workflow": ci_path,
                "env_template": env_path,
                "files_generated": [
                    "Dockerfile",
                    "docker-compose.yml",
                    ".github/workflows/ci-cd.yml",
                    ".env.example",
                ],
            },
            sender=self.agent_id,
            validation_status="ready",
            notes="Generated deployment artifacts with multi-stage Dockerfile, Compose, CI/CD, and env template.",
        )
        await self.send_message(artifact_msg)
        await self.update_status("Deployment config complete", 1.0)
