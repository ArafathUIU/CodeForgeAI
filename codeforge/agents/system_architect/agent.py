"""System Architect Agent implementation."""

from __future__ import annotations

import json
import uuid

from codeforge.agents.llm_mixin import LLMMixin
from codeforge.agents.system_architect.api_designer import APIContractDesigner
from codeforge.agents.system_architect.data_model import DataModelDesigner
from codeforge.agents.system_architect.file_tree import FileTreeGenerator
from codeforge.agents.system_architect.risk_assessor import RiskAssessor
from codeforge.agents.system_architect.tech_stack import TechStackSelector
from codeforge.artifacts.prd import PRD
from codeforge.artifacts.tech_spec import (
    APIEndpoint,
    DataEntity,
    DataField,
    FileTreeNode,
    TechnicalRisk,
    TechSpec,
    TechStackDecision,
)
from codeforge.core.agent_registry import BaseAgent
from codeforge.core.llm_client import LlmClient
from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageType,
    create_artifact_submission,
)
from codeforge.prompts.system_architect import (
    SYSTEM_ARCHITECT_SYSTEM_PROMPT,
    build_tech_spec_prompt,
)


def _safe_attr(obj, attr: str, default: str = "") -> str:
    if hasattr(obj, attr):
        return str(getattr(obj, attr))
    if isinstance(obj, dict):
        return str(obj.get(attr, default))
    return default


class SystemArchitectAgent(LLMMixin, BaseAgent):
    """Turns PRD artifacts into implementation-ready technical specifications."""

    def __init__(self, *args, llm_client: LlmClient | None = None, **kwargs):
        BaseAgent.__init__(self, *args, **kwargs)
        LLMMixin.__init__(self, llm_client=llm_client)
        self._stack_selector = TechStackSelector()
        self._data_model_designer = DataModelDesigner()
        self._api_designer = APIContractDesigner()
        self._file_tree_generator = FileTreeGenerator()
        self._risk_assessor = RiskAssessor()

    @property
    def role(self) -> str:
        return "system_architect"

    async def process_message(self, message: Message) -> None:
        if message.type != MessageType.TASK_ASSIGNMENT:
            return

        prd = self._load_prd(message)
        spec = None

        llm_available = await self._check_llm()
        if llm_available:
            await self.update_status("Reasoning with LLM architecture", 0.1)
            context_digest = self.get_context_digest()
            prd_json = json.dumps(prd.to_dict(), indent=2, default=str)

            response = await self.llm_reason(
                system_prompt=SYSTEM_ARCHITECT_SYSTEM_PROMPT,
                user_prompt=build_tech_spec_prompt(prd_json, context_digest),
                temperature=0.3,
                max_tokens=3072,
            )

            llm_data = self.parse_json_response(response)
            if llm_data:
                await self.update_status("Building tech spec from LLM output", 0.7)
                spec = self._build_from_llm(llm_data, prd.title)
                await self.update_status("Tech spec finalized via LLM", 0.9)

        if spec is None:
            await self.update_status("Selecting technology stack", 0.2)
            tech_stack = self._stack_selector.select(prd)

            await self.update_status("Designing data model", 0.4)
            data_entities = self._data_model_designer.design(prd)

            await self.update_status("Designing API contracts", 0.6)
            api_endpoints = self._api_designer.design(prd, data_entities)

            await self.update_status("Generating file tree and risks", 0.8)
            file_tree = self._file_tree_generator.generate()
            risks = self._risk_assessor.assess(prd)

            spec = TechSpec(
                id=f"tech-spec-{uuid.uuid4().hex[:8]}",
                title=f"Technical Specification for {prd.title}",
                overview=f"Implementation plan for {prd.title}: {prd.summary}",
                tech_stack=tech_stack,
                data_entities=data_entities,
                api_endpoints=api_endpoints,
                file_tree=file_tree,
                risks=risks,
            )

        stack_summary = ", ".join(
            f"{_safe_attr(t, 'category')}:{_safe_attr(t, 'choice')}"
            for t in spec.tech_stack[:4]
        )
        await self.discuss_with(
            "code_writer",
            f"Architecture is ready for \u201c{spec.title}\u201d. "
            f"Stack: {stack_summary}. "
            f"I designed {len(spec.data_entities)} data entities "
            f"and {len(spec.api_endpoints)} API endpoints. "
            f"File tree has {len(spec.file_tree)} nodes "
            f"across the project structure. "
            f"I assessed {len(spec.risks)} risks \u2014 "
            f"please implement following the file tree structure "
            f"and API contracts.",
            reasoning=(
                f"Selected stack based on {spec.title} requirements. "
                f"Data model covers {len(spec.data_entities)} entities. "
                f"API contracts follow RESTful conventions."
            ),
            plan_snippet=(
                f"Stack: {stack_summary}. "
                f"Entities: {len(spec.data_entities)}. "
                f"Endpoints: {len(spec.api_endpoints)}."
            ),
        )
        await self.discuss_with(
            "code_writer",
            f"Architecture is ready for \u201c{spec.title}\u201d. "
            f"Stack: {stack_summary}. "
            f"I designed {len(spec.data_entities)} data entities "
            f"and {len(spec.api_endpoints)} API endpoints. "
            f"File tree has {len(spec.file_tree)} nodes "
            f"across the project structure. "
            f"I assessed {len(spec.risks)} risks \u2014 "
            f"please implement following the file tree structure "
            f"and API contracts.",
            reasoning=(
                f"Selected stack based on {prd.title} requirements. "
                f"Data model covers {len(spec.data_entities)} entities. "
                f"API contracts follow RESTful conventions."
            ),
            plan_snippet=(
                f"Stack: {stack_summary}. "
                f"Entities: {len(spec.data_entities)}. "
                f"Endpoints: {len(spec.api_endpoints)}."
            ),
        )

        artifact_message = create_artifact_submission(
            artifact_id=spec.id,
            artifact_type=ArtifactType.TECH_SPEC,
            content=spec.to_dict(),
            sender=self.agent_id,
            validation_status=(
                "ready" if spec.is_ready_for_implementation() else "incomplete"
            ),
            notes=(
                "Generated via LLM architecture reasoning"
                if llm_available
                else "Generated by deterministic architecture pipeline"
            ),
        )
        await self.send_message(artifact_message)
        await self.update_status("Tech spec submitted", 1.0)

    def _load_prd(self, message: Message) -> PRD:
        context = message.payload.get("context", {})
        if "prd" in context:
            return PRD.from_dict(context["prd"])

        specification = context.get(
            "specification",
            message.payload.get("description", "Untitled app"),
        )
        return PRD(
            id="prd-placeholder",
            title="Generated Application",
            summary=specification,
            goals=[specification],
        )

    def _build_from_llm(self, data: dict, title: str) -> TechSpec:
        tech_stack = []
        for item in data.get("tech_stack", []):
            tech_stack.append(TechStackDecision(
                category=item.get("category", ""),
                choice=item.get("choice", ""),
                rationale=item.get("rationale", ""),
                alternatives_considered=item.get("alternatives_considered", []),
            ))

        data_entities = []
        for entity in data.get("data_entities", []):
            fields = []
            for f in entity.get("fields", []):
                fields.append(DataField(
                    name=f.get("name", "id"),
                    type=f.get("type", "str"),
                    required=f.get("required", True),
                    indexed=f.get("indexed", False),
                    description=f.get("description", ""),
                ))
            data_entities.append(DataEntity(
                name=entity.get("name", "Entity"),
                fields=fields,
                relationships=entity.get("relationships", []),
            ))

        api_endpoints = []
        for ep in data.get("api_endpoints", []):
            api_endpoints.append(APIEndpoint(
                method=ep.get("method", "GET"),
                path=ep.get("path", "/"),
                summary=ep.get("summary", ""),
                request_schema=ep.get("request_schema", {}),
                response_schema=ep.get("response_schema", {}),
                auth_required=ep.get("auth_required", False),
            ))

        file_tree = []
        for node in data.get("file_tree", []):
            file_tree.append(FileTreeNode(
                path=node.get("path", ""),
                node_type=node.get("node_type", "file"),
                purpose=node.get("purpose", ""),
            ))

        risks = []
        for r in data.get("risks", []):
            risks.append(TechnicalRisk(
                description=r.get("description", ""),
                severity=r.get("severity", "medium"),
                mitigation=r.get("mitigation", ""),
            ))

        return TechSpec(
            id=f"tech-spec-{uuid.uuid4().hex[:8]}",
            title=f"Technical Specification for {title}",
            overview=data.get("overview", f"Architecture for {title}"),
            tech_stack=tech_stack,
            data_entities=data_entities,
            api_endpoints=api_endpoints,
            file_tree=file_tree,
            risks=risks,
        )
