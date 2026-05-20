"""Message bus for routing and delivering messages between agents.

Provides a priority-based queue, publish-subscribe routing, and
delivery tracking with acknowledgements and dead-letter handling.
"""

from __future__ import annotations

import asyncio
import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from codeforge.core.message_protocol import Message, Priority
from codeforge.utils.logging import get_logger

logger = get_logger(__name__)

MessageHandler = Callable[[Message], Any]
"""Type alias for message handler callbacks."""


@dataclass(order=True)
class _PrioritizedMessage:
    """Internal wrapper for priority queue ordering."""

    priority: int
    timestamp: datetime = field(compare=False)
    message: Message = field(compare=False)


class MessageBus:
    """Central message bus for inter-agent communication.

    Handles:
    - Priority-based message queuing
    - Pub/sub topic routing
    - Direct agent-to-agent delivery
    - Delivery acknowledgements
    - Dead-letter queue for undeliverable messages
    - Message history for debugging
    """

    def __init__(self):
        self._queue: list[_PrioritizedMessage] = []
        self._subscribers: dict[str, list[MessageHandler]] = {}
        self._agent_handlers: dict[str, MessageHandler] = {}
        self._delivery_status: dict[str, str] = {}
        self._dead_letter: list[Message] = []
        self._message_history: list[Message] = []
        self._lock = asyncio.Lock()

    async def publish(self, message: Message) -> None:
        """Publish a message to all subscribers of the recipient topic."""
        async with self._lock:
            self._message_history.append(message)
            self._delivery_status[message.id] = "published"

            delivered = False

            handler = self._agent_handlers.get(message.recipient)
            if handler:
                try:
                    await self._dispatch_to_handler(message, handler)
                    self._delivery_status[message.id] = "delivered"
                    delivered = True
                except Exception as e:
                    logger.error(
                        f"Failed to deliver message {message.id} to {message.recipient}",
                        extra={"error": str(e), "message_id": message.id},
                    )
                    self._delivery_status[message.id] = "failed"

            subscribers = self._subscribers.get(message.recipient, [])
            for handler_fn in subscribers:
                try:
                    await self._dispatch_to_handler(message, handler_fn)
                    if not delivered:
                        self._delivery_status[message.id] = "delivered"
                        delivered = True
                except Exception as e:
                    logger.error(
                        f"Failed to deliver message {message.id} to subscriber",
                        extra={"error": str(e)},
                    )

            if not delivered:
                self._dead_letter.append(message)
                self._delivery_status[message.id] = "dead_letter"
                logger.warning(
                    f"No handler found for message {message.id} to '{message.recipient}'"
                )

    async def _dispatch_to_handler(
        self, message: Message, handler: MessageHandler
    ) -> None:
        """Dispatch a message to a handler, supporting both sync and async."""
        result = handler(message)
        if asyncio.iscoroutine(result):
            await result

    async def enqueue(self, message: Message) -> None:
        """Add a message to the priority queue for ordered processing."""
        priority_map = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.NORMAL: 2,
            Priority.LOW: 3,
        }
        priority_value = priority_map.get(message.priority, 2)

        async with self._lock:
            heapq.heappush(
                self._queue,
                _PrioritizedMessage(
                    priority=priority_value,
                    timestamp=message.timestamp,
                    message=message,
                ),
            )
            self._delivery_status[message.id] = "queued"
            self._message_history.append(message)

    async def dequeue(self) -> Message | None:
        """Dequeue the highest priority message."""
        async with self._lock:
            if not self._queue:
                return None
            item = heapq.heappop(self._queue)
            self._delivery_status[item.message.id] = "dequeued"
            return item.message

    async def process_queue(self) -> None:
        """Process all queued messages in priority order."""
        while True:
            message = await self.dequeue()
            if message is None:
                break
            await self.publish(message)

    def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """Subscribe a handler to a topic/agent ID.

        Multiple handlers can subscribe to the same topic.
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug(f"Handler subscribed to topic '{topic}'")

    def unsubscribe(self, topic: str, handler: MessageHandler) -> None:
        """Remove a handler subscription from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                h for h in self._subscribers[topic] if h is not handler
            ]
            if not self._subscribers[topic]:
                del self._subscribers[topic]

    def register_agent(self, agent_id: str, handler: MessageHandler) -> None:
        """Register an agent handler for direct message delivery.

        Only one handler per agent ID. Registers the old one.
        """
        self._agent_handlers[agent_id] = handler
        logger.info(f"Agent '{agent_id}' registered on message bus")

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent registration."""
        self._agent_handlers.pop(agent_id, None)
        logger.info(f"Agent '{agent_id}' unregistered from message bus")

    def get_delivery_status(self, message_id: str) -> str | None:
        """Get the delivery status of a specific message."""
        return self._delivery_status.get(message_id)

    def get_dead_letters(self) -> list[Message]:
        """Get all messages in the dead letter queue."""
        return list(self._dead_letter)

    def get_message_history(
        self, sender: str | None = None, since: datetime | None = None
    ) -> list[Message]:
        """Query message history with optional filters."""
        result = self._message_history
        if sender:
            result = [m for m in result if m.sender == sender]
        if since:
            result = [m for m in result if m.timestamp >= since]
        return result

    async def retry_dead_letters(self) -> int:
        """Attempt to redeliver all dead-letter messages."""
        async with self._lock:
            dead = list(self._dead_letter)
            self._dead_letter.clear()

        count = 0
        for message in dead:
            try:
                await self.publish(message)
                count += 1
            except Exception as e:
                self._dead_letter.append(message)
                logger.warning(
                    f"Dead letter retry failed for {message.id}",
                    extra={"error": str(e)},
                )
        return count

    def clear(self) -> None:
        """Clear all queues and history (useful for testing)."""
        self._queue.clear()
        self._subscribers.clear()
        self._agent_handlers.clear()
        self._delivery_status.clear()
        self._dead_letter.clear()
        self._message_history.clear()

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    @property
    def subscriber_count(self) -> int:
        return sum(len(h) for h in self._subscribers.values())
