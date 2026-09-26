"""Gemeinsame Test-Bausteine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jarvis.core.modules.formate import neue_id
from jarvis.workspace import Workspace

_OHNE = object()


def lege_bereich(ordner: Path, id: Any = _OHNE, **felder: Any) -> Path:
    """Legt einen Bereich (Ordner mit folder.json) an. `id=None` laesst sie weg."""
    ordner.mkdir(parents=True, exist_ok=True)
    daten: dict[str, Any] = {"schema": 1}
    if id is _OHNE:
        daten["id"] = neue_id("ord")
    elif id is not None:
        daten["id"] = id
    daten.update(felder)
    (ordner / "folder.json").write_text(json.dumps(daten), encoding="utf-8")
    return ordner


def lege_modul(ordner: Path, typ: str = "notizen", id: Any = _OHNE, **felder: Any) -> Path:
    """Legt ein Modul (Ordner mit module.json) an."""
    ordner.mkdir(parents=True, exist_ok=True)
    daten: dict[str, Any] = {"schema": 1, "typ": typ}
    if id is _OHNE:
        daten["id"] = neue_id("mod")
    elif id is not None:
        daten["id"] = id
    daten.update(felder)
    (ordner / "module.json").write_text(json.dumps(daten), encoding="utf-8")
    return ordner


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
