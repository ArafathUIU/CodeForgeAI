"""Shared test fixtures and configuration for CodeForge tests."""

import pytest

from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import Message, MessageType, Priority
from codeforge.core.state_store import EpisodicStore, SemanticStore
from codeforge.core.checkpoint import CheckpointManager
from codeforge.core.agent_registry import AgentRegistry
from codeforge.utils.config import Config, set_config


@pytest.fixture
def message_bus():
    bus = MessageBus()
    yield bus
    bus.clear()


@pytest.fixture
def episodic_store():
    store = EpisodicStore()
    yield store
    store.clear()


@pytest.fixture
def semantic_store():
    store = SemanticStore()
    yield store
    store.clear()


@pytest.fixture
def checkpoint_manager(tmp_path):
    return CheckpointManager(storage_path=tmp_path / "checkpoints")


@pytest.fixture
def agent_registry():
    return AgentRegistry()


@pytest.fixture
def sample_message():
    return Message(
        sender="product_manager",
        recipient="orchestrator",
        type=MessageType.ARTIFACT_SUBMISSION,
        payload={
            "artifact_id": "test-artifact-1",
            "artifact_type": "prd",
            "content": {"summary": "Test PRD"},
            "version": "1.0",
        },
        priority=Priority.NORMAL,
    )


@pytest.fixture
def task_message():
    return Message(
        sender="orchestrator",
        recipient="product_manager",
        type=MessageType.TASK_ASSIGNMENT,
        payload={
            "task_id": "task-001",
            "description": "Analyze specifications",
            "agent_role": "product_manager",
        },
        priority=Priority.HIGH,
    )


@pytest.fixture
def mock_config():
    config = Config()
    config.agent.timeout_seconds = 30
    config.agent.max_retry_attempts = 2
    set_config(config)
    yield config
