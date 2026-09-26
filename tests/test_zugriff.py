"""Schranken zwischen Agents und Modulsystem.

1. Kein Werkzeug darf folder.json, module.json oder .jarvis/ schreiben.
2. Ein Modell sieht nur Dateien, deren Datenschutzstufe es sehen darf.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path

import pytest
from conftest import lege_bereich, lege_modul
from test_agent import FakeModel

from jarvis.core.agent import Agent
from jarvis.core.models.base import ModelReply, ToolCall, ToolResultsMessage
from jarvis.core.modules.zugriff import pruefe_schreibzugriff
from jarvis.core.safety.datenschutz import Stufe
from jarvis.core.tools.files import ListFilesTool, ReadFileTool, SearchTextTool, default_tools
from jarvis.core.tools.registry import ToolRegistry
from jarvis.errors import DatenschutzVerstoss, WorkspaceViolation
from jarvis.workspace import Workspace

nur_windows = pytest.mark.skipif(os.name != "nt", reason="Braucht echtes Windows")

# ---------------------------------------------------------------------------
# 1. Schreibsperre
# ---------------------------------------------------------------------------

GESCHUETZT = [
    "bereiche/folder.json",
    "bereiche/Schule/folder.json",
    "bereiche/Schule/Mathe/module.json",
    "bereiche/Schule/Mathe/MODULE.JSON",
    "bereiche\\Schule\\Folder.Json",
    ".jarvis/auftraege/auf_1234.json",
    ".JARVIS/typen/neu.json",
    ".jarvis",
]


@pytest.mark.parametrize("pfad", GESCHUETZT)
def test_werkzeuge_duerfen_verwaltungsdateien_nicht_schreiben(
    workspace: Workspace, pfad: str
) -> None:
    with pytest.raises(WorkspaceViolation, match="Verwaltung von Jarvis"):
        pruefe_schreibzugriff(workspace, pfad)


def test_normale_dateien_bleiben_schreibbar(workspace: Workspace) -> None:
    ziel = pruefe_schreibzugriff(workspace, "bereiche/Schule/Mathe/notizen/formel.md")
    assert ziel.name == "formel.md"


def test_waechter_gilt_weiterhin(workspace: Workspace) -> None:
    with pytest.raises(WorkspaceViolation):
        pruefe_schreibzugriff(workspace, "../draussen.txt")


def _kurzname(pfad: Path) -> str | None:
    """Der 8.3-Kurzname, den Windows fuer lange Namen vergeben kann."""
    puffer = ctypes.create_unicode_buffer(1024)
    laenge = ctypes.windll.kernel32.GetShortPathNameW(str(pfad), puffer, 1024)  # type: ignore[attr-defined]
    if laenge == 0:
        return None
    kurz = Path(puffer.value).name
    return kurz if kurz.casefold() != pfad.name.casefold() else None


@nur_windows
def test_kurzname_umgeht_die_sperre_nicht(workspace: Workspace) -> None:
    """MODULE~1.JSO ist unter Windows u. U. dieselbe Datei wie module.json."""
    modul = lege_modul(workspace.root / "bereiche" / "M")
    kurz = _kurzname(modul / "module.json")
    if kurz is None:
        pytest.skip("8.3-Kurznamen sind auf diesem Laufwerk abgeschaltet")
    with pytest.raises(WorkspaceViolation, match="Verwaltung von Jarvis"):
        pruefe_schreibzugriff(workspace, f"bereiche/M/{kurz}")


@nur_windows
def test_junction_in_den_systemordner(workspace: Workspace) -> None:
    """Ein Umweg ueber eine Junction fuehrt trotzdem nicht nach .jarvis."""
    system = workspace.root / ".jarvis"
    system.mkdir()
    ergebnis = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(workspace.root / "tarnung"), str(system)],
        capture_output=True,
        text=True,
        check=False,
    )
    if ergebnis.returncode != 0:
        pytest.skip(f"mklink /J nicht moeglich: {ergebnis.stdout} {ergebnis.stderr}")
    with pytest.raises(WorkspaceViolation, match="Verwaltung von Jarvis"):
        pruefe_schreibzugriff(workspace, "tarnung/auftrag.json")


# ---------------------------------------------------------------------------
# 2. Datenschutz-Sperre der Lese-Werkzeuge
# ---------------------------------------------------------------------------


@pytest.fixture()
def gemischt(workspace: Workspace) -> Workspace:
    """Drei Bereiche mit den drei Stufen, je ein Modul mit einer Datei."""
    b = lege_bereich(workspace.root / "bereiche", id=None)
    lege_bereich(b / "Schule")
    (lege_modul(b / "Schule" / "Mathe") / "formel.md").write_text("Pythagoras", encoding="utf-8")
    lege_bereich(b / "Firma", datenschutz="vertraulich")
    (lege_modul(b / "Firma" / "Kunden") / "kunde.md").write_text("Kundin Meier", encoding="utf-8")
    lege_bereich(b / "Privat", datenschutz="lokal")
    (lege_modul(b / "Privat" / "Tagebuch") / "heute.md").write_text(
        "Mein Geheimnis", encoding="utf-8"
    )
    (workspace.root / ".jarvis").mkdir()
    (workspace.root / ".jarvis" / "auftrag.json").write_text("Geheimnis", encoding="utf-8")
    (workspace.root / "lose.txt").write_text("frei", encoding="utf-8")
    return workspace


def test_liste_zeigt_nur_offenes(gemischt: Workspace) -> None:
    inhalt = ListFilesTool(gemischt).run().content
    assert "formel.md" in inhalt and "lose.txt" in inhalt
    assert "kunde.md" not in inhalt
    assert "heute.md" not in inhalt
    assert ".jarvis" not in inhalt
    assert "ausgeblendet" in inhalt


@pytest.mark.parametrize(
    "pfad",
    [
        "bereiche/Firma/Kunden/kunde.md",
        "bereiche/Privat/Tagebuch/heute.md",
        "bereiche/privat/tagebuch/HEUTE.md",
        ".jarvis/auftrag.json",
    ],
)
def test_lesen_ueber_der_stufe_wird_verweigert(gemischt: Workspace, pfad: str) -> None:
    with pytest.raises(DatenschutzVerstoss):
        ReadFileTool(gemischt).run(path=pfad)


def test_suche_verraet_keine_inhalte(gemischt: Workspace) -> None:
    inhalt = SearchTextTool(gemischt).run(query="Geheimnis").content
    assert "Keine Treffer" in inhalt
    assert "heute.md" not in inhalt


def test_unterordner_ueber_der_stufe_wird_verweigert(gemischt: Workspace) -> None:
    with pytest.raises(DatenschutzVerstoss):
        ListFilesTool(gemischt).run(subdir="bereiche/Privat")
    with pytest.raises(DatenschutzVerstoss):
        SearchTextTool(gemischt).run(query="x", subdir="bereiche/Firma")


def test_kaputter_bereich_ist_gesperrt(gemischt: Workspace) -> None:
    """Im Zweifel lokal - auch fuer die Werkzeuge."""
    kaputt = gemischt.root / "bereiche" / "Schule" / "folder.json"
    kaputt.write_text("{kaputt", encoding="utf-8")
    with pytest.raises(DatenschutzVerstoss):
        ReadFileTool(gemischt).run(path="bereiche/Schule/Mathe/formel.md")


def test_stufe_wird_bei_jedem_aufruf_neu_gelesen(gemischt: Workspace) -> None:
    werkzeug = ReadFileTool(gemischt)
    assert "Pythagoras" in werkzeug.run(path="bereiche/Schule/Mathe/formel.md").content
    lege_bereich(gemischt.root / "bereiche" / "Schule", datenschutz="lokal")
    with pytest.raises(DatenschutzVerstoss):
        werkzeug.run(path="bereiche/Schule/Mathe/formel.md")


def test_lokales_modell_duerfte_alles_sehen(gemischt: Workspace) -> None:
    """Fuer Ollama spaeter: mit erlaubt=LOKAL ist nichts gesperrt."""
    werkzeuge = {t.name: t for t in default_tools(gemischt, erlaubt=Stufe.LOKAL)}
    inhalt = werkzeuge["read_file"].run(path="bereiche/Privat/Tagebuch/heute.md").content
    assert "Mein Geheimnis" in inhalt


def test_standard_ist_nur_offen(gemischt: Workspace) -> None:
    """Sicher by default: wer nichts angibt, bekommt die strengste Sicht."""
    for werkzeug in default_tools(gemischt):
        assert werkzeug.datenschutz.erlaubt is Stufe.OFFEN  # type: ignore[attr-defined]


def test_agent_bekommt_verbot_statt_inhalt(gemischt: Workspace) -> None:
    """Der ganze Weg: Modell fragt, Werkzeug verweigert, Inhalt fliesst nie hinaus."""
    modell = FakeModel(
        [
            ModelReply(
                text="",
                tool_calls=(
                    ToolCall(
                        id="t1",
                        name="read_file",
                        arguments={"path": "bereiche/Privat/Tagebuch/heute.md"},
                    ),
                ),
            ),
            ModelReply(text="Darauf habe ich keinen Zugriff."),
        ]
    )
    agent = Agent(model=modell, tools=ToolRegistry(default_tools(gemischt)))
    agent.run("Lies mein Tagebuch")

    antwort = modell.calls[1][-1]
    assert isinstance(antwort, ToolResultsMessage)
    ergebnis = antwort.outcomes[0]
    assert ergebnis.is_error and "VERBOTEN" in ergebnis.content
    assert "Geheimnis" not in ergebnis.content
