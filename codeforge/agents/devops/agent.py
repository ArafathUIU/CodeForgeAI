"""DevOps Agent: prepares applications for deployment."""

from __future__ import annotations

import json
import os
import uuid

from codeforge.agents.devops.cicd_generator import CICDConfig, CICDGenerator
from codeforge.agents.devops.compose_generator import ComposeGenerator
from codeforge.agents.devops.docker_generator import DockerfileGenerator
from codeforge.agents.llm_mixin import LLMMixin
from codeforge.core.agent_registry import BaseAgent
from codeforge.core.llm_client import LlmClient
from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageType,
    create_artifact_submission,
)
from codeforge.prompts.devops import (
    DEVOPS_SYSTEM_PROMPT,
    build_devops_prompt,
)


class DevOpsAgent(LLMMixin, BaseAgent):
    """Prepares deployment artifacts: Docker, Compose, CI/CD, env templates."""

    def __init__(self, *args, output_dir: str = "", llm_client: LlmClient | None = None, **kwargs):
        BaseAgent.__init__(self, *args, **kwargs)
        LLMMixin.__init__(self, llm_client=llm_client)
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

        llm_available = await self._check_llm()
        if llm_available:
            await self.update_status("LLM-powered deployment config", 0.15)
            tech_json = json.dumps(tech_spec, indent=2, default=str)
            response = await self.llm_reason(
                system_prompt=DEVOPS_SYSTEM_PROMPT,
                user_prompt=build_devops_prompt(app_name, tech_json),
                temperature=0.2,
                max_tokens=3072,
            )
            llm_data = self.parse_json_response(response)
            if llm_data:
                dockerfile = llm_data.get(
                    "dockerfile", self._docker_gen.generate_simple(app_name)
                )
                compose = llm_data.get(
                    "docker_compose",
                    self._compose_gen.generate_web_app(app_name),
                )
                ci_workflow = llm_data.get(
                    "cicd",
                    self._cicd_gen.generate_github_actions(CICDConfig()),
                )
                env_template = llm_data.get(
                    "env_template", self._cicd_gen.generate_env_template()
                )
            else:
                dockerfile = self._docker_gen.generate_simple(app_name)
                compose = self._compose_gen.generate_web_app(app_name, 8000)
                ci_workflow = self._cicd_gen.generate_github_actions(
                    CICDConfig(project_name=app_name)
                )
                env_template = self._cicd_gen.generate_env_template()
        else:
            dockerfile = self._docker_gen.generate_simple(app_name)
            compose = self._compose_gen.generate_web_app(app_name, 8000)
            ci_workflow = self._cicd_gen.generate_github_actions(
                CICDConfig(project_name=app_name)
            )
            env_template = self._cicd_gen.generate_env_template()
        dockerfile_path = os.path.join(base, "Dockerfile")
        os.makedirs(base, exist_ok=True)
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile)

        compose_path = os.path.join(base, "docker-compose.yml")
        with open(compose_path, "w", encoding="utf-8") as f:
            f.write(compose)

        github_dir = os.path.join(base, ".github", "workflows")
        os.makedirs(github_dir, exist_ok=True)
        ci_path = os.path.join(github_dir, "ci-cd.yml")
        with open(ci_path, "w", encoding="utf-8") as f:
            f.write(ci_workflow)

        await self.update_status("Generating environment template", 0.8)

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
            notes=(
                "Generated deployment artifacts: "
                "Dockerfile, Compose, CI/CD, and env template."
            ),
        )
        await self.send_message(artifact_msg)
        await self.update_status("Deployment config complete", 1.0)
