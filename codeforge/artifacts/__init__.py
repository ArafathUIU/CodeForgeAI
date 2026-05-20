"""Typed artifact data models: PRD, TechSpec, SourceCode, TestSuite, etc."""

from codeforge.artifacts.prd import AcceptanceCriterion, PRD, ScopeBoundary, UserStory
from codeforge.artifacts.tech_spec import (
    APIEndpoint,
    DataEntity,
    DataField,
    FileTreeNode,
    TechSpec,
    TechStackDecision,
    TechnicalRisk,
)

__all__ = [
    "AcceptanceCriterion",
    "APIEndpoint",
    "DataEntity",
    "DataField",
    "FileTreeNode",
    "PRD",
    "ScopeBoundary",
    "TechSpec",
    "TechStackDecision",
    "TechnicalRisk",
    "UserStory",
]
