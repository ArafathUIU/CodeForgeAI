"""Tests for the agent registry and base agent."""

import asyncio

import pytest

from codeforge.core.agent_registry import (
    AgentRegistry,
    AgentState,
    BaseAgent,
)
from codeforge.core.message_protocol import Message, MessageType
from codeforge.utils.exceptions import AgentNotFoundError


class MockAgent(BaseAgent):
    def __init__(self, agent_id, message_bus, episodic=None, semantic=None):
        super().__init__(agent_id, message_bus, episodic, semantic)
        self.received_messages = []
        self._initialized = False

    async def process_message(self, message):
        self.received_messages.append(message)

    async def initialize(self):
        self._initialized = True
        self._state = AgentState.IDLE

    def get_status_report(self):
        return super().get_status_report()


class TestAgentRegistry:
    def test_register_agent(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)
        assert registry.count == 1

    def test_get_agent(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)
        retrieved = registry.get_agent("pm")
        assert retrieved.agent_id == "pm"

    def test_get_nonexistent_agent_raises(self):
        registry = AgentRegistry()
        with pytest.raises(AgentNotFoundError):
            registry.get_agent("nonexistent")

    def test_get_by_role(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)

        matches = registry.get_by_role("mockagent")
        assert len(matches) == 1

    def test_list_agents(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("agent1", message_bus)
        registry.register(agent)
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "agent1"

    def test_unregister_agent(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)
        registry.unregister("pm")
        assert registry.count == 0

    def test_initialize_all(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(registry.initialize_all())
        assert agent._initialized

    def test_shutdown_all(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(registry.shutdown_all())
        assert agent.state == AgentState.TERMINATED

    def test_get_status_report(self, message_bus):
        registry = AgentRegistry()
        agent = MockAgent("pm", message_bus)
        registry.register(agent)
        report = registry.get_status_report()
        assert report["total_agents"] == 1
