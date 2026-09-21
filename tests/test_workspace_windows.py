"""Windows-spezifische Angriffe auf den Workspace-Waechter.

Wichtig fuer das Verstaendnis: fast alle Tests hier laufen auf JEDEM
Betriebssystem. Der Waechter prueft Pfade naemlich rein textlich
(`split_relative`), bevor er das Dateisystem anfasst - dadurch lehnt er
"CON" oder "C:\\Windows" auch unter Linux ab. Nur die Tests fuer Junctions
und die Gross-/Kleinschreibung des echten Dateisystems brauchen wirklich
Windows; sie werden anderswo uebersprungen.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from jarvis.errors import WorkspaceViolation
from jarvis.workspace import Workspace, split_relative

nur_windows = pytest.mark.skipif(os.name != "nt", reason="Braucht echtes Windows")


# ---------------------------------------------------------------------------
# Laufwerksbuchstaben und Netzwerkpfade
# ---------------------------------------------------------------------------

LAUFWERKE_UND_UNC = [
    "C:\\Windows\\system.ini",
    "C:/Windows/system.ini",
    "c:\\windows\\system.ini",
    "D:\\Daten\\geheim.txt",
    "Z:/freigabe/datei.txt",
    "C:notizen.txt",            # laufwerksrelativ: "C:datei" heisst "aktueller Ordner auf C:"
    "C:",
    "\\\\server\\freigabe\\datei.txt",   # UNC
    "//server/freigabe/datei.txt",
    "\\\\?\\C:\\Windows\\system.ini",    # erweiterte Pfadsyntax umgeht normale Pruefungen
    "\\\\.\\pipe\\jarvis",               # Geraetenamensraum
    "\\\\127.0.0.1\\c$\\Windows",        # administrative Freigabe
]


@pytest.mark.parametrize("pfad", LAUFWERKE_UND_UNC)
def test_laufwerke_und_netzwerkpfade_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


# ---------------------------------------------------------------------------
# Reservierte Geraetenamen
# ---------------------------------------------------------------------------

RESERVIERTE_NAMEN = [
    "CON", "con", "CoN",
    "PRN", "AUX", "NUL", "nul",
    "COM1", "com9", "LPT1", "LPT9",
    "con.txt",                 # Endung hilft nicht: CON bleibt CON
    "NUL.log",
    "COM1.tar.gz",
    "notizen/CON",             # auch tief im Baum
    "CON/datei.txt",           # auch als Ordnername
    "nul ",                    # mit Leerzeichen dahinter
]


@pytest.mark.parametrize("pfad", RESERVIERTE_NAMEN)
def test_reservierte_geraetenamen_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


HARMLOSE_AEHNLICHE_NAMEN = [
    "conference.md",           # faengt mit CON an, ist aber nicht CON
    "COMIC.txt",
    "nulpunkt.csv",
    "auxiliar/notiz.txt",
    "lpt.txt",                 # ohne Ziffer nicht reserviert
    "com10.txt",               # nur COM1..COM9 sind reserviert
]


@pytest.mark.parametrize("pfad", HARMLOSE_AEHNLICHE_NAMEN)
def test_aehnliche_namen_bleiben_erlaubt(workspace: Workspace, pfad: str) -> None:
    ergebnis = workspace.resolve(pfad)
    assert workspace.contains(ergebnis)


# ---------------------------------------------------------------------------
# Punkte und Leerzeichen am Ende - Windows schneidet sie stillschweigend ab
# ---------------------------------------------------------------------------

PUNKTE_UND_LEERZEICHEN = [
    "bericht.txt.",            # wird unter Windows zu "bericht.txt"
    "bericht.txt...",
    "bericht.txt ",
    "bericht.txt . ",
    " bericht.txt",            # fuehrendes Leerzeichen im Namen
    "ordner /datei.txt",       # Leerzeichen am Ende eines Ordnernamens
    "ordner./datei.txt",
]


@pytest.mark.parametrize("pfad", PUNKTE_UND_LEERZEICHEN)
def test_punkte_und_leerzeichen_am_ende_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


def test_leerzeichen_innerhalb_bleiben_erlaubt(workspace: Workspace) -> None:
    """Nur am Rand ist das Leerzeichen gefaehrlich, mittendrin nicht."""
    ergebnis = workspace.resolve("meine notizen/liste des tages.txt")
    assert ergebnis.name == "liste des tages.txt"


def test_punkte_im_namen_bleiben_erlaubt(workspace: Workspace) -> None:
    ergebnis = workspace.resolve("archiv.2026/bericht.final.md")
    assert ergebnis.name == "bericht.final.md"


# ---------------------------------------------------------------------------
# Alternate Data Streams und verbotene Zeichen
# ---------------------------------------------------------------------------

VERBOTENE_ZEICHEN = [
    "datei.txt:geheim",            # Alternate Data Stream
    "datei.txt:geheim:$DATA",
    "ordner:stream/datei.txt",
    "*.txt",
    "datei?.txt",
    'datei".txt',
    "datei<1>.txt",
    "datei|pipe.txt",
]


@pytest.mark.parametrize("pfad", VERBOTENE_ZEICHEN)
def test_verbotene_zeichen_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


STEUERZEICHEN = ["datei\ntxt", "datei\ttxt", "datei\rtxt", "datei\x00txt", "datei\x1b[31m.txt"]


@pytest.mark.parametrize("pfad", STEUERZEICHEN)
def test_steuerzeichen_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


# ---------------------------------------------------------------------------
# Gross-/Kleinschreibung
# ---------------------------------------------------------------------------

def test_aehnlicher_ordnername_ist_kein_unterordner(tmp_path: Path) -> None:
    """"workspace_geheim" darf nicht als Teil von "workspace" durchgehen.

    Ein reiner Textvergleich ("faengt der Pfad mit dem Workspace an?")
    wuerde hier versagen. Deshalb vergleicht `contains` ganze Pfadteile.
    """
    workspace = Workspace.open(tmp_path / "workspace")
    nachbar = tmp_path / "workspace_geheim"
    nachbar.mkdir()
    assert not workspace.contains(nachbar / "datei.txt")
    assert workspace.contains(workspace.root / "datei.txt")


def test_contains_ignoriert_gross_kleinschreibung_wie_das_system(tmp_path: Path) -> None:
    """Unter Windows ist C:\\Temp dasselbe wie c:\\temp, unter Linux nicht."""
    workspace = Workspace.open(tmp_path / "ws")
    anders_geschrieben = Path(str(workspace.root).upper()) / "datei.txt"
    if os.name == "nt":
        assert workspace.contains(anders_geschrieben)
    else:
        assert not workspace.contains(anders_geschrieben)


@nur_windows
def test_gross_kleinschreibung_findet_dieselbe_datei(filled_workspace: Workspace) -> None:
    """Windows-Dateisysteme sind nicht case-sensitiv - der Waechter muss das aushalten."""
    original = filled_workspace.resolve_file("notizen/todo.txt")
    gross = filled_workspace.resolve_file("NOTIZEN/TODO.TXT")
    assert original.read_text(encoding="utf-8") == gross.read_text(encoding="utf-8")
    assert filled_workspace.contains(gross)


@nur_windows
def test_verschiedene_laufwerke_sind_nie_enthalten(workspace: Workspace) -> None:
    """Liegt der Workspace auf C:, ist nichts auf D: jemals drin."""
    anderes_laufwerk = Path("D:\\") / "daten" / "datei.txt"
    assert not workspace.contains(anderes_laufwerk)


# ---------------------------------------------------------------------------
# Junctions und symbolische Links (nur Windows)
# ---------------------------------------------------------------------------

@nur_windows
def test_junction_nach_draussen_wird_erkannt(workspace: Workspace, tmp_path: Path) -> None:
    """Eine Junction ist die Windows-Variante eines Ordner-Symlinks.

    Sie braucht KEINE Administratorrechte - deshalb ist sie der
    naheliegendste Ausbruchsweg unter Windows.
    """
    draussen = tmp_path / "draussen"
    draussen.mkdir(exist_ok=True)
    (draussen / "geheim.txt").write_text("streng geheim", encoding="utf-8")

    junction = workspace.root / "harmlos"
    ergebnis = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(draussen)],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        pytest.skip(f"mklink /J nicht moeglich: {ergebnis.stdout} {ergebnis.stderr}")

    with pytest.raises(WorkspaceViolation):
        workspace.resolve("harmlos/geheim.txt")


@nur_windows
def test_junction_innerhalb_bleibt_erlaubt(workspace: Workspace) -> None:
    """Eine Junction, die im Workspace bleibt, ist kein Ausbruch."""
    ziel = workspace.root / "echt"
    ziel.mkdir()
    (ziel / "notiz.txt").write_text("ok", encoding="utf-8")

    junction = workspace.root / "verweis"
    ergebnis = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(ziel)],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0:
        pytest.skip(f"mklink /J nicht moeglich: {ergebnis.stdout} {ergebnis.stderr}")

    aufgeloest = workspace.resolve("verweis/notiz.txt")
    assert aufgeloest.read_text(encoding="utf-8") == "ok"
    assert workspace.contains(aufgeloest)


@nur_windows
def test_dateisymlink_nach_draussen_wird_erkannt(workspace: Workspace, tmp_path: Path) -> None:
    """Symlinks brauchen unter Windows den Entwicklermodus - sonst Skip."""
    draussen = tmp_path / "draussen.txt"
    draussen.write_text("geheim", encoding="utf-8")
    link = workspace.root / "harmlos.txt"
    try:
        link.symlink_to(draussen)
    except OSError as exc:
        pytest.skip(f"Symlink nicht erlaubt (Entwicklermodus aus?): {exc}")

    with pytest.raises(WorkspaceViolation):
        workspace.resolve("harmlos.txt")


# ---------------------------------------------------------------------------
# Die reine Textpruefung direkt
# ---------------------------------------------------------------------------

def test_split_relative_zerlegt_beide_trennzeichen() -> None:
    assert split_relative("notizen\\schule\\mathe.txt") == ["notizen", "schule", "mathe.txt"]
    assert split_relative("notizen/schule/mathe.txt") == ["notizen", "schule", "mathe.txt"]


def test_split_relative_leere_angaben_meinen_den_workspace() -> None:
    assert split_relative("") == []
    assert split_relative(".") == []
    assert split_relative("./") == []


def test_split_relative_braucht_kein_dateisystem() -> None:
    """Der Beweis, dass diese Pruefung ueberall gleich ist: kein Workspace noetig."""
    with pytest.raises(WorkspaceViolation):
        split_relative("C:\\Windows")
    with pytest.raises(WorkspaceViolation):
        split_relative("CON")
    with pytest.raises(WorkspaceViolation):
        split_relative("..")
