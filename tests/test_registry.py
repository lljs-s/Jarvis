"""Tests fuer die Werkzeug-Sammlung."""

from __future__ import annotations

import pytest

from jarvis.errors import ToolError
from jarvis.core.tools.files import default_tools
from jarvis.core.tools.registry import ToolRegistry
from jarvis.workspace import Workspace


def test_registry_kennt_ihre_werkzeuge(workspace: Workspace) -> None:
    registry = ToolRegistry(default_tools(workspace))
    assert len(registry) == 3
    assert registry.get("read_file").name == "read_file"


def test_registry_meldet_unbekanntes_werkzeug(workspace: Workspace) -> None:
    registry = ToolRegistry(default_tools(workspace))
    with pytest.raises(ToolError, match="Unbekanntes Werkzeug"):
        registry.get("rm_minus_rf")


def test_registry_verbietet_doppelte_namen(workspace: Workspace) -> None:
    tools = default_tools(workspace)
    registry = ToolRegistry(tools)
    with pytest.raises(ValueError):
        registry.add(tools[0])


def test_specs_sind_stabil_sortiert(workspace: Workspace) -> None:
    """Gleiche Reihenfolge = spaeter funktionierendes Prompt-Caching."""
    registry = ToolRegistry(default_tools(workspace))
    namen = [spec["name"] for spec in registry.specs()]
    assert namen == sorted(namen)
