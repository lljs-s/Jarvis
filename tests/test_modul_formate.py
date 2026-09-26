"""folder.json und module.json: was wird gelesen, was abgelehnt?"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import symlink_or_skip

from jarvis.core.modules.formate import (
    MAX_JSON_BYTES,
    SCHEMA_AKTUELL,
    lies_json,
    modul_aus_json,
    neue_id,
    ordner_aus_json,
    schreibe_json,
)
from jarvis.core.safety.datenschutz import Stufe
from jarvis.errors import WorkspaceViolation
from jarvis.workspace import Workspace

# -- Schema-Versionen (CLAUDE.md 5.2) ----------------------------------------


def test_hoehere_schema_version_wird_nicht_geraten() -> None:
    with pytest.raises(ValueError, match="neuer als dieses Jarvis"):
        ordner_aus_json({"schema": SCHEMA_AKTUELL + 1, "id": "ord_abcd1234"})
    with pytest.raises(ValueError, match="neuer als dieses Jarvis"):
        modul_aus_json({"schema": 99, "typ": "notizen"})


@pytest.mark.parametrize("schema", [None, 0, -1, "1", 1.0, True])
def test_fehlende_oder_ungueltige_schema_version(schema: object) -> None:
    roh: dict[str, Any] = {"id": "ord_abcd1234"}
    if schema is not None:
        roh["schema"] = schema
    with pytest.raises(ValueError, match="schema"):
        ordner_aus_json(roh)


# -- Datenschutz: sicherheitsrelevant, deshalb harter Fehler -----------------


@pytest.mark.parametrize("stufe", ["Offen", "geheim", 1, True, ""])
def test_ungueltige_stufe_ist_ein_fehler(stufe: object) -> None:
    with pytest.raises(ValueError):
        ordner_aus_json({"schema": 1, "datenschutz": stufe})
    with pytest.raises(ValueError):
        modul_aus_json({"schema": 1, "typ": "notizen", "datenschutz": stufe})


def test_gueltige_felder_werden_gelesen() -> None:
    datei = ordner_aus_json(
        {
            "schema": 1,
            "id": "ord_abcd1234",
            "beschreibung": "Schule",
            "datenschutz": "vertraulich",
            "datenschutz_grund": {"art": "verschoben", "text": "aus X", "datum": "2026-09-26"},
            "symbol": "buch",
            "farbe": "blau",
            "standard_agents": ["recherche"],
        }
    )
    assert datei.id == "ord_abcd1234"
    assert datei.datenschutz is Stufe.VERTRAULICH
    assert datei.datenschutz_grund is not None
    assert datei.datenschutz_grund.text == "aus X"
    assert datei.farbe == "blau"
    assert datei.standard_agents == ("recherche",)
    assert datei.warnungen == ()


def test_darstellungsfehler_sind_nur_warnungen() -> None:
    datei = ordner_aus_json(
        {
            "schema": 1,
            "id": "UNGUELTIG",
            "farbe": "neonpink",
            "symbol": "<script>",
            "standard_agents": "recherche",
            "datenschutz_grund": "irgendwas",
        }
    )
    assert datei.id is None
    assert datei.farbe is None and datei.symbol is None and datei.standard_agents is None
    assert datei.datenschutz_grund is None
    assert len(datei.warnungen) == 5


def test_modul_ohne_typ_ist_ein_fehler() -> None:
    with pytest.raises(ValueError, match="typ"):
        modul_aus_json({"schema": 1})
    with pytest.raises(ValueError, match="typ"):
        modul_aus_json({"schema": 1, "typ": "../boese"})


def test_abteilung_wird_gelesen() -> None:
    datei = modul_aus_json(
        {
            "schema": 1,
            "typ": "recherche",
            "abteilung": {"beschreibung": "sucht", "auftragsarten": ["recherche"]},
        }
    )
    assert datei.abteilung is not None
    assert datei.abteilung.auftragsarten == ("recherche",)


def test_neue_id_hat_das_richtige_format() -> None:
    kennung = neue_id("mod")
    assert kennung.startswith("mod_")
    assert modul_aus_json({"schema": 1, "typ": "notizen", "id": kennung}).id == kennung


# -- Lesen von der Platte -----------------------------------------------------


def test_bom_von_windows_editoren_stoert_nicht(workspace: Workspace) -> None:
    datei = workspace.root / "folder.json"
    datei.write_bytes(b"\xef\xbb\xbf" + json.dumps({"schema": 1}).encode("utf-8"))
    assert lies_json(workspace, datei) == {"schema": 1}


@pytest.mark.parametrize(
    ("inhalt", "meldung"),
    [
        (b"{kaputt", "kein gueltiges JSON"),
        (b"[1, 2]", "JSON-Objekt"),
        (b"\xff\xfe\x00", "UTF-8"),
    ],
)
def test_kaputte_dateien(workspace: Workspace, inhalt: bytes, meldung: str) -> None:
    datei = workspace.root / "folder.json"
    datei.write_bytes(inhalt)
    with pytest.raises(ValueError, match=meldung):
        lies_json(workspace, datei)


def test_riesige_datei_wird_nicht_gelesen(workspace: Workspace) -> None:
    datei = workspace.root / "folder.json"
    datei.write_text('{"schema": 1, "x": "' + "a" * MAX_JSON_BYTES + '"}', encoding="utf-8")
    with pytest.raises(ValueError, match="zu gross"):
        lies_json(workspace, datei)


def test_folder_json_als_symlink_nach_draussen(workspace: Workspace, tmp_path: Path) -> None:
    """Niemand soll dem Baum fremde Einstellungen unterschieben koennen."""
    draussen = tmp_path / "fremd.json"
    draussen.write_text('{"schema": 1, "datenschutz": "offen"}', encoding="utf-8")
    link = workspace.root / "folder.json"
    symlink_or_skip(link, draussen)
    with pytest.raises(ValueError, match="Verknuepfung"):
        lies_json(workspace, link)


# -- Schreiben ----------------------------------------------------------------


def test_schreiben_ist_atomar_und_hinterlaesst_nichts(workspace: Workspace) -> None:
    ziel = workspace.root / "folder.json"
    ziel.write_text('{"schema": 1, "alt": true}', encoding="utf-8")
    schreibe_json(workspace, ziel, {"schema": 1, "neu": "ä"})
    assert json.loads(ziel.read_text(encoding="utf-8")) == {"schema": 1, "neu": "ä"}
    assert [p.name for p in workspace.root.iterdir()] == ["folder.json"]


def test_schreiben_ausserhalb_wird_verweigert(workspace: Workspace, tmp_path: Path) -> None:
    with pytest.raises(WorkspaceViolation):
        schreibe_json(workspace, tmp_path / "folder.json", {"schema": 1})
