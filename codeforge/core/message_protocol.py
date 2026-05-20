"""Structured message protocol for inter-agent communication.

Every message between agents is a formal package with typed fields,
enabling traceable, structured, and verifiable communication.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageType(StrEnum):
    """Enumeration of all message types in the CodeForge protocol."""

    TASK_ASSIGNMENT = "task_assignment"
    ARTIFACT_SUBMISSION = "artifact_submission"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    BLOCKAGE_REPORT = "blockage_report"
    REVISION_REQUEST = "revision_request"
    STATUS_UPDATE = "status_update"
    CONFLICT_ESCALATION = "conflict_escalation"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    SYSTEM_EVENT = "system_event"


class Priority(StrEnum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AgentRole(StrEnum):
    """Known agent roles in the system."""

    ORCHESTRATOR = "orchestrator"
    PRODUCT_MANAGER = "product_manager"
    SYSTEM_ARCHITECT = "system_architect"
    CODE_WRITER = "code_writer"
    TEST_ENGINEER = "test_engineer"
    CODE_REVIEWER = "code_reviewer"
    DEVOPS = "devops"
    HUMAN_OPERATOR = "human_operator"
    CONFLICT_RESOLVER = "conflict_resolver"


class ArtifactType(StrEnum):
    """Types of artifacts produced by agents."""

    PRD = "prd"
    TECH_SPEC = "tech_spec"
    SOURCE_CODE = "source_code"
    TEST_SUITE = "test_suite"
    REVIEW_REPORT = "review_report"
    DEPLOYMENT_CONFIG = "deployment_config"
    FILE_TREE = "file_tree"


class Message(BaseModel):
    """Core message structure for all inter-agent communication.

    Every message sent between agents must use this schema.
    The payload field holds the structured content, which varies by message type.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    recipient: str
    type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    requires_response: bool = False
    timeout_seconds: int = 300
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID: {v}")
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1:
            raise ValueError("timeout_seconds must be positive")
        return v

    def is_expired(self) -> bool:
        """Check if the message has exceeded its timeout."""
        if self.timeout_seconds <= 0:
            return False
        age = (datetime.now(UTC) - self.timestamp).total_seconds()
        return age > self.timeout_seconds

    def create_reply(
        self,
        sender: str,
        msg_type: MessageType,
        payload: dict[str, Any] | None = None,
        priority: Priority | None = None,
    ) -> Message:
        """Create a reply message linked to this one via correlation_id."""
        return Message(
            sender=sender,
            recipient=self.sender,
            type=msg_type,
            payload=payload or {},
            priority=priority or self.priority,
            correlation_id=self.id,
        )


class MessageSerializer:
    """Serializes and deserializes Message objects to/from dict and JSON."""

    @staticmethod
    def to_dict(message: Message) -> dict[str, Any]:
        """Convert a Message to a dictionary."""
        return message.model_dump()

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Message:
        """Create a Message from a dictionary."""
        return Message(**data)

    @staticmethod
    def to_json(message: Message) -> str:
        """Serialize a Message to JSON string."""
        return message.model_dump_json(indent=2)

    @staticmethod
    def from_json(json_str: str) -> Message:
        """Deserialize a Message from a JSON string."""
        return Message.model_validate_json(json_str)


class MessageValidator:
    """Validates message content based on message type.

    Ensures that messages contain the required fields for their type
    and that payloads match expected schemas.
    """

    REQUIRED_PAYLOAD_KEYS: dict[MessageType, list[str]] = {
        MessageType.TASK_ASSIGNMENT: ["task_id", "description", "agent_role"],
        MessageType.ARTIFACT_SUBMISSION: ["artifact_id", "artifact_type", "content", "version"],
        MessageType.CLARIFICATION_REQUEST: ["question", "context"],
        MessageType.CLARIFICATION_RESPONSE: ["question_id", "answer"],
        MessageType.BLOCKAGE_REPORT: ["blockage_reason", "blocked_by", "suggestions"],
        MessageType.REVISION_REQUEST: ["artifact_id", "revision_notes", "requested_by"],
        MessageType.STATUS_UPDATE: ["agent_id", "status", "progress"],
        MessageType.CONFLICT_ESCALATION: ["conflict_type", "agent_a", "agent_b", "details"],
        MessageType.APPROVAL_REQUEST: ["approval_id", "artifact_id", "description"],
        MessageType.APPROVAL_RESPONSE: ["approval_id", "decision", "comments"],
        MessageType.SYSTEM_EVENT: ["event_type", "description"],
    }

    OPTIONAL_PAYLOAD_KEYS: dict[MessageType, list[str]] = {
        MessageType.TASK_ASSIGNMENT: ["deadline", "dependencies", "context"],
        MessageType.ARTIFACT_SUBMISSION: ["dependencies", "validation_status", "notes"],
        MessageType.CLARIFICATION_REQUEST: ["options", "urgency"],
        MessageType.BLOCKAGE_REPORT: ["workaround", "impact_assessment"],
        MessageType.REVISION_REQUEST: ["priority", "deadline"],
        MessageType.STATUS_UPDATE: ["current_task", "blockers", "eta"],
        MessageType.CONFLICT_ESCALATION: ["proposed_resolution", "urgency"],
        MessageType.APPROVAL_REQUEST: ["deadline", "impact", "alternatives"],
        MessageType.APPROVAL_RESPONSE: ["revision_notes", "deadline"],
        MessageType.SYSTEM_EVENT: ["severity", "affected_components"],
    }

    @classmethod
    def validate(cls, message: Message) -> list[str]:
        """Validate a message and return a list of validation errors.

        An empty list means the message is valid.
        """
        errors: list[str] = []

        required = cls.REQUIRED_PAYLOAD_KEYS.get(message.type, [])
        for key in required:
            if key not in message.payload:
                errors.append(
                    f"Message type '{message.type.value}' requires payload key '{key}'"
                )

        allowed = required + cls.OPTIONAL_PAYLOAD_KEYS.get(message.type, [])
        for key in message.payload:
            if key not in allowed:
                errors.append(
                    f"Message type '{message.type.value}' has unexpected payload key '{key}'"
                )

        return errors

    @classmethod
    def is_valid(cls, message: Message) -> bool:
        """Check if a message passes all validation rules."""
        return len(cls.validate(message)) == 0


def create_task_assignment(
    task_id: str,
    description: str,
    agent_role: AgentRole | str,
    sender: str = AgentRole.ORCHESTRATOR.value,
    recipient: str = "",
    **kwargs: Any,
) -> Message:
    """Factory for TASK_ASSIGNMENT messages."""
    priority = kwargs.pop("priority", Priority.NORMAL)
    role_value = getattr(agent_role, "value", agent_role)
    payload = {
        "task_id": task_id,
        "description": description,
        "agent_role": role_value,
        **kwargs,
    }
    return Message(
        sender=sender,
        recipient=recipient or role_value,
        type=MessageType.TASK_ASSIGNMENT,
        payload=payload,
        priority=priority,
    )


def create_artifact_submission(
    artifact_id: str,
    artifact_type: ArtifactType | str,
    content: dict[str, Any],
    version: str = "1.0",
    sender: str = "",
    recipient: str = AgentRole.ORCHESTRATOR.value,
    **kwargs: Any,
) -> Message:
    """Factory for ARTIFACT_SUBMISSION messages."""
    artifact_type_value = getattr(artifact_type, "value", artifact_type)
    payload = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type_value,
        "content": content,
        "version": version,
        **kwargs,
    }
    return Message(
        sender=sender,
        recipient=recipient,
        type=MessageType.ARTIFACT_SUBMISSION,
        payload=payload,
    )


def create_clarification_request(
    question: str,
    context: str,
    sender: str = "",
    recipient: str = AgentRole.HUMAN_OPERATOR.value,
    **kwargs: Any,
) -> Message:
    """Factory for CLARIFICATION_REQUEST messages."""
    payload = {"question": question, "context": context, **kwargs}
    return Message(
        sender=sender,
        recipient=recipient,
        type=MessageType.CLARIFICATION_REQUEST,
        payload=payload,
        requires_response=True,
    )


def create_system_event(
    event_type: str,
    description: str,
    sender: str = AgentRole.ORCHESTRATOR.value,
    recipient: str = "all",
    **kwargs: Any,
) -> Message:
    """Factory for SYSTEM_EVENT messages."""
    payload = {"event_type": event_type, "description": description, **kwargs}
    return Message(
        sender=sender,
        recipient=recipient,
        type=MessageType.SYSTEM_EVENT,
        payload=payload,
    )
