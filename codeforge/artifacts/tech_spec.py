"""Technical specification artifact models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TechStackDecision:
    """Technology selection with rationale and alternatives."""

    category: str
    choice: str
    rationale: str
    alternatives_considered: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "choice": self.choice,
            "rationale": self.rationale,
            "alternatives_considered": self.alternatives_considered,
        }


@dataclass
class DataField:
    """A field on a data entity."""

    name: str
    type: str
    required: bool = True
    indexed: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "indexed": self.indexed,
            "description": self.description,
        }


@dataclass
class DataEntity:
    """A persistent data entity in the application model."""

    name: str
    fields: list[DataField] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fields": [field.to_dict() for field in self.fields],
            "relationships": self.relationships,
        }


@dataclass
class APIEndpoint:
    """HTTP API endpoint contract."""

    method: str
    path: str
    summary: str
    request_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    auth_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.upper(),
            "path": self.path,
            "summary": self.summary,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
            "auth_required": self.auth_required,
        }


@dataclass
class FileTreeNode:
    """A file or directory in the planned project tree."""

    path: str
    node_type: str
    purpose: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "node_type": self.node_type,
            "purpose": self.purpose,
        }


@dataclass
class TechnicalRisk:
    """A technical risk and its mitigation strategy."""

    description: str
    severity: str
    mitigation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "severity": self.severity,
            "mitigation": self.mitigation,
        }


@dataclass
class TechSpec:
    """Technical specification produced by System Architect Agent."""

    id: str
    title: str
    overview: str
    tech_stack: list[TechStackDecision] = field(default_factory=list)
    data_entities: list[DataEntity] = field(default_factory=list)
    api_endpoints: list[APIEndpoint] = field(default_factory=list)
    file_tree: list[FileTreeNode] = field(default_factory=list)
    risks: list[TechnicalRisk] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_ready_for_implementation(self) -> bool:
        return bool(self.tech_stack and self.file_tree)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "overview": self.overview,
            "tech_stack": [item.to_dict() for item in self.tech_stack],
            "data_entities": [entity.to_dict() for entity in self.data_entities],
            "api_endpoints": [endpoint.to_dict() for endpoint in self.api_endpoints],
            "file_tree": [node.to_dict() for node in self.file_tree],
            "risks": [risk.to_dict() for risk in self.risks],
            "version": self.version,
            "created_at": self.created_at.isoformat(),
        }
