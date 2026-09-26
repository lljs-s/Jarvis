"""Der Modul-Dienst: Anlegen, Umbenennen, Verschieben und Datenschutz setzen."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from conftest import lege_bereich, lege_modul

from jarvis.core.modules.baum import WURZEL_ID, Baum, Knoten
from jarvis.core.modules.dienst import ModulDienst, pruefe_name
from jarvis.core.modules.typen import eingebaute_typen
from jarvis.core.safety.datenschutz import Stufe
from jarvis.errors import ModulFehler
from jarvis.workspace import Workspace

HEUTE = date(2026, 9, 26)


@pytest.fixture()
def dienst(workspace: Workspace) -> ModulDienst:
    return ModulDienst(workspace, eingebaute_typen(), heute=lambda: HEUTE)


@pytest.fixture()
def bereiche(workspace: Workspace) -> Path:
    return lege_bereich(workspace.root / "bereiche", id=None, datenschutz="offen")


def _k(baum: Baum, pfad: str) -> Knoten:
    for k in baum.alle():
        if k.pfad == pfad:
            return k
    raise AssertionError(f"{pfad} nicht im Baum")


def _json(ordner: Path, name: str = "module.json") -> dict[str, Any]:
    daten: dict[str, Any] = json.loads((ordner / name).read_text(encoding="utf-8"))
    return daten


# -- Namen -------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "",
        "a/b",
        "a\\b",
        "..",
        ".",
        ".versteckt",
        "CON",
        "nul.txt",
        "ordner ",
        " ordner",
        "bericht.",
        "a:b",
        "wer?",
        "folder.json",
        "MODULE.JSON",
        "x" * 81,
        "C:\\Windows",
    ],
)
def test_ungueltige_namen(name: str) -> None:
    with pytest.raises(ModulFehler):
        pruefe_name(name)


@pytest.mark.parametrize("name", ["Schule", "Firma A", "Mathe 2026", "Übungen (alt)", "a.b"])
def test_gueltige_namen(name: str) -> None:
    assert pruefe_name(name) == name


# -- Anlegen -----------------------------------------------------------------


def test_erster_ordner_legt_die_wurzel_an(dienst: ModulDienst, workspace: Workspace) -> None:
    ergebnis = dienst.ordner_anlegen(WURZEL_ID, "Schule")
    wurzel = workspace.root / "bereiche"
    assert _json(wurzel, "folder.json")["datenschutz"] == "offen"
    assert _json(wurzel / "Schule", "folder.json")["id"] == ergebnis.knoten_id
    assert _k(dienst.baum(), "Schule").datenschutz is Stufe.OFFEN


def test_neuer_ordner_erbt(dienst: ModulDienst, bereiche: Path) -> None:
    lege_bereich(bereiche / "Unternehmen", id="ord_unter001", datenschutz="vertraulich")
    dienst.ordner_anlegen("ord_unter001", "Firma A")
    firma = _k(dienst.baum(), "Unternehmen/Firma A")
    assert firma.datenschutz is Stufe.VERTRAULICH
    assert "datenschutz" not in _json(bereiche / "Unternehmen" / "Firma A", "folder.json")


def test_modul_anlegen_mit_startdateien(dienst: ModulDienst, bereiche: Path) -> None:
    lege_bereich(bereiche / "Schule", id="ord_schule01")
    ergebnis = dienst.modul_anlegen("ord_schule01", "Referat", "recherche")
    ordner = bereiche / "Schule" / "Referat"
    daten = _json(ordner)
    assert daten["id"] == ergebnis.knoten_id
    assert daten["typ"] == "recherche"
    assert daten["einstellungen"] == {"zitierstil": "kurz"}
    assert (ordner / "frage.md").is_file()
    assert (ordner / "quellen").is_dir() and (ordner / "ergebnisse").is_dir()


def test_unbekannter_typ(dienst: ModulDienst, bereiche: Path) -> None:
    with pytest.raises(ModulFehler, match="gibt es nicht"):
        dienst.modul_anlegen(WURZEL_ID, "X", "trading_order")


def test_nichts_in_ein_modul_legen(dienst: ModulDienst, bereiche: Path) -> None:
    lege_modul(bereiche / "Notizen", id="mod_notiz001")
    with pytest.raises(ModulFehler, match="nur in einen Bereich"):
        dienst.ordner_anlegen("mod_notiz001", "Unterordner")


def test_name_schon_belegt_auch_bei_anderer_schreibweise(
    dienst: ModulDienst, bereiche: Path
) -> None:
    lege_bereich(bereiche / "Schule")
    with pytest.raises(ModulFehler, match="schon"):
        dienst.ordner_anlegen(WURZEL_ID, "Schule")
    with pytest.raises(ModulFehler, match="schon"):
        dienst.modul_anlegen(WURZEL_ID, "SCHULE", "notizen")


def test_unbekannte_id(dienst: ModulDienst, bereiche: Path) -> None:
    with pytest.raises(ModulFehler, match="gibt es nicht mehr"):
        dienst.ordner_anlegen("ord_gibtsnicht", "X")


# -- IDs -----------------------------------------------------------------------


def test_doppelte_id_wird_repariert(dienst: ModulDienst, bereiche: Path) -> None:
    lege_modul(bereiche / "A", id="mod_aaaa1111")
    lege_modul(bereiche / "B", id="mod_aaaa1111")
    baum = dienst.baum()
    assert _k(baum, "A").id == "mod_aaaa1111"
    neue = _json(bereiche / "B")["id"]
    assert neue != "mod_aaaa1111" and neue.startswith("mod_")
    assert not baum.zu_reparieren()


def test_id_bleibt_bei_umbenennen_und_verschieben(dienst: ModulDienst, bereiche: Path) -> None:
    lege_bereich(bereiche / "Ziel", id="ord_ziel0001")
    lege_modul(bereiche / "Mathe", id="mod_mathe001")
    dienst.umbenennen("mod_mathe001", "Mathematik")
    dienst.verschieben("mod_mathe001", "ord_ziel0001")
    assert _k(dienst.baum(), "Ziel/Mathematik").id == "mod_mathe001"


# -- Umbenennen ----------------------------------------------------------------


def test_umbenennen(dienst: ModulDienst, bereiche: Path) -> None:
    lege_bereich(bereiche / "Schul", id="ord_schule01")
    dienst.umbenennen("ord_schule01", "Schule")
    assert (bereiche / "Schule" / "folder.json").is_file()
    assert not (bereiche / "Schul").exists()


def test_nur_gross_klein_aendern(dienst: ModulDienst, bereiche: Path) -> None:
    """Unter Windows ist 'mathe' und 'Mathe' dieselbe Stelle - das muss trotzdem gehen."""
    lege_modul(bereiche / "mathe", id="mod_mathe001")
    dienst.umbenennen("mod_mathe001", "Mathe")
    assert [p.name for p in bereiche.iterdir() if p.is_dir()] == ["Mathe"]


def test_umbenennen_auf_belegten_namen(dienst: ModulDienst, bereiche: Path) -> None:
    lege_modul(bereiche / "A", id="mod_aaaa0001")
    lege_modul(bereiche / "B")
    with pytest.raises(ModulFehler, match="schon"):
        dienst.umbenennen("mod_aaaa0001", "b")


def test_wurzel_nicht_umbenennen(dienst: ModulDienst, bereiche: Path) -> None:
    with pytest.raises(ModulFehler, match="Wurzel"):
        dienst.umbenennen(WURZEL_ID, "Neu")


# -- Verschieben ---------------------------------------------------------------


@pytest.fixture()
def unternehmen(bereiche: Path) -> Path:
    """Unternehmen (vertraulich) mit Modul Kunden, daneben Privat (offen) und Tresor (lokal)."""
    lege_bereich(bereiche / "Unternehmen", id="ord_untern01", datenschutz="vertraulich")
    lege_modul(bereiche / "Unternehmen" / "Kunden", id="mod_kunden01")
    lege_bereich(bereiche / "Privat", id="ord_privat01")
    lege_bereich(bereiche / "Tresor", id="ord_tresor01", datenschutz="lokal")
    return bereiche


def test_in_strengeren_bereich_wird_automatisch_strenger(
    dienst: ModulDienst, unternehmen: Path
) -> None:
    ergebnis = dienst.verschieben("mod_kunden01", "ord_tresor01")
    kunden = _k(dienst.baum(), "Tresor/Kunden")
    assert kunden.datenschutz is Stufe.LOKAL
    assert "datenschutz" not in _json(unternehmen / "Tresor" / "Kunden"), "nichts festgeschrieben"
    assert ergebnis.hinweise and not ergebnis.warnungen


def test_in_lockereren_bereich_behaelt_die_stufe_mit_grund(
    dienst: ModulDienst, unternehmen: Path
) -> None:
    """Kern-Schranke: Verschieben macht nie etwas lockerer."""
    ergebnis = dienst.verschieben("mod_kunden01", "ord_privat01")
    kunden = _k(dienst.baum(), "Privat/Kunden")
    assert kunden.datenschutz is Stufe.VERTRAULICH
    assert kunden.grund is not None
    assert kunden.grund.text == "festgeschrieben beim Verschieben aus Unternehmen am 26.09.2026"
    assert kunden.grund.art == "verschoben" and kunden.grund.datum == "2026-09-26"
    assert ergebnis.warnungen and "behaelt" in ergebnis.warnungen[0]


def test_bereich_mit_inhalt_verschieben_behaelt_alle_stufen(
    dienst: ModulDienst, bereiche: Path
) -> None:
    lege_bereich(bereiche / "Firma", id="ord_firma001", datenschutz="vertraulich")
    lege_bereich(bereiche / "Firma" / "Geheim", datenschutz="lokal")
    lege_modul(bereiche / "Firma" / "Geheim" / "Vertraege")
    lege_modul(bereiche / "Firma" / "Kunden")
    lege_bereich(bereiche / "Archiv", id="ord_archiv01")

    vorher = {k.name: k.datenschutz for k in dienst.baum().alle()}
    dienst.verschieben("ord_firma001", "ord_archiv01")
    nachher = {k.name: k.datenschutz for k in dienst.baum().alle()}
    for name in ("Firma", "Geheim", "Vertraege", "Kunden"):
        assert nachher[name] == vorher[name], name


def test_eigene_stufe_und_grund_bleiben_beim_verschieben(
    dienst: ModulDienst, unternehmen: Path
) -> None:
    lege_modul(
        unternehmen / "Unternehmen" / "Bilanz",
        id="mod_bilanz01",
        datenschutz="lokal",
        datenschutz_grund={"art": "gesetzt", "text": "von dir gesetzt", "datum": "2026-01-01"},
    )
    dienst.verschieben("mod_bilanz01", "ord_privat01")
    daten = _json(unternehmen / "Privat" / "Bilanz")
    assert daten["datenschutz"] == "lokal"
    assert daten["datenschutz_grund"]["text"] == "von dir gesetzt"


def test_nicht_in_sich_selbst_verschieben(dienst: ModulDienst, bereiche: Path) -> None:
    lege_bereich(bereiche / "A", id="ord_aaaa0001")
    lege_bereich(bereiche / "A" / "B", id="ord_bbbb0001")
    with pytest.raises(ModulFehler, match="in sich selbst"):
        dienst.verschieben("ord_aaaa0001", "ord_aaaa0001")
    with pytest.raises(ModulFehler, match="in sich selbst"):
        dienst.verschieben("ord_aaaa0001", "ord_bbbb0001")


def test_nicht_in_ein_modul_verschieben(dienst: ModulDienst, unternehmen: Path) -> None:
    lege_modul(unternehmen / "Notizen", id="mod_notiz001")
    with pytest.raises(ModulFehler, match="nur in einen Bereich"):
        dienst.verschieben("mod_kunden01", "mod_notiz001")


def test_verschieben_auf_belegten_namen(dienst: ModulDienst, unternehmen: Path) -> None:
    lege_modul(unternehmen / "Privat" / "kunden")
    with pytest.raises(ModulFehler, match="schon"):
        dienst.verschieben("mod_kunden01", "ord_privat01")
    assert (unternehmen / "Unternehmen" / "Kunden").is_dir(), "nichts wurde bewegt"


# -- Datenschutz setzen ----------------------------------------------------------


def test_strenger_setzen_geht_immer(dienst: ModulDienst, unternehmen: Path) -> None:
    dienst.datenschutz_setzen("mod_kunden01", Stufe.LOKAL)
    daten = _json(unternehmen / "Unternehmen" / "Kunden")
    assert daten["datenschutz"] == "lokal"
    assert daten["datenschutz_grund"]["text"] == "von dir gesetzt am 26.09.2026"


def test_unter_die_geerbte_stufe_geht_nicht(dienst: ModulDienst, unternehmen: Path) -> None:
    """Kern-Schranke, nicht nur Oberflaeche."""
    with pytest.raises(ModulFehler, match="Tiefer als 'vertraulich'"):
        dienst.datenschutz_setzen("mod_kunden01", Stufe.OFFEN, bestaetigt=True)
    assert "datenschutz" not in _json(unternehmen / "Unternehmen" / "Kunden")


def test_senken_braucht_bestaetigung(dienst: ModulDienst, unternehmen: Path) -> None:
    dienst.verschieben("mod_kunden01", "ord_privat01")  # jetzt festgeschrieben vertraulich
    ordner = unternehmen / "Privat" / "Kunden"

    frage = dienst.datenschutz_setzen("mod_kunden01", None)
    assert frage.braucht_bestaetigung
    assert frage.betroffene == ["Privat/Kunden: vertraulich -> offen"]
    assert _json(ordner)["datenschutz"] == "vertraulich", "ohne Ja keine Aenderung"

    dienst.datenschutz_setzen("mod_kunden01", None, bestaetigt=True)
    daten = _json(ordner)
    assert "datenschutz" not in daten and "datenschutz_grund" not in daten
    assert _k(dienst.baum(), "Privat/Kunden").datenschutz is Stufe.OFFEN


def test_senken_eines_bereichs_nennt_alle_betroffenen(
    dienst: ModulDienst, unternehmen: Path
) -> None:
    frage = dienst.datenschutz_setzen("ord_untern01", Stufe.OFFEN)
    assert frage.braucht_bestaetigung
    assert frage.betroffene == [
        "Unternehmen: vertraulich -> offen",
        "Unternehmen/Kunden: vertraulich -> offen",
    ]


def test_unbekannte_felder_bleiben_erhalten(dienst: ModulDienst, bereiche: Path) -> None:
    lege_modul(bereiche / "M", id="mod_mmmm0001", zukunft={"x": 1})
    dienst.datenschutz_setzen("mod_mmmm0001", Stufe.VERTRAULICH)
    assert _json(bereiche / "M")["zukunft"] == {"x": 1}


# -- Fehlerhafte Eintraege ---------------------------------------------------------


def test_fehlerhafte_eintraege_werden_nicht_angefasst(dienst: ModulDienst, bereiche: Path) -> None:
    """Eine Datei aus einer neueren Jarvis-Version wird nie ueberschrieben."""
    ordner = lege_modul(bereiche / "Neu", schema=2)
    vorher = (ordner / "module.json").read_bytes()
    kaputt = _k(dienst.baum(), "Neu")
    with pytest.raises(ModulFehler, match="fehlerhaft"):
        dienst.datenschutz_setzen(kaputt.id, Stufe.LOKAL)
    with pytest.raises(ModulFehler, match="fehlerhaft"):
        dienst.umbenennen(kaputt.id, "Anders")
    assert (ordner / "module.json").read_bytes() == vorher


def test_nichts_in_fehlerhaften_bereich_legen(dienst: ModulDienst, bereiche: Path) -> None:
    (bereiche / "Kaputt").mkdir()
    (bereiche / "Kaputt" / "folder.json").write_text("{", encoding="utf-8")
    kaputt = _k(dienst.baum(), "Kaputt")
    with pytest.raises(ModulFehler, match="fehlerhaft"):
        dienst.ordner_anlegen(kaputt.id, "Neu")
