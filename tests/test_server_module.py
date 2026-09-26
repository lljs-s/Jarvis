"""REST-Endpunkte des Modulbaums - und dass Fremde nichts veraendern koennen."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from conftest import lege_bereich, lege_modul
from fastapi.testclient import TestClient

from jarvis.config import Settings
from jarvis.server import create_app

TOKEN = "test-token-nur-fuer-tests"  # noqa: S105
KOPF = {"X-Jarvis-Token": TOKEN}


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    return tmp_path / "ws"


@pytest.fixture()
def client(ws: Path) -> TestClient:
    settings = Settings(_env_file=None, JARVIS_WORKSPACE_DIR=str(ws))  # type: ignore[call-arg]
    return TestClient(create_app(settings, token=TOKEN), base_url="http://127.0.0.1:8765")


def _post(client: TestClient, pfad: str, daten: dict[str, Any]) -> Any:
    return client.post(f"/api/modules/{pfad}", json=daten, headers=KOPF)


def _finde(knoten: dict[str, Any], name: str) -> dict[str, Any]:
    if knoten["name"] == name:
        return knoten
    for kind in knoten["kinder"]:
        try:
            return _finde(kind, name)
        except KeyError:
            continue
    raise KeyError(name)


# -- Tuersteher gilt auch hier -------------------------------------------------


def test_aenderung_ohne_token_wird_abgewiesen(client: TestClient, ws: Path) -> None:
    antwort = client.post("/api/modules/ordner", json={"eltern_id": "wurzel", "name": "X"})
    assert antwort.status_code == 401
    assert not (ws / "bereiche").exists()


def test_aenderung_von_fremder_seite_wird_abgewiesen(client: TestClient, ws: Path) -> None:
    """Auch MIT Token: eine fremde Webseite darf keine Ordner anlegen."""
    antwort = client.post(
        "/api/modules/ordner",
        json={"eltern_id": "wurzel", "name": "X"},
        headers={**KOPF, "Origin": "https://boese-seite.example"},
    )
    assert antwort.status_code == 403
    assert not (ws / "bereiche").exists()


# -- Lesen -----------------------------------------------------------------------


def test_leerer_baum(client: TestClient) -> None:
    antwort = client.get("/api/modules", headers=KOPF)
    assert antwort.status_code == 200
    wurzel = antwort.json()
    assert wurzel["id"] == "wurzel" and wurzel["kinder"] == []
    assert wurzel["datenschutz"] == "offen"


def test_typen(client: TestClient) -> None:
    typen = client.get("/api/modules/typen", headers=KOPF).json()
    assert [t["id"] for t in typen] == ["aufgaben", "dateien", "notizen", "recherche"]


def test_keine_rechnerpfade_in_der_antwort(client: TestClient, ws: Path) -> None:
    lege_modul(lege_bereich(ws / "bereiche", id=None) / "Mathe")
    text = client.get("/api/modules", headers=KOPF).text
    assert str(ws) not in text
    assert json.dumps(str(ws))[1:-1] not in text  # auch nicht JSON-maskiert


def test_eigene_stufe_offen_ist_nicht_null(client: TestClient, ws: Path) -> None:
    """Rueckfall-Test: 'offen' ist intern die Zahl 0 und darf nicht als 'nichts' gelten."""
    lege_modul(lege_bereich(ws / "bereiche", id=None) / "M", datenschutz="offen")
    modul = _finde(client.get("/api/modules", headers=KOPF).json(), "M")
    assert modul["datenschutz_eigen"] == "offen"


# -- Aendern ---------------------------------------------------------------------


def test_ordner_und_modul_anlegen(client: TestClient) -> None:
    antwort = _post(client, "ordner", {"eltern_id": "wurzel", "name": "Schule"})
    assert antwort.status_code == 200
    schule_id = antwort.json()["knoten_id"]

    antwort = _post(client, "modul", {"eltern_id": schule_id, "name": "Mathe", "typ": "notizen"})
    assert antwort.status_code == 200
    mathe = _finde(antwort.json()["baum"], "Mathe")
    assert mathe["art"] == "modul" and mathe["typ_name"] == "Notizen"
    assert mathe["pfad"] == "Schule/Mathe"


@pytest.mark.parametrize("name", ["../draussen", "CON", "a/b", "folder.json", "x."])
def test_ungueltiger_name_ergibt_400_mit_klartext(client: TestClient, ws: Path, name: str) -> None:
    antwort = _post(client, "ordner", {"eltern_id": "wurzel", "name": name})
    assert antwort.status_code == 400
    assert antwort.json()["fehler"]
    assert not (ws.parent / "draussen").exists()


def test_unbekannte_stufe_wird_abgelehnt(client: TestClient) -> None:
    antwort = _post(client, "datenschutz", {"id": "wurzel", "stufe": "geheim"})
    assert antwort.status_code == 422


def test_verschieben_und_senken_mit_bestaetigung(client: TestClient, ws: Path) -> None:
    b = lege_bereich(ws / "bereiche", id=None)
    lege_bereich(b / "Unternehmen", id="ord_untern01", datenschutz="vertraulich")
    lege_modul(b / "Unternehmen" / "Kunden", id="mod_kunden01")
    lege_bereich(b / "Privat", id="ord_privat01")

    antwort = _post(client, "verschieben", {"id": "mod_kunden01", "ziel_id": "ord_privat01"})
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["warnungen"]
    kunden = _finde(daten["baum"], "Kunden")
    assert kunden["datenschutz"] == "vertraulich"
    assert kunden["datenschutz_grund"]["text"].startswith(
        "festgeschrieben beim Verschieben aus Unternehmen am "
    )

    frage = _post(client, "datenschutz", {"id": "mod_kunden01", "stufe": None}).json()
    assert frage["braucht_bestaetigung"] is True
    assert frage["betroffene"] == ["Privat/Kunden: vertraulich -> offen"]

    fertig = _post(
        client, "datenschutz", {"id": "mod_kunden01", "stufe": None, "bestaetigt": True}
    ).json()
    assert _finde(fertig["baum"], "Kunden")["datenschutz"] == "offen"


def test_tiefer_als_geerbt_ergibt_400(client: TestClient, ws: Path) -> None:
    b = lege_bereich(ws / "bereiche", id=None)
    lege_bereich(b / "Trading", datenschutz="vertraulich")
    lege_modul(b / "Trading" / "Journal", id="mod_journal1")
    antwort = _post(
        client, "datenschutz", {"id": "mod_journal1", "stufe": "offen", "bestaetigt": True}
    )
    assert antwort.status_code == 400
    assert "Tiefer als 'vertraulich'" in antwort.json()["fehler"]
