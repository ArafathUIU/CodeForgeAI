"""Code Writer Agent implementation."""

from __future__ import annotations

import json
import uuid

from codeforge.agents.code_writer.batch_implementer import BatchImplementer
from codeforge.agents.code_writer.dependency_analyzer import DependencyAnalyzer
from codeforge.agents.code_writer.skeleton_builder import SkeletonBuilder
from codeforge.agents.code_writer.structured_editor import StructuredEditor
from codeforge.agents.code_writer.symbol_tracker import SymbolTracker
from codeforge.agents.code_writer.syntax_validator import SyntaxValidator
from codeforge.agents.llm_mixin import LLMMixin
from codeforge.core.agent_registry import BaseAgent
from codeforge.core.llm_client import LlmClient
from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageType,
    create_artifact_submission,
)
from codeforge.prompts.code_writer import (
    CODE_WRITER_SYSTEM_PROMPT,
    build_full_implementation_prompt,
)


class CodeWriterAgent(LLMMixin, BaseAgent):
    """Implements software from technical specifications in five stages."""

    def __init__(self, *args, output_dir: str = "", llm_client: LlmClient | None = None, **kwargs):
        BaseAgent.__init__(self, *args, **kwargs)
        LLMMixin.__init__(self, llm_client=llm_client)
        self._output_dir = output_dir
        self._editor = StructuredEditor(base_dir=output_dir)
        self._skeleton_builder = SkeletonBuilder(self._editor)
        self._analyzer = DependencyAnalyzer()
        self._tracker = SymbolTracker()
        self._validator = SyntaxValidator(base_dir=output_dir)
        self._implementer = BatchImplementer(
            self._editor, self._analyzer, self._tracker, self._validator
        )

    @property
    def role(self) -> str:
        return "code_writer"

    async def process_message(self, message: Message) -> None:
        if message.type != MessageType.TASK_ASSIGNMENT:
            return

        context = message.payload.get("context", {})
        tech_spec_data = context.get("tech_spec", {})

        if self._output_dir and not self._editor._base_dir:
            self._editor._base_dir = self._output_dir
            self._validator._base_dir = self._output_dir

        await self.update_status("Building skeleton", 0.1)

        file_tree = []
        if tech_spec_data.get("file_tree"):
            from codeforge.artifacts.tech_spec import FileTreeNode
            file_tree = [
                FileTreeNode(**node) if isinstance(node, dict) else node
                for node in tech_spec_data["file_tree"]
            ]

        if not file_tree:
            file_tree = self._skeleton_builder.generate_default_tree()

        skeleton_result = self._skeleton_builder.build(file_tree)
        if skeleton_result.errors:
            await self.report_blockage(
                f"Skeleton build failed: {'; '.join(skeleton_result.errors[:3])}",
                "skeleton_builder",
            )
            return

        await self.update_status("Analyzing dependencies", 0.2)

        build_order = self._analyzer.analyze(
            skeleton_result.files_created, {}
        )

        await self.update_status("Implementing code", 0.4)

        generated_code = self._generate_code(tech_spec_data, skeleton_result.files_created)

        # Per-file thinking updates
        for i, (filepath, code) in enumerate(generated_code.items()):
            if code and len(code) > 5:
                filename = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                progress = 0.4 + 0.2 * ((i + 1) / max(len(generated_code), 1))
                await self.update_status(f"Writing {filename}", progress, thinking=True)

        llm_available = await self._check_llm()
        if llm_available and tech_spec_data:
            await self.update_status("Enhancing with LLM code generation", 0.35)
            spec_json = json.dumps(tech_spec_data, indent=2, default=str)
            response = await self.llm_reason(
                system_prompt=CODE_WRITER_SYSTEM_PROMPT,
                user_prompt=build_full_implementation_prompt(spec_json),
                temperature=0.2,
                max_tokens=4096,
            )
            llm_data = self.parse_json_response(response)
            if llm_data:
                for key, value in llm_data.items():
                    if isinstance(value, str) and len(value) > 10:
                        file_path = key if "/" in key or "\\" in key else key
                        generated_code[file_path] = value
                await self.update_status("LLM code merged", 0.5)

        batch_result = self._implementer.implement(generated_code, build_order)

        await self.update_status("Validating syntax", 0.7)

        validation = batch_result.validation_report
        report_text = validation.summary() if validation else "No validation report"

        await self.update_status("Checking cross-file consistency", 0.85)

        unresolved = self._tracker.get_unresolved(generated_code)

        await self.discuss_with(
            "test_engineer",
            f"I have implemented {len(batch_result.files_written)} files "
            f"based on the architecture. {report_text}. "
            f"I need comprehensive tests covering "
            f"happy path, edge cases, error handling, "
            f"and integration flows. "
            f"Key files to test: "
            f"{', '.join(sorted(batch_result.files_written)[:5])}.",
            reasoning=(
                f"Generated {len(generated_code)} source files. "
                f"Files failed validation: {len(batch_result.files_failed)}. "
                f"Unresolved references: {len(unresolved)}."
            ),
            plan_snippet=(
                f"Files: {sorted(batch_result.files_written)[:6]}."
            ),
        )

        source_code_id = f"source-code-{uuid.uuid4().hex[:8]}"

        await self.update_status("Submitting source code artifact", 0.95)

        artifact_msg = create_artifact_submission(
            artifact_id=source_code_id,
            artifact_type=ArtifactType.SOURCE_CODE,
            content={
                "files": sorted(batch_result.files_written),
                "failed_files": batch_result.files_failed,
                "validation_report": report_text,
                "unresolved_references": len(unresolved),
                "editor_summary": self._editor.get_summary(),
            },
            sender=self.agent_id,
            validation_status="ready" if batch_result.success else "needs_fix",
            notes=f"Implemented {len(batch_result.files_written)} files. {report_text}",
        )
        await self.send_message(artifact_msg)
        await self.update_status("Code implementation complete", 1.0)

    def _generate_code(
        self, tech_spec_data: dict, files: list[str]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        endpoints = tech_spec_data.get("api_endpoints", [])
        entities = tech_spec_data.get("data_entities", [])
        title = tech_spec_data.get("title", "Service")

        handlers = {
            "__init__.py": lambda f: "",
            "models.py": lambda f: self._build_models(entities),
            "routes.py": lambda f: self._build_routes(endpoints),
            "services.py": lambda f: self._build_services(endpoints),
            "schemas.py": lambda f: self._build_schemas(entities),
            "main.py": lambda f: self._build_main(title),
            "config.py": lambda f: self._build_config(),
            "database.py": lambda f: self._build_database(),
            "requirements.txt": lambda f: self._build_requirements(tech_spec_data),
            "README.md": lambda f: self._build_readme(tech_spec_data),
            "conftest.py": lambda f: self._build_conftest(),
        }

        for f in files:
            matched = None
            for pattern, handler in handlers.items():
                if pattern in f:
                    matched = handler
                    break
            if matched:
                result[f] = matched(f)
            elif f.endswith(".py"):
                result[f] = self._build_stub_module(f)

        return result

    def _build_schemas(self, entities: list) -> str:
        lines = ['"""Pydantic schemas."""', "", "from pydantic import BaseModel", "", ""]
        for entity in entities:
            name = entity.get("name", entity.name if hasattr(entity, "name") else "Entity")
            lines.append(f"class {name}Schema(BaseModel):")
            lines.append(f'    """Schema for {name}."""')
            fields = entity.get("fields", [])
            for field_def in fields:
                fname = field_def.get("name", "id")
                ftype = entity.get("python_type", "str")
                required = field_def.get("required", True)
                default = "" if required else " | None = None"
                lines.append(f"    {fname}: {ftype}{default}")
            lines.append("")
        return "\n".join(lines)

    def _build_main(self, title: str) -> str:
        return (
            '"""Application entry point."""\n\n'
            'from fastapi import FastAPI\n\n'
            f'app = FastAPI(title="{title}", version="0.1.0")\n\n'
            '\n'
            '@app.get("/health")\n'
            'def health():\n'
            '    return {"status": "ok"}\n'
        )

    @staticmethod
    def _build_config() -> str:
        return '"""Application configuration."""\n\n\nclass Settings:\n    app_name: str = "app"\n'

    @staticmethod
    def _build_database() -> str:
        return (
            '"""Database session management."""\n\n'
            'from sqlalchemy import create_engine\n'
            'from sqlalchemy.orm import sessionmaker\n\n'
            'engine = create_engine("sqlite:///./data.db", echo=False)\n'
            'SessionLocal = sessionmaker(bind=engine)\n'
        )

    def _build_stub_module(self, filepath: str) -> str:
        name = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].replace(".py", "")
        return f'"""Stub for {name}."""\n\n\n'

    @staticmethod
    def _build_conftest() -> str:
        return (
            '"""Shared test fixtures."""\n\n'
            'import pytest\n\n'
            '@pytest.fixture\n'
            'def client():\n'
            '    from app.main import app\n'
            '    from fastapi.testclient import TestClient\n'
            '    return TestClient(app)\n'
        )

    def _build_models(self, entities: list) -> str:
        lines = ['"""Data models."""', "", ""]
        for entity in entities:
            name = entity.get("name", entity.name if hasattr(entity, "name") else "Entity")
            lines.append(f"class {name}:")
            lines.append(f'    """{name} data model."""')
            lines.append("")
            fields = entity.get(
                "fields", entity.fields if hasattr(entity, "fields") else []
            )
            for field_def in fields:
                fname = field_def.get(
                    "name",
                    field_def.name if hasattr(field_def, "name") else "id",
                )
                ftype = field_def.get(
                    "type",
                    field_def.type if hasattr(field_def, "type") else "str",
                )
                required = field_def.get("required", True)
                default = "" if required else " = None"
                lines.append(f"    {fname}: {ftype}{default}")
            lines.append("")
        return "\n".join(lines)

    def _build_routes(self, endpoints: list) -> str:
        lines = ['"""API routes."""', "", ""]
        for ep in endpoints:
            method = ep.get("method", "GET").lower() if isinstance(ep, dict) else ep.method.lower()
            path = ep.get("path", "/") if isinstance(ep, dict) else ep.path
            summary = ep.get("summary", "") if isinstance(ep, dict) else ep.summary
            func_name = path.strip("/").replace("/", "_").replace("-", "_") or "index"
            lines.append(f"def {func_name}():")
            lines.append(f'    """{method.upper()} {path}: {summary}"""')
            lines.append("    pass")
            lines.append("")
        return "\n".join(lines)

    def _build_services(self, endpoints: list) -> str:
        lines = ['"""Business logic services."""', "", ""]
        lines.append("class ServiceManager:")
        lines.append('    """Core service manager."""')
        lines.append("")
        lines.append("    def __init__(self):")
        lines.append("        pass")
        lines.append("")
        return "\n".join(lines)

    def _build_requirements(self, tech_spec_data: dict) -> str:
        stack = tech_spec_data.get("tech_stack", [])
        deps = []
        for item in stack:
            if isinstance(item, dict) and item.get("category") == "framework":
                deps.append(item.get("choice", ""))
        if not deps:
            deps = ["fastapi", "uvicorn", "sqlalchemy"]
        return "\n".join(deps)

    def _build_readme(self, tech_spec_data: dict) -> str:
        title = tech_spec_data.get("title", "Generated Application")
        overview = tech_spec_data.get("overview", "")
        return f"# {title}\n\n{overview}\n"

    def set_output_directory(self, path: str) -> None:
        self._output_dir = path
        self._editor._base_dir = path
        self._validator._base_dir = path
