"""Tests fuer die Datei-Werkzeuge (Etappe 1: nur lesend)."""

from __future__ import annotations

import pytest

from jarvis.core.tools.base import RiskLevel
from jarvis.core.tools.files import ListFilesTool, ReadFileTool, SearchTextTool, default_tools
from jarvis.errors import ToolError, WorkspaceViolation
from jarvis.workspace import Workspace


def test_alle_werkzeuge_sind_nur_lesend(filled_workspace: Workspace) -> None:
    """Etappe-1-Garantie: kein Werkzeug darf etwas veraendern."""
    for tool in default_tools(filled_workspace):
        assert tool.risk is RiskLevel.LOW, f"{tool.name} ist nicht LOW"


def test_list_files(filled_workspace: Workspace) -> None:
    ergebnis = ListFilesTool(filled_workspace).run()
    assert not ergebnis.is_error
    assert "brief.md" in ergebnis.content
    assert "notizen/todo.txt" in ergebnis.content


def test_list_files_leerer_ordner(workspace: Workspace) -> None:
    assert "leer" in ListFilesTool(workspace).run().content


def test_read_file(filled_workspace: Workspace) -> None:
    ergebnis = ReadFileTool(filled_workspace).run(path="notizen/todo.txt")
    assert "Mathe lernen" in ergebnis.content


def test_read_file_ausserhalb_wird_geblockt(filled_workspace: Workspace) -> None:
    with pytest.raises(WorkspaceViolation):
        ReadFileTool(filled_workspace).run(path="../../etc/passwd")


def test_read_file_fehlende_datei(filled_workspace: Workspace) -> None:
    with pytest.raises(ToolError):
        ReadFileTool(filled_workspace).run(path="gibtsnicht.txt")


def test_read_file_binaerdatei(filled_workspace: Workspace) -> None:
    with pytest.raises(ToolError, match="Binaerdatei"):
        ReadFileTool(filled_workspace).run(path="bild.png")


def test_read_file_kuerzt_grosse_dateien(workspace: Workspace) -> None:
    (workspace.root / "gross.txt").write_text("a" * 5000, encoding="utf-8")
    ergebnis = ReadFileTool(workspace, max_bytes=1024).run(path="gross.txt")
    assert "gekuerzt" in ergebnis.content
    assert len(ergebnis.content) < 2000


def test_search_text(filled_workspace: Workspace) -> None:
    ergebnis = SearchTextTool(filled_workspace).run(query="physik")  # Gross/klein egal
    assert "notizen/todo.txt:2" in ergebnis.content


def test_search_text_ohne_treffer(filled_workspace: Workspace) -> None:
    assert "Keine Treffer" in SearchTextTool(filled_workspace).run(query="Einhorn").content


def test_search_text_leere_anfrage(filled_workspace: Workspace) -> None:
    with pytest.raises(ToolError):
        SearchTextTool(filled_workspace).run(query="   ")


def test_werkzeug_beschreibungen_sind_vollstaendig(filled_workspace: Workspace) -> None:
    """Ohne sauberes Schema kann das Modell das Werkzeug nicht benutzen."""
    for tool in default_tools(filled_workspace):
        spec = tool.spec()
        assert spec["name"] and spec["description"]
        assert spec["input_schema"]["type"] == "object"
