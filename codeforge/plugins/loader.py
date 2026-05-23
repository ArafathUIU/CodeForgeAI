"""Plugin loader: discovers and loads custom agent plugins.

Scans plugin directories, validates plugin structure, and
loads Python modules dynamically for agent registration.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PluginInfo:
    name: str
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    entry_point: str = ""
    path: str = ""
    loaded: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "entry_point": self.entry_point,
            "loaded": self.loaded,
        }


class PluginLoader:
    def __init__(self, plugin_dirs: list[str] | None = None):
        self._plugin_dirs = plugin_dirs or ["plugins"]
        self._discovered: dict[str, PluginInfo] = {}

    def discover(self) -> list[PluginInfo]:
        self._discovered.clear()
        for search_dir in self._plugin_dirs:
            path = Path(search_dir)
            if not path.exists():
                continue

            for entry in path.iterdir():
                if entry.is_dir() and (entry / "plugin.json").exists():
                    info = self._parse_plugin_json(entry)
                    if info:
                        self._discovered[info.name] = info

        return list(self._discovered.values())

    def load_plugin(self, plugin_name: str) -> object | None:
        info = self._discovered.get(plugin_name)
        if not info:
            return None

        try:
            module_path = info.entry_point
            module = importlib.import_module(module_path)
            info.loaded = True
            return module
        except ImportError as e:
            return None

    def get_discovered(self) -> list[PluginInfo]:
        return list(self._discovered.values())

    def _parse_plugin_json(self, plugin_dir: Path) -> PluginInfo | None:
        import json

        manifest_path = plugin_dir / "plugin.json"
        try:
            data = json.loads(manifest_path.read_text())
            return PluginInfo(
                name=data.get("name", plugin_dir.name),
                version=data.get("version", "0.1.0"),
                author=data.get("author", ""),
                description=data.get("description", ""),
                entry_point=data.get("entry_point", ""),
                path=str(plugin_dir),
            )
        except Exception:
            return None
