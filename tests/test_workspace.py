"""Der wichtigste Test des Projekts: kommt jemand aus dem Workspace heraus?"""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.errors import ToolError, WorkspaceViolation
from jarvis.workspace import Workspace

# Jeder dieser Pfade MUSS abgelehnt werden.
AUSBRUCHSVERSUCHE = [
    "../geheim.txt",
    "../../etc/passwd",
    "notizen/../../draussen.txt",
    "/etc/passwd",
    "/",
    "C:\\Windows\\system.ini",
    "C:/Windows/system.ini",
    "\\\\server\\freigabe\\datei.txt",
    "~/.ssh/id_rsa",
    "~",
    "ordner/~/datei",
    "datei\x00.txt",
    "CON",
    "notizen/NUL.txt",
]


@pytest.mark.parametrize("pfad", AUSBRUCHSVERSUCHE)
def test_ausbruchsversuche_werden_abgelehnt(workspace: Workspace, pfad: str) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(pfad)


@pytest.mark.parametrize(
    "pfad,erwartet",
    [
        ("datei.txt", "datei.txt"),
        ("./datei.txt", "datei.txt"),
        ("notizen/todo.txt", "notizen/todo.txt"),
        ("notizen\\todo.txt", "notizen/todo.txt"),  # Windows-Schreibweise
        ("a/./b/c.txt", "a/b/c.txt"),
        ("  datei.txt  ", "datei.txt"),  # Leerzeichen aussen
        ("", "."),
        (".", "."),
    ],
)
def test_erlaubte_pfade(workspace: Workspace, pfad: str, erwartet: str) -> None:
    ziel = workspace.resolve(pfad)
    assert workspace.label(ziel) == erwartet
    assert ziel == workspace.root or workspace.root in ziel.parents


def test_symlink_nach_draussen_wird_erkannt(workspace: Workspace, tmp_path: Path) -> None:
    """Ein Symlink im Workspace darf kein Schlupfloch sein."""
    draussen = tmp_path / "draussen.txt"
    draussen.write_text("geheim", encoding="utf-8")
    link = workspace.root / "harmlos.txt"
    link.symlink_to(draussen)

    with pytest.raises(WorkspaceViolation):
        workspace.resolve("harmlos.txt")


def test_symlink_ordner_nach_draussen_wird_erkannt(workspace: Workspace, tmp_path: Path) -> None:
    ziel_ordner = tmp_path / "extern"
    ziel_ordner.mkdir()
    (ziel_ordner / "x.txt").write_text("geheim", encoding="utf-8")
    (workspace.root / "ordner").symlink_to(ziel_ordner, target_is_directory=True)

    with pytest.raises(WorkspaceViolation):
        workspace.resolve("ordner/x.txt")


def test_pfad_muss_text_sein(workspace: Workspace) -> None:
    with pytest.raises(WorkspaceViolation):
        workspace.resolve(42)  # type: ignore[arg-type]


def test_resolve_file_verlangt_existierende_datei(filled_workspace: Workspace) -> None:
    assert filled_workspace.resolve_file("brief.md").is_file()

    with pytest.raises(ToolError):
        filled_workspace.resolve_file("gibtsnicht.txt")

    with pytest.raises(ToolError):
        filled_workspace.resolve_file("notizen")  # ist ein Ordner


def test_resolve_erlaubt_noch_nicht_existierende_datei(workspace: Workspace) -> None:
    """Fuer spaeteres Schreiben (Etappe 2) muss ein neuer Pfad erlaubt sein."""
    ziel = workspace.resolve("neu/unterordner/datei.txt")
    assert not ziel.exists()
    assert workspace.root in ziel.parents


def test_iter_files_listet_rekursiv(filled_workspace: Workspace) -> None:
    namen = {filled_workspace.label(p) for p in filled_workspace.iter_files()}
    assert namen == {"brief.md", "bild.png", "notizen/todo.txt"}


def test_iter_files_unterordner(filled_workspace: Workspace) -> None:
    namen = {filled_workspace.label(p) for p in filled_workspace.iter_files("notizen")}
    assert namen == {"notizen/todo.txt"}


def test_workspace_wird_angelegt(tmp_path: Path) -> None:
    neu = tmp_path / "gibt" / "es" / "noch" / "nicht"
    space = Workspace.open(neu)
    assert space.root.is_dir()
    assert space.root == neu.resolve()
