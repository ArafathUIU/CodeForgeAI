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
    """Implements software from technical specifications — LLM-first with deterministic fallback."""

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

        await self.update_status("Analyzing dependencies", 0.15)

        build_order = self._analyzer.analyze(
            skeleton_result.files_created, {}
        )

        generated_code: dict[str, str] = {}

        llm_available = await self._check_llm()
        if llm_available and tech_spec_data:
            await self.update_status("Generating code via LLM", 0.2, thinking=True)
            skel_files = skeleton_result.files_created
            generated_code = await self._generate_code_llm(tech_spec_data, skel_files)

        if not generated_code:
            await self.update_status("Using deterministic code templates", 0.25)
            skel_files = skeleton_result.files_created
            generated_code = self._generate_code_deterministic(tech_spec_data, skel_files)

        # Per-file status updates
        for i, (filepath, code) in enumerate(generated_code.items()):
            if code and len(code) > 5:
                filename = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                progress = 0.4 + 0.2 * ((i + 1) / max(len(generated_code), 1))
                await self.update_status(f"Writing {filename}", progress, thinking=True)

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

    async def _generate_code_llm(
        self, tech_spec_data: dict, files: list[str]
    ) -> dict[str, str]:
        """Generate all source files from tech spec via LLM. Empty dict on failure."""
        try:
            spec_json = json.dumps(tech_spec_data, indent=2, default=str)
            response = await self.llm_reason(
                system_prompt=CODE_WRITER_SYSTEM_PROMPT,
                user_prompt=build_full_implementation_prompt(spec_json),
                temperature=0.2,
                max_tokens=8192,
            )
            data = self.parse_json_response(response)
            if not data or not isinstance(data, dict):
                return {}

            result: dict[str, str] = {}
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 20:
                    result[key] = value
                elif isinstance(value, dict) and "content" in value:
                    result[key] = value["content"]

            return result
        except Exception:
            return {}

    def _generate_code_deterministic(
        self, tech_spec_data: dict, files: list[str]
    ) -> dict[str, str]:
        """Deterministic code generation — used as fallback when LLM is unavailable."""
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
        lines = [
            '"""Pydantic schemas."""', "",
            "from datetime import datetime",
            "from typing import Optional",
            "from pydantic import BaseModel", "", "",
        ]
        for entity in entities:
            name = entity.get("name", entity.name if hasattr(entity, "name") else "Entity")
            lines.append(f"class {name}Create(BaseModel):")
            lines.append(f'    """Schema for creating {name}."""')
            fields = entity.get("fields", [])
            for field_def in fields:
                fname = field_def.get("name", "id")
                ftype_s = field_def.get("type", "str")
                ftype = self._map_type(field_def.get("python_type", ftype_s))
                required = field_def.get("required", True)
                default = "" if required else " | None = None"
                lines.append(f"    {fname}: {ftype}{default}")
            lines.append("")
            lines.append(f"class {name}Response({name}Create):")
            lines.append(f'    """Schema for {name} responses."""')
            lines.append("    id: int")
            lines.append("    created_at: datetime")
            lines.append("    updated_at: Optional[datetime] = None")
            lines.append("")
        return "\n".join(lines)

    def _build_main(self, title: str) -> str:
        return (
            '"""Application entry point."""\n\n'
            'from fastapi import FastAPI\n'
            'from fastapi.middleware.cors import CORSMiddleware\n\n'
            f'app = FastAPI(title="{title}", version="0.1.0")\n\n'
            'app.add_middleware(\n'
            '    CORSMiddleware,\n'
            '    allow_origins=["*"],\n'
            '    allow_credentials=True,\n'
            '    allow_methods=["*"],\n'
            '    allow_headers=["*"],\n'
            ')\n\n'
            'from app.routes import router\n'
            'app.include_router(router)\n\n'
            'from app.database import engine\n'
            'from app.models import Base\n\n'
            '@app.on_event("startup")\n'
            'async def startup():\n'
            '    Base.metadata.create_all(bind=engine)\n\n'
            '@app.get("/health")\n'
            'def health():\n'
            '    return {"status": "ok"}\n'
        )

    @staticmethod
    def _build_config() -> str:
        return (
            '"""Application configuration."""\n\n'
            'import os\n\n\n'
            'class Settings:\n'
            '    app_name: str = "app"\n'
            '    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")\n'
            '    debug: bool = os.getenv("DEBUG", "false").lower() == "true"\n\n'
            'settings = Settings()\n'
        )

    @staticmethod
    def _build_database() -> str:
        return (
            '"""Database session management."""\n\n'
            'from sqlalchemy import create_engine\n'
            'from sqlalchemy.orm import Session, sessionmaker, declarative_base\n\n'
            'from app.config import settings\n\n'
            'engine = create_engine(settings.database_url, echo=settings.debug)\n'
            'SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)\n'
            'Base = declarative_base()\n\n\n'
            'def get_db():\n'
            '    db = SessionLocal()\n'
            '    try:\n'
            '        yield db\n'
            '    finally:\n'
            '        db.close()\n'
        )

    def _build_stub_module(self, filepath: str) -> str:
        name = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].replace(".py", "")
        return f'"""{name} module."""\n\n\n'

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

    @staticmethod
    def _map_type(type_str: str) -> str:
        mapping = {
            "str": "str",
            "string": "str",
            "int": "int",
            "integer": "int",
            "float": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "datetime",
            "uuid": "str",
        }
        return mapping.get(type_str.lower(), "str")

    def _build_models(self, entities: list) -> str:
        lines = [
            '"""Data models."""', '',
            'from sqlalchemy import ('
            'Column, Integer, String, Float, '
            'Boolean, DateTime, ForeignKey, Text'
            ')',
            'from sqlalchemy.orm import relationship',
            'from sqlalchemy.sql import func', '',
            'from app.database import Base', '', '',
        ]
        for entity in entities:
            name = entity.get("name", entity.name if hasattr(entity, "name") else "Entity")
            table = name.lower() + "s"
            lines.append(f"class {name}(Base):")
            lines.append(f"    __tablename__ = '{table}'")
            lines.append("")
            lines.append("    id = Column(Integer, primary_key=True, index=True)")
            fields = entity.get(
                "fields",
                entity.fields if hasattr(entity, "fields") else [],
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
                ftype_str = str(ftype).lower()
                col = {
                    "str": "String(255)",
                    "string": "String(255)",
                    "int": "Integer",
                    "integer": "Integer",
                    "float": "Float",
                    "bool": "Boolean",
                    "boolean": "Boolean",
                    "datetime": "DateTime(timezone=True), server_default=func.now()",
                    "text": "Text",
                }.get(ftype_str, "String(255)")
                required = field_def.get("required", True)
                nullable = ", nullable=False" if required else ", nullable=True"
                lines.append(f"    {fname} = Column({col}{nullable})")
            lines.append(
                "    created_at = Column("
                "DateTime(timezone=True), server_default=func.now()"
                ")"
            )
            lines.append(
                "    updated_at = Column("
                "DateTime(timezone=True), onupdate=func.now()"
                ")"
            )
            lines.append("")
        return "\n".join(lines)

    def _build_routes(self, endpoints: list) -> str:
        lines = [
            '"""API routes."""', '',
            'from fastapi import APIRouter, Depends, HTTPException, status',
            'from sqlalchemy.orm import Session',
            'from typing import List', '',
            'from app.database import get_db', '',
            'router = APIRouter()', '', '',
        ]
        for ep in endpoints:
            method = (
                ep.get("method", "GET") if isinstance(ep, dict)
                else ep.method
            ).upper()
            path = (
                ep.get("path", "/") if isinstance(ep, dict)
                else ep.path
            )
            summary = (
                ep.get("summary", "") if isinstance(ep, dict)
                else getattr(ep, "summary", "")
            )
            entity = path.strip("/").split("/")[0] or "item"
            raw = path.strip("/")
            raw = raw.replace("/", "_").replace("-", "_")
            raw = raw.replace("{", "").replace("}", "")
            func_name = raw or "index"

            not_found = (
                f'raise HTTPException('
                f'status_code=status.HTTP_404_NOT_FOUND, '
                f'detail="{entity} not found")'
            )

            if method == "GET" and "{" not in path:
                lines.append(
                    f'@router.get("{path}", response_model=List[dict])'
                )
                lines.append(
                    f"async def list_{func_name}("
                    f"db: Session = Depends(get_db)):"
                )
                lines.append(f'    """GET {path}: {summary}"""')
                lines.append("    return []")
            elif method == "GET" and "{" in path:
                lines.append(f'@router.get("{path}")')
                lines.append(
                    f"async def get_{func_name}("
                    f"id: int, db: Session = Depends(get_db)):"
                )
                lines.append(f'    """GET {path}: {summary}"""')
                lines.append(f"    {not_found}")
            elif method == "POST":
                lines.append(
                    f'@router.post("{path}", '
                    f'status_code=status.HTTP_201_CREATED)'
                )
                lines.append(
                    f"async def create_{func_name}("
                    f"body: dict, db: Session = Depends(get_db)):"
                )
                lines.append(f'    """POST {path}: {summary}"""')
                lines.append("    return body")
            elif method == "PUT":
                lines.append(f'@router.put("{path}")')
                lines.append(
                    f"async def update_{func_name}("
                    f"id: int, body: dict, "
                    f"db: Session = Depends(get_db)):"
                )
                lines.append(f'    """PUT {path}: {summary}"""')
                lines.append(f"    {not_found}")
            elif method == "DELETE":
                lines.append(
                    f'@router.delete("{path}", '
                    f'status_code=status.HTTP_204_NO_CONTENT)'
                )
                lines.append(
                    f"async def delete_{func_name}("
                    f"id: int, db: Session = Depends(get_db)):"
                )
                lines.append(f'    """DELETE {path}: {summary}"""')
                lines.append(f"    {not_found}")
            else:
                lines.append(
                    f'@router.{method.lower()}("{path}")'
                )
                lines.append(f"async def {func_name}():")
                lines.append(f'    """{method} {path}: {summary}"""')
                lines.append("    return {}")

            lines.append("")
            lines.append("")
        return "\n".join(lines)

    def _build_services(self, endpoints: list) -> str:
        lines = [
            '"""Business logic services."""', '',
            'from typing import Optional, List',
            'from sqlalchemy.orm import Session', '',
        ]
        entities = set()
        for ep in endpoints:
            path = ep.get("path", "/") if isinstance(ep, dict) else ep.path
            e = path.strip("/").split("/")[0]
            if e:
                entities.add(e)

        for entity in sorted(entities):
            lines.append(f"class {entity.capitalize()}Service:")
            lines.append(f'    """Service for {entity} operations."""')
            lines.append("")
            lines.append("    @staticmethod")
            lines.append("    def get_all(db: Session) -> list:")
            lines.append("        return []")
            lines.append("")
            lines.append("    @staticmethod")
            lines.append("    def get_by_id(db: Session, item_id: int):")
            lines.append("        return None")
            lines.append("")
            lines.append("    @staticmethod")
            lines.append("    def create(db: Session, data: dict):")
            lines.append("        return data")
            lines.append("")
            lines.append("    @staticmethod")
            lines.append("    def update(db: Session, item_id: int, data: dict):")
            lines.append("        return data")
            lines.append("")
            lines.append("    @staticmethod")
            lines.append("    def delete(db: Session, item_id: int) -> bool:")
            lines.append("        return True")
            lines.append("")
        return "\n".join(lines)

    def _build_requirements(self, tech_spec_data: dict) -> str:
        deps = [
            "fastapi>=0.110.0",
            "uvicorn[standard]>=0.27.0",
            "sqlalchemy>=2.0.0",
            "pydantic>=2.0.0",
            "python-dotenv>=1.0.0",
            "alembic>=1.13.0",
            "python-multipart>=0.0.6",
        ]
        stack = tech_spec_data.get("tech_stack", [])
        for item in stack:
            if isinstance(item, dict) and item.get("category") == "framework":
                fw = item.get("choice", "")
                if fw.lower() == "fastapi":
                    pass
        return "\n".join(deps)

    def _build_readme(self, tech_spec_data: dict) -> str:
        title = tech_spec_data.get("title", "Generated Application")
        overview = tech_spec_data.get("overview", "A generated FastAPI application.")
        endpoints = tech_spec_data.get("api_endpoints", [])
        ep_lines = ""
        for ep in endpoints[:15]:
            method = (
                ep.get("method", "GET") if isinstance(ep, dict)
                else getattr(ep, "method", "GET")
            ).upper()
            path = (
                ep.get("path", "/") if isinstance(ep, dict)
                else getattr(ep, "path", "/")
            )
            summary = (
                ep.get("summary", "") if isinstance(ep, dict)
                else getattr(ep, "summary", "")
            )
            ep_lines += f"| {method} | `{path}` | {summary} |\n"

        return (
            f"# {title}\n\n"
            f"{overview}\n\n"
            f"## Setup\n\n"
            f"```bash\n"
            f"pip install -r requirements.txt\n"
            f"uvicorn app.main:app --reload\n"
            f"```\n\n"
            f"## API Endpoints\n\n"
            f"| Method | Path | Description |\n"
            f"|--------|------|-------------|\n"
            f"{ep_lines}\n"
            f"## OpenAPI Docs\n\n"
            f"Run the server and visit http://localhost:8000/docs\n"
        )

    def set_output_directory(self, path: str) -> None:
        self._output_dir = path
        self._editor._base_dir = path
        self._validator._base_dir = path
