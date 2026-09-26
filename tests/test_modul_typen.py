"""Modultypen: eingebaute Typen und die Grenzen, die jeder Typ einhalten muss."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from jarvis.core.modules.typen import eingebaute_typen, typ_aus_json
from jarvis.core.safety.datenschutz import Stufe
from jarvis.core.tools.base import KERN_WERKZEUGE
from jarvis.core.tools.files import default_tools
from jarvis.workspace import Workspace

GUELTIG: dict[str, Any] = {
    "schema": 1,
    "id": "test",
    "version": 1,
    "name": "Test",
    "beschreibung": "Ein Testtyp",
    "symbol": "stern",
    "widgets": [{"widget": "notizliste", "platz": "seite"}],
    "startordner": ["daten"],
    "startdateien": [{"pfad": "daten/a.md", "inhalt": "# A\n"}],
    "einstellungen": {"sortierung": {"art": "auswahl", "werte": ["a", "b"], "standard": "a"}},
    "werkzeuge": ["read_file"],
    "mindest_datenschutz": "vertraulich",
}


def _mit(**aenderungen: Any) -> dict[str, Any]:
    roh = copy.deepcopy(GUELTIG)
    roh.update(aenderungen)
    return roh


def test_die_vier_starttypen_sind_da() -> None:
    typen = eingebaute_typen()
    assert [t.id for t in typen.alle()] == ["aufgaben", "dateien", "notizen", "recherche"]
    for typ in typen.alle():
        assert typ.mindest_datenschutz is Stufe.OFFEN
        assert typ.werkzeuge <= KERN_WERKZEUGE


def test_gueltiger_typ() -> None:
    typ = typ_aus_json(GUELTIG)
    assert typ.mindest_datenschutz is Stufe.VERTRAULICH
    assert typ.standard_einstellungen() == {"sortierung": "a"}


def test_kern_werkzeuge_passen_zu_den_gebauten(workspace: Workspace) -> None:
    """Die Liste in tools/base.py darf nicht von der Wirklichkeit abweichen."""
    assert {t.name for t in default_tools(workspace)} == KERN_WERKZEUGE


def test_typ_kann_kein_fremdes_werkzeug_anfordern() -> None:
    """Etwa fuer ein Trading-Journal: Orders ausloesen gibt es nicht."""
    with pytest.raises(ValueError, match="gibt es im Kern nicht"):
        typ_aus_json(_mit(werkzeuge=["read_file", "broker_order"]))


def test_unbekanntes_widget_wird_abgelehnt() -> None:
    with pytest.raises(ValueError, match="Widget"):
        typ_aus_json(_mit(widgets=[{"widget": "fernsteuerung", "platz": "haupt"}]))


@pytest.mark.parametrize(
    "pfad",
    ["../draussen.md", "C:\\Windows\\x.md", "module.json", "unter/FOLDER.JSON", ".jarvis/x", ""],
)
def test_startdateien_bleiben_im_modul(pfad: str) -> None:
    with pytest.raises(ValueError):
        typ_aus_json(_mit(startdateien=[{"pfad": pfad, "inhalt": "x"}]))


def test_startordner_bleiben_im_modul() -> None:
    with pytest.raises(ValueError):
        typ_aus_json(_mit(startordner=["../../weg"]))


def test_hoehere_schema_version_beim_typ() -> None:
    with pytest.raises(ValueError, match="neuer als"):
        typ_aus_json(_mit(schema=2))


def test_auswahl_standard_muss_passen() -> None:
    with pytest.raises(ValueError, match="Standard"):
        typ_aus_json(_mit(einstellungen={"s": {"art": "auswahl", "werte": ["a"], "standard": "z"}}))
