"""Datei-Werkzeuge fuer Etappe 1 - alle nur lesend (Risiko LOW).

Schreiben, Ueberschreiben und Loeschen kommen bewusst erst in Etappe 2,
zusammen mit Diff-Vorschau und deiner Bestaetigung.

Alle drei Werkzeuge holen ihre Pfade ausschliesslich vom Workspace-Waechter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from ...errors import ToolError
from ...workspace import Workspace
from .base import RiskLevel, Tool, ToolResult

# Wie viele Treffer bzw. Zeilen geben wir hoechstens zurueck? Ein Agent, der
# eine 10-MB-Datei ins Gespraech zieht, verbrennt nur Geld.
_MAX_MATCHES = 50


def _read_text(path: Path, workspace: Workspace, max_bytes: int) -> str:
    """Liest eine Textdatei, erkennt Binaerdateien und kuerzt zu grosse."""
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    if b"\x00" in data:
        raise ToolError(
            f"{workspace.label(path)} sieht nach einer Binaerdatei aus "
            "(Bild, PDF, ZIP ...) und kann nicht als Text gelesen werden."
        )
    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += f"\n\n[... gekuerzt bei {max_bytes} Bytes ...]"
    return text


class ListFilesTool(Tool):
    """Zeigt, welche Dateien es im Workspace gibt."""

    name = "list_files"
    description = (
        "Listet Dateien im Workspace auf (rekursiv, alphabetisch). "
        "Nutze das zuerst, um herauszufinden, welche Dateien es ueberhaupt gibt."
    )
    risk = RiskLevel.LOW
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "subdir": {
                "type": "string",
                "description": "Unterordner relativ zum Workspace. Standard: '.' (alles).",
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, subdir: str = ".", **_: Any) -> ToolResult:
        files = self.workspace.iter_files(subdir)
        if not files:
            return ToolResult(f"Keine Dateien in '{subdir}'. Der Ordner ist leer.")
        lines = [
            f"{self.workspace.label(p)}  ({p.stat().st_size} Bytes)" for p in files
        ]
        return ToolResult(f"{len(files)} Datei(en):\n" + "\n".join(lines))


class ReadFileTool(Tool):
    """Liest eine Textdatei aus dem Workspace."""

    name = "read_file"
    description = (
        "Liest den Inhalt einer Textdatei im Workspace. "
        "Der Pfad ist immer relativ zum Workspace, z. B. 'notizen/todo.txt'."
    )
    risk = RiskLevel.LOW
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Pfad relativ zum Workspace, z. B. 'texte/brief.md'.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    }

    def __init__(self, workspace: Workspace, max_bytes: int = 200_000) -> None:
        self.workspace = workspace
        self.max_bytes = max_bytes

    def run(self, path: str = "", **_: Any) -> ToolResult:
        target = self.workspace.resolve_file(path)
        text = _read_text(target, self.workspace, self.max_bytes)
        return ToolResult(f"--- {self.workspace.label(target)} ---\n{text}")


class SearchTextTool(Tool):
    """Sucht einen Text in allen Dateien des Workspace."""

    name = "search_text"
    description = (
        "Sucht eine Zeichenkette in allen Textdateien des Workspace und gibt "
        "die Fundstellen mit Dateiname und Zeilennummer zurueck."
    )
    risk = RiskLevel.LOW
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Gesuchter Text (ohne Gross/Klein-Beachtung)."},
            "subdir": {"type": "string", "description": "Optionaler Unterordner. Standard: '.'"},
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(self, workspace: Workspace, max_bytes: int = 200_000) -> None:
        self.workspace = workspace
        self.max_bytes = max_bytes

    def run(self, query: str = "", subdir: str = ".", **_: Any) -> ToolResult:
        if not query.strip():
            raise ToolError("Der Suchbegriff darf nicht leer sein.")
        needle = query.lower()
        hits: list[str] = []
        for path in self.workspace.iter_files(subdir):
            try:
                text = _read_text(path, self.workspace, self.max_bytes)
            except ToolError:
                continue  # Binaerdateien ueberspringen wir stillschweigend
            for number, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    hits.append(f"{self.workspace.label(path)}:{number}: {line.strip()[:200]}")
                    if len(hits) >= _MAX_MATCHES:
                        hits.append(f"[... weitere Treffer ausgelassen, Grenze {_MAX_MATCHES} ...]")
                        return ToolResult("\n".join(hits))
        if not hits:
            return ToolResult(f"Keine Treffer fuer {query!r}.")
        return ToolResult(f"{len(hits)} Treffer:\n" + "\n".join(hits))


def default_tools(workspace: Workspace, max_read_bytes: int = 200_000) -> list[Tool]:
    """Die Werkzeugausstattung von Etappe 1: nur lesen."""
    return [
        ListFilesTool(workspace),
        ReadFileTool(workspace, max_read_bytes),
        SearchTextTool(workspace, max_read_bytes),
    ]
