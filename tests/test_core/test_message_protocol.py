"""Tests for the message protocol module."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageSerializer,
    MessageType,
    MessageValidator,
    Priority,
    create_artifact_submission,
    create_task_assignment,
    create_system_event,
)


class TestMessage:
    def test_create_message_with_defaults(self):
        msg = Message(sender="agent1", recipient="agent2", type=MessageType.STATUS_UPDATE)
        assert msg.id
        assert msg.sender == "agent1"
        assert msg.recipient == "agent2"
        assert msg.priority == Priority.NORMAL
        assert msg.requires_response is False
        assert msg.timeout_seconds == 300
        assert msg.payload == {}
        assert msg.correlation_id is None

    def test_message_id_is_valid_uuid(self):
        msg = Message(sender="a", recipient="b", type=MessageType.STATUS_UPDATE)
        uuid.UUID(msg.id)

    def test_message_id_validation_rejects_invalid_uuid(self):
        with pytest.raises(ValidationError):
            Message(id="not-a-uuid", sender="a", recipient="b", type=MessageType.STATUS_UPDATE)

    def test_timeout_must_be_positive(self):
        with pytest.raises(ValidationError):
            Message(sender="a", recipient="b", type=MessageType.STATUS_UPDATE, timeout_seconds=0)

    def test_is_expired_returns_false_for_recent_message(self):
        msg = Message(sender="a", recipient="b", type=MessageType.STATUS_UPDATE)
        assert not msg.is_expired()

    def test_is_expired_returns_true_for_old_message(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        msg = Message(
            sender="a",
            recipient="b",
            type=MessageType.STATUS_UPDATE,
            timestamp=past,
            timeout_seconds=1,
        )
        assert msg.is_expired()

    def test_create_reply_links_via_correlation_id(self):
        msg = Message(sender="orchestrator", recipient="pm", type=MessageType.TASK_ASSIGNMENT)
        reply = msg.create_reply(
            sender="pm",
            msg_type=MessageType.ARTIFACT_SUBMISSION,
            payload={"key": "value"},
        )
        assert reply.sender == "pm"
        assert reply.recipient == "orchestrator"
        assert reply.correlation_id == msg.id
        assert reply.payload == {"key": "value"}


class TestMessageSerializer:
    def test_roundtrip_dict(self):
        msg = Message(
            sender="pm",
            recipient="orchestrator",
            type=MessageType.ARTIFACT_SUBMISSION,
            payload={"artifact_id": "x"},
            priority=Priority.HIGH,
        )
        data = MessageSerializer.to_dict(msg)
        restored = MessageSerializer.from_dict(data)
        assert restored.id == msg.id
        assert restored.sender == msg.sender
        assert restored.payload == msg.payload
        assert restored.priority == Priority.HIGH

    def test_roundtrip_json(self):
        msg = Message(sender="pm", recipient="orch", type=MessageType.STATUS_UPDATE)
        json_str = MessageSerializer.to_json(msg)
        restored = MessageSerializer.from_json(json_str)
        assert restored.id == msg.id
        assert restored.sender == msg.sender


class TestMessageValidator:
    def test_valid_task_assignment(self):
        msg = Message(
            sender="orchestrator",
            recipient="pm",
            type=MessageType.TASK_ASSIGNMENT,
            payload={
                "task_id": "t1",
                "description": "do stuff",
                "agent_role": "product_manager",
            },
        )
        assert MessageValidator.is_valid(msg)

    def test_missing_required_key(self):
        msg = Message(
            sender="orchestrator",
            recipient="pm",
            type=MessageType.TASK_ASSIGNMENT,
            payload={"task_id": "t1"},
        )
        errors = MessageValidator.validate(msg)
        assert len(errors) > 0
        assert not MessageValidator.is_valid(msg)

    def test_unexpected_payload_key(self):
        msg = Message(
            sender="o",
            recipient="a",
            type=MessageType.TASK_ASSIGNMENT,
            payload={
                "task_id": "t1",
                "description": "d",
                "agent_role": "pm",
                "unexpected_field": "oops",
            },
        )
        errors = MessageValidator.validate(msg)
        assert any("unexpected" in e.lower() for e in errors)

    def test_all_message_types_have_required_keys_defined(self):
        for msg_type in MessageType:
            assert msg_type in MessageValidator.REQUIRED_PAYLOAD_KEYS


class TestFactoryFunctions:
    def test_create_task_assignment(self):
        msg = create_task_assignment(
            task_id="t1",
            description="test task",
            agent_role=ArtifactType.SOURCE_CODE,
            recipient="writer",
        )
        assert msg.type == MessageType.TASK_ASSIGNMENT
        assert msg.payload["task_id"] == "t1"
        assert msg.payload["description"] == "test task"

    def test_create_artifact_submission(self):
        msg = create_artifact_submission(
            artifact_id="a1",
            artifact_type=ArtifactType.PRD,
            content={"summary": "Test"},
            sender="pm",
        )
        assert msg.type == MessageType.ARTIFACT_SUBMISSION
        assert msg.payload["artifact_id"] == "a1"

    def test_create_system_event(self):
        msg = create_system_event(
            event_type="startup",
            description="System starting",
        )
        assert msg.type == MessageType.SYSTEM_EVENT
        assert msg.payload["event_type"] == "startup"
