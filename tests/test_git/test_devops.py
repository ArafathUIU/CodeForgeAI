"""Tests for DevOps Agent components."""

import os

import pytest

from codeforge.agents.devops.docker_generator import DockerfileConfig, DockerfileGenerator
from codeforge.agents.devops.compose_generator import ComposeConfig, ComposeGenerator, ServiceConfig
from codeforge.agents.devops.cicd_generator import CICDConfig, CICDGenerator


class TestDockerfileGenerator:
    @pytest.fixture
    def generator(self):
        return DockerfileGenerator()

    def test_generate_produces_multistage(self, generator):
        content = generator.generate_simple("myapp")
        assert "FROM" in content
        assert "AS builder" in content
        assert "AS production" in content
        assert "EXPOSE" in content
        assert "HEALTHCHECK" in content
        assert "appuser" in content

    def test_generate_custom_config(self, generator):
        config = DockerfileConfig(
            app_name="customapp",
            port=3000,
            base_image="python:3.12-slim",
        )
        content = generator.generate(config)
        assert "customapp" in content
        assert "3000" in content
        assert "python:3.12-slim" in content

    def test_generate_includes_build_stage(self, generator):
        content = generator.generate(DockerfileConfig())
        assert "pip install" in content.lower()


class TestComposeGenerator:
    @pytest.fixture
    def generator(self):
        return ComposeGenerator()

    def test_generate_web_app(self, generator):
        content = generator.generate_web_app("testapp", 8080)
        assert "version:" in content
        assert "services:" in content
        assert "web:" in content
        assert "8080" in content
        assert "healthcheck" in content.lower()

    def test_generate_custom_config(self, generator):
        config = ComposeConfig(
            services=[
                ServiceConfig(
                    name="api",
                    port=5000,
                    environment={"DEBUG": "true"},
                    depends_on=["db"],
                ),
                ServiceConfig(name="db", port=5432),
            ],
        )
        content = generator.generate(config)
        assert "api:" in content
        assert "db:" in content
        assert "depends_on" in content


class TestCICDGenerator:
    @pytest.fixture
    def generator(self):
        return CICDGenerator()

    def test_generate_github_actions(self, generator):
        config = CICDConfig(project_name="testproj")
        content = generator.generate_github_actions(config)
        assert "name: CI/CD" in content
        assert "pytest" in content
        assert "ruff" in content
        assert "actions/checkout@v4" in content

    def test_generate_with_docker(self, generator):
        config = CICDConfig(project_name="dockerapp", docker_build=True)
        content = generator.generate_github_actions(config)
        assert "build:" in content
        assert "docker build" in content

    def test_generate_env_template(self, generator):
        content = generator.generate_env_template()
        assert "APP_NAME" in content
        assert "SECRET_KEY" in content
        assert "DATABASE_URL" in content
