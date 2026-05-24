"""Plugin system for CodeForge.

Enables custom agent plugins with discovery, loading, and
registration support for extending the multi-agent system.
"""

from codeforge.plugins.loader import PluginInfo, PluginLoader
from codeforge.plugins.registry import PluginRegistry

__all__ = [
    "PluginInfo",
    "PluginLoader",
    "PluginRegistry",
]
