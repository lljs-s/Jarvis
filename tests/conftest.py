"""Gemeinsame Test-Bausteine."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.workspace import Workspace


@pytest.fixture()
def workspace(tmp_path: Path) -> Workspace:
    """Ein frischer, leerer Workspace in einem Wegwerf-Ordner."""
    return Workspace.open(tmp_path / "ws")


@pytest.fixture()
def filled_workspace(workspace: Workspace) -> Workspace:
    """Workspace mit ein paar Beispieldateien."""
    (workspace.root / "notizen").mkdir()
    (workspace.root / "notizen" / "todo.txt").write_text(
        "Mathe lernen\nHausaufgabe Physik\n", encoding="utf-8"
    )
    (workspace.root / "brief.md").write_text("# Brief\nHallo Welt\n", encoding="utf-8")
    (workspace.root / "bild.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00binary")
    return workspace


def symlink_or_skip(link: Path, ziel: Path, *, ordner: bool = False) -> None:
    """Legt einen Symlink an - oder ueberspringt den Test.

    Unter Windows darf ein normaler Nutzer nur dann Symlinks anlegen, wenn
    der Entwicklermodus aktiv ist. Ohne diesen Helfer wuerden die
    Symlink-Tests dort nicht "fehlschlagen", sondern nur nicht laufen -
    und genau das sollen sie auch sagen.
    """
    try:
        link.symlink_to(ziel, target_is_directory=ordner)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Symlinks sind auf diesem System nicht erlaubt: {exc}")
