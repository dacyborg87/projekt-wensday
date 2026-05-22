"""Read-only defensive plugin placeholders for Wensday OS."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PluginResult:
    handled: bool
    answer: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: str = "medium"
    plugin_name: str | None = None


class DefensivePlugin(Protocol):
    name: str
    request_types: set[str]
    read_only: bool

    def can_handle(self, request: Any) -> bool:
        ...

    def run(self, request: Any) -> PluginResult:
        ...


class PluginRegistry:
    """Small read-only plugin registry for Phase 4."""

    def __init__(self) -> None:
        self._plugins: list[DefensivePlugin] = []

    def register(self, plugin: DefensivePlugin) -> None:
        if not getattr(plugin, "read_only", False):
            raise ValueError("Phase 4 plugins must be read-only.")
        self._plugins.append(plugin)

    def route(self, request: Any) -> PluginResult:
        for plugin in self._plugins:
            if request.request_type in getattr(plugin, "request_types", set()) and plugin.can_handle(request):
                result = plugin.run(request)
                result.plugin_name = getattr(plugin, "name", None)
                return result
        return PluginResult(handled=False)


def build_default_registry() -> PluginRegistry:
    """Return the Phase 4 registry. Active plugins are added in later phases."""
    return PluginRegistry()
