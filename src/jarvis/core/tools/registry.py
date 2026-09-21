"""Sammlung der Werkzeuge, die einem Agenten zur Verfuegung stehen."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ...errors import ToolError
from .base import RiskLevel, Tool


class ToolRegistry:
    """Haelt Werkzeuge unter ihrem Namen und liefert ihre Beschreibungen."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.add(tool)

    def add(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Werkzeug {tool.name!r} ist bereits registriert.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            known = ", ".join(sorted(self._tools)) or "(keine)"
            raise ToolError(f"Unbekanntes Werkzeug {name!r}. Verfuegbar: {known}") from None

    def specs(self) -> list[dict[str, Any]]:
        # Feste Reihenfolge: gleiche Anfrage -> gleiche Bytes -> spaeter
        # funktioniert Prompt-Caching zuverlaessig.
        return [self._tools[name].spec() for name in sorted(self._tools)]

    def max_risk(self) -> RiskLevel:
        return max((t.risk for t in self._tools.values()), default=RiskLevel.LOW)

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)
