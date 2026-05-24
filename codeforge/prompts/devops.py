"""Prompt templates for DevOps Agent."""

DEVOPS_SYSTEM_PROMPT = """
You are the DevOps Agent in CodeForge.
Generate production-ready deployment artifacts:
- Multi-stage Dockerfile (build + production, non-root user)
- Docker Compose configuration
- CI/CD pipeline (GitHub Actions)
- Environment templates with secret markers
Return structured JSON with all configurations.
""".strip()


def build_devops_prompt(app_name: str, tech_stack_json: str) -> str:
    return f"""
Generate deployment artifacts for `{app_name}`.

Tech stack:
{tech_stack_json}

Return JSON with:
- dockerfile: complete multi-stage Dockerfile content
- docker_compose: complete docker-compose.yml content
- cicd: GitHub Actions workflow YAML
- env_template: .env.example content
""".strip()
