"""Tests for the message bus module."""

import pytest

from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import Message, MessageType, Priority


class TestMessageBus:
    def test_register_and_deliver_to_agent(self, sample_message):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.register_agent("orchestrator", handler)
        bus.publish(sample_message)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(sample_message))
        assert len(received) == 1
        assert received[0].id == sample_message.id
        bus.clear()

    def test_subscribe_and_publish(self):
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe("topic-x", handler)

        msg = Message(sender="a", recipient="topic-x", type=MessageType.STATUS_UPDATE)
        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        assert len(received) == 1
        bus.clear()

    def test_multiple_subscribers(self):
        bus = MessageBus()
        results = []

        def make_handler(name):
            def handler(msg):
                results.append(name)
            return handler

        bus.subscribe("topic", make_handler("h1"))
        bus.subscribe("topic", make_handler("h2"))

        msg = Message(sender="a", recipient="topic", type=MessageType.STATUS_UPDATE)
        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        assert "h1" in results
        assert "h2" in results
        bus.clear()

    def test_dead_letter_for_unknown_recipient(self):
        bus = MessageBus()
        msg = Message(sender="a", recipient="nonexistent", type=MessageType.STATUS_UPDATE)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        dead = bus.get_dead_letters()
        assert len(dead) == 1
        assert dead[0].id == msg.id
        bus.clear()

    def test_delivery_status_tracking(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.register_agent("agent1", handler)
        msg = Message(sender="a", recipient="agent1", type=MessageType.STATUS_UPDATE)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        assert bus.get_delivery_status(msg.id) == "delivered"
        bus.clear()

    def test_message_history(self):
        bus = MessageBus()
        msg1 = Message(sender="agent_a", recipient="agent_b", type=MessageType.STATUS_UPDATE)

        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg1))
        history = bus.get_message_history()
        assert len(history) == 1

        history_filtered = bus.get_message_history(sender="agent_a")
        assert len(history_filtered) == 1

        history_filtered = bus.get_message_history(sender="other")
        assert len(history_filtered) == 0
        bus.clear()

    def test_unsubscribe(self):
        bus = MessageBus()
        received = []

        def handler(msg):
            received.append(msg)

        bus.subscribe("topic", handler)
        bus.unsubscribe("topic", handler)

        msg = Message(sender="a", recipient="topic", type=MessageType.STATUS_UPDATE)
        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        assert len(received) == 0
        bus.clear()

    def test_unregister_agent(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.register_agent("agent1", handler)
        bus.unregister_agent("agent1")

        msg = Message(sender="a", recipient="agent1", type=MessageType.STATUS_UPDATE)
        import asyncio

        asyncio.get_event_loop().run_until_complete(bus.publish(msg))
        assert len(bus.get_dead_letters()) == 1
        bus.clear()


class TestPriorityQueue:
    def test_enqueue_dequeue_order(self):
        bus = MessageBus()
        low = Message(
            sender="a", recipient="b", type=MessageType.STATUS_UPDATE, priority=Priority.LOW
        )
        high = Message(
            sender="a", recipient="b", type=MessageType.STATUS_UPDATE, priority=Priority.HIGH
        )
        normal = Message(
            sender="a", recipient="b", type=MessageType.STATUS_UPDATE, priority=Priority.NORMAL
        )

        import asyncio

        loop = asyncio.get_event_loop()

        loop.run_until_complete(bus.enqueue(low))
        loop.run_until_complete(bus.enqueue(high))
        loop.run_until_complete(bus.enqueue(normal))

        first = loop.run_until_complete(bus.dequeue())
        assert first.priority == Priority.HIGH

        second = loop.run_until_complete(bus.dequeue())
        assert second.priority == Priority.NORMAL

        third = loop.run_until_complete(bus.dequeue())
        assert third.priority == Priority.LOW
        bus.clear()

    def test_dequeue_empty_returns_none(self):
        bus = MessageBus()
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(bus.dequeue())
        assert result is None
        bus.clear()
