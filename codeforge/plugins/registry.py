"""Plugin registry: manages custom agent plugin registration.

Handles registration, validation, and lifecycle management
for user-defined agent plugins in the CodeForge system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from codeforge.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RegisteredPlugin:
    name: str
    module: object
    version: str = "0.1.0"
    metadata: dict[str, Any] = field(default_factory=dict)


class PluginRegistry:
    def __init__(self):
        self._plugins: dict[str, RegisteredPlugin] = {}

    def register(
        self,
        name: str,
        module: object,
        version: str = "0.1.0",
        metadata: dict[str, Any] | None = None,
    ) -> RegisteredPlugin:
        plugin = RegisteredPlugin(
            name=name,
            module=module,
            version=version,
            metadata=metadata or {},
        )
        self._plugins[name] = plugin
        logger.info(f"Plugin registered: {name} v{version}")
        return plugin

    def unregister(self, name: str) -> bool:
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"Plugin unregistered: {name}")
            return True
        return False

    def get_plugin(self, name: str) -> RegisteredPlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.name,
                "version": p.version,
                "metadata": p.metadata,
            }
            for p in self._plugins.values()
        ]

    @property
    def count(self) -> int:
        return len(self._plugins)

    def clear(self) -> None:
        self._plugins.clear()
