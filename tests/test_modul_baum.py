"""Der Modulbaum: echte Ordner, Vererbung, und was bei kaputten Dateien passiert."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from conftest import lege_bereich, lege_modul, symlink_or_skip

from jarvis.core.modules import baum as baum_modul
from jarvis.core.modules.baum import Baum, Knoten, lade_baum, wirksame_stufe_unter
from jarvis.core.modules.typen import TypRegister, eingebaute_typen, typ_aus_json
from jarvis.core.safety.datenschutz import Stufe
from jarvis.workspace import Workspace

nur_windows = pytest.mark.skipif(os.name != "nt", reason="Braucht echtes Windows")


@pytest.fixture()
def bereiche(workspace: Workspace) -> Path:
    ordner = workspace.root / "bereiche"
    lege_bereich(ordner, id=None)
    return ordner


def _laden(workspace: Workspace, typen: TypRegister | None = None) -> Baum:
    return lade_baum(workspace, typen or eingebaute_typen())


def _knoten(baum: Baum, pfad: str) -> Knoten:
    for k in baum.alle():
        if k.pfad == pfad:
            return k
    raise AssertionError(f"{pfad} nicht im Baum")


# -- Grundform ---------------------------------------------------------------


def test_leerer_workspace_hat_nur_die_wurzel(workspace: Workspace) -> None:
    baum = _laden(workspace)
    assert baum.wurzel.kinder == []
    assert baum.wurzel.datenschutz is Stufe.OFFEN
    assert not (workspace.root / "bereiche").exists(), "Lesen darf nichts anlegen"


def test_baum_aus_echten_ordnern(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Unternehmen")
    lege_bereich(bereiche / "Unternehmen" / "Firma A")
    lege_bereich(bereiche / "Unternehmen" / "Firma A" / "Kunden")
    lege_modul(bereiche / "Unternehmen" / "Firma A" / "Kunden" / "Liste", typ="aufgaben")
    lege_bereich(bereiche / "Schule")

    baum = _laden(workspace)
    assert [k.name for k in baum.wurzel.kinder] == ["Schule", "Unternehmen"]
    liste = _knoten(baum, "Unternehmen/Firma A/Kunden/Liste")
    assert liste.art == "modul"
    assert liste.typ is not None and liste.typ.id == "aufgaben"
    assert baum.finde(liste.id) is liste


def test_modul_ist_ein_blatt(workspace: Workspace, bereiche: Path) -> None:
    """Was in einem Modul liegt, sind Daten - auch wenn es wie ein Bereich aussieht."""
    lege_modul(bereiche / "Notizen")
    lege_bereich(bereiche / "Notizen" / "sieht aus wie ein Bereich")
    baum = _laden(workspace)
    assert _knoten(baum, "Notizen").kinder == []


def test_ordner_ohne_json_wird_ignoriert_mit_warnung(workspace: Workspace, bereiche: Path) -> None:
    (bereiche / "Einfach so").mkdir()
    baum = _laden(workspace)
    assert baum.wurzel.kinder == []
    assert any("Einfach so" in w for w in baum.wurzel.warnungen)


# -- Vererbung ---------------------------------------------------------------


def test_farbe_symbol_und_agents_werden_vererbt(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Schule", farbe="blau", symbol="buch", standard_agents=["recherche"])
    lege_bereich(bereiche / "Schule" / "Mathe")
    lege_bereich(bereiche / "Schule" / "Kunst", farbe="rot", standard_agents=[])
    lege_modul(bereiche / "Schule" / "Mathe" / "Formeln", typ="notizen")

    baum = _laden(workspace)
    mathe = _knoten(baum, "Schule/Mathe")
    assert (mathe.farbe, mathe.symbol, mathe.standard_agents) == ("blau", "buch", ("recherche",))
    kunst = _knoten(baum, "Schule/Kunst")
    assert kunst.farbe == "rot"
    assert kunst.standard_agents == (), "leere Liste ersetzt die geerbte"
    formeln = _knoten(baum, "Schule/Mathe/Formeln")
    assert formeln.farbe == "blau"
    assert formeln.symbol == "notizblock", "Module zeigen das Symbol ihres Typs"


def test_datenschutz_wird_nach_unten_nie_lockerer(workspace: Workspace, bereiche: Path) -> None:
    """Kern-Schranke: eine lockerere Stufe weiter unten wirkt nicht."""
    lege_bereich(bereiche / "Schule", datenschutz="vertraulich")
    lege_bereich(bereiche / "Schule" / "Mathe", datenschutz="offen")
    lege_modul(bereiche / "Schule" / "Mathe" / "Formeln", datenschutz="offen")

    baum = _laden(workspace)
    mathe = _knoten(baum, "Schule/Mathe")
    assert mathe.datenschutz is Stufe.VERTRAULICH
    assert mathe.datenschutz_herkunft == "geerbt von Schule"
    assert any("wirkt deshalb nicht" in w for w in mathe.warnungen)
    formeln = _knoten(baum, "Schule/Mathe/Formeln")
    assert formeln.datenschutz is Stufe.VERTRAULICH
    assert formeln.datenschutz_herkunft == "geerbt von Schule"


def test_datenschutz_kann_nach_unten_strenger_werden(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Privat")
    lege_bereich(bereiche / "Privat" / "Tagebuch", datenschutz="lokal")
    lege_modul(bereiche / "Privat" / "Tagebuch" / "2026")

    baum = _laden(workspace)
    assert _knoten(baum, "Privat").datenschutz is Stufe.OFFEN
    tagebuch = _knoten(baum, "Privat/Tagebuch")
    assert tagebuch.datenschutz is Stufe.LOKAL
    assert tagebuch.datenschutz_herkunft == "eigene Einstellung"
    assert tagebuch.datenschutz_mindest is Stufe.OFFEN
    modul = _knoten(baum, "Privat/Tagebuch/2026")
    assert modul.datenschutz is Stufe.LOKAL
    assert modul.datenschutz_mindest is Stufe.LOKAL
    assert modul.datenschutz_herkunft == "geerbt von Privat/Tagebuch"


def test_wurzel_kann_strenger_sein(workspace: Workspace) -> None:
    lege_bereich(workspace.root / "bereiche", id=None, datenschutz="vertraulich")
    lege_modul(workspace.root / "bereiche" / "Irgendwas")
    baum = _laden(workspace)
    assert _knoten(baum, "Irgendwas").datenschutz is Stufe.VERTRAULICH


def test_mindeststufe_des_typs(workspace: Workspace, bereiche: Path) -> None:
    strenger_typ = typ_aus_json(
        {
            "schema": 1,
            "id": "tagebuch",
            "version": 1,
            "name": "Tagebuch",
            "beschreibung": "x",
            "symbol": "herz",
            "widgets": [{"widget": "markdown_editor", "platz": "haupt"}],
            "mindest_datenschutz": "vertraulich",
        }
    )
    lege_modul(bereiche / "Mein Tagebuch", typ="tagebuch", datenschutz="offen")
    baum = _laden(workspace, TypRegister([strenger_typ]))
    modul = _knoten(baum, "Mein Tagebuch")
    assert modul.datenschutz is Stufe.VERTRAULICH
    assert modul.datenschutz_herkunft == "Mindeststufe des Typs Tagebuch"


def test_unbekannter_typ_ist_im_zweifel_lokal(workspace: Workspace, bereiche: Path) -> None:
    lege_modul(bereiche / "Zukunft", typ="gibtsnochnicht")
    modul = _knoten(_laden(workspace), "Zukunft")
    assert modul.typ is None
    assert modul.datenschutz is Stufe.LOKAL
    assert any("unbekannt" in w for w in modul.warnungen)


# -- Fehler: im Zweifel lokal ------------------------------------------------


def test_kaputte_folder_json_macht_bereich_und_kinder_lokal(
    workspace: Workspace, bereiche: Path
) -> None:
    kaputt = bereiche / "Kaputt"
    kaputt.mkdir()
    (kaputt / "folder.json").write_text("{nicht json", encoding="utf-8")
    lege_modul(kaputt / "Drin")

    baum = _laden(workspace)
    bereich = _knoten(baum, "Kaputt")
    assert bereich.fehler is not None and "JSON" in bereich.fehler
    assert bereich.datenschutz is Stufe.LOKAL
    kind = _knoten(baum, "Kaputt/Drin")
    assert kind.datenschutz is Stufe.LOKAL, "Kinder eines kaputten Bereichs erben lokal"


def test_kaputte_module_json_bricht_den_baum_nicht(workspace: Workspace, bereiche: Path) -> None:
    (bereiche / "Kaputt").mkdir()
    (bereiche / "Kaputt" / "module.json").write_text("[]", encoding="utf-8")
    lege_modul(bereiche / "Heil")
    baum = _laden(workspace)
    assert _knoten(baum, "Kaputt").fehler is not None
    assert _knoten(baum, "Kaputt").datenschutz is Stufe.LOKAL
    assert _knoten(baum, "Heil").fehler is None


def test_neuere_schema_version_ist_fehler_und_lokal(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Aus der Zukunft", schema=2)
    bereich = _knoten(_laden(workspace), "Aus der Zukunft")
    assert bereich.fehler is not None and "neuer als dieses Jarvis" in bereich.fehler
    assert bereich.datenschutz is Stufe.LOKAL


def test_folder_und_module_json_zugleich(workspace: Workspace, bereiche: Path) -> None:
    ordner = lege_bereich(bereiche / "Beides")
    lege_modul(ordner)
    knoten = _knoten(_laden(workspace), "Beides")
    assert knoten.fehler is not None and "UND" in knoten.fehler
    assert knoten.datenschutz is Stufe.LOKAL


def test_zu_tiefe_verschachtelung(
    workspace: Workspace, bereiche: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(baum_modul, "MAX_TIEFE", 2)
    lege_bereich(bereiche / "a" / "b" / "c")
    lege_bereich(bereiche / "a" / "b")
    lege_bereich(bereiche / "a")
    baum = _laden(workspace)
    b = _knoten(baum, "a/b")
    assert b.kinder == []
    assert any("zu tief" in w for w in b.warnungen)


# -- IDs -----------------------------------------------------------------------


def test_doppelte_id_wird_erkannt(workspace: Workspace, bereiche: Path) -> None:
    """Etwa wenn ein Modul im Explorer kopiert wurde."""
    lege_modul(bereiche / "Original", id="mod_aaaa1111")
    lege_modul(bereiche / "Original - Kopie", id="mod_aaaa1111")
    baum = _laden(workspace)
    original = _knoten(baum, "Original")
    kopie = _knoten(baum, "Original - Kopie")
    assert original.id != kopie.id
    zu_reparieren = baum.zu_reparieren()
    assert len(zu_reparieren) == 1 and zu_reparieren[0].id_vorlaeufig


def test_fehlende_id_wird_vorlaeufig_vergeben(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Ohne id", id=None)
    knoten = _knoten(_laden(workspace), "Ohne id")
    assert knoten.id_vorlaeufig


# -- Verknuepfungen ------------------------------------------------------------


def test_symlink_im_baum_wird_nicht_verfolgt(
    workspace: Workspace, bereiche: Path, tmp_path: Path
) -> None:
    draussen = lege_bereich(tmp_path / "draussen")
    symlink_or_skip(bereiche / "Link", draussen, ordner=True)
    baum = _laden(workspace)
    assert baum.wurzel.kinder == []
    assert any("Verknuepfung" in w for w in baum.wurzel.warnungen)


@nur_windows
def test_junction_im_baum_wird_nicht_verfolgt(
    workspace: Workspace, bereiche: Path, tmp_path: Path
) -> None:
    draussen = lege_bereich(tmp_path / "draussen")
    lege_modul(draussen / "Geheim")
    ergebnis = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(bereiche / "Harmlos"), str(draussen)],
        capture_output=True,
        text=True,
        check=False,
    )
    if ergebnis.returncode != 0:
        pytest.skip(f"mklink /J nicht moeglich: {ergebnis.stdout} {ergebnis.stderr}")
    baum = _laden(workspace)
    assert baum.wurzel.kinder == []
    assert any("Verknuepfung" in w for w in baum.wurzel.warnungen)


# -- Stufe fuer beliebige Pfade --------------------------------------------------


def test_stufe_fuer_dateien_im_workspace(workspace: Workspace, bereiche: Path) -> None:
    lege_bereich(bereiche / "Privat", datenschutz="lokal")
    modul = lege_modul(bereiche / "Privat" / "Tagebuch")
    (modul / "eintraege").mkdir()
    datei = modul / "eintraege" / "heute.md"
    datei.write_text("geheim", encoding="utf-8")
    (workspace.root / "lose.txt").write_text("x", encoding="utf-8")

    baum = _laden(workspace)
    assert wirksame_stufe_unter(baum, datei) is Stufe.LOKAL
    assert wirksame_stufe_unter(baum, workspace.root / "lose.txt") is Stufe.OFFEN
