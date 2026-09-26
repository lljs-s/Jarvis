"""Demo im Repo und Erstbefuellung des echten Workspace."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from jarvis.config import PROJECT_ROOT, Settings
from jarvis.core.modules.baum import Baum, Knoten, lade_baum
from jarvis.core.modules.demo import OEFFENTLICH, erstbefuellung
from jarvis.core.modules.typen import eingebaute_typen
from jarvis.core.safety.datenschutz import Stufe
from jarvis.server.start import richte_workspace_ein
from jarvis.workspace import Workspace

HEUTE = date(2026, 9, 26)


def _k(baum: Baum, pfad: str) -> Knoten:
    for k in baum.alle():
        if k.pfad == pfad:
            return k
    raise AssertionError(f"{pfad} nicht im Baum")


def _pruefe_beispiel(baum: Baum) -> None:
    """Die Vererbung, die das Beispiel zeigen soll."""
    beispiel = _k(baum, "Beispiel")
    assert (beispiel.farbe, beispiel.symbol, beispiel.datenschutz) == (
        "gruen",
        "stern",
        Stufe.OFFEN,
    )

    oeffentlich = _k(baum, f"Beispiel/{OEFFENTLICH}")
    assert (oeffentlich.farbe, oeffentlich.symbol) == ("gruen", "stern")
    links = _k(baum, f"Beispiel/{OEFFENTLICH}/Linksammlung")
    assert links.typ is not None and links.typ.id == "recherche"
    assert (links.farbe, links.datenschutz) == ("gruen", Stufe.OFFEN)

    privat = _k(baum, "Beispiel/Privat")
    assert (privat.farbe, privat.datenschutz) == ("rot", Stufe.VERTRAULICH)
    tagebuch = _k(baum, "Beispiel/Privat/Tagebuch")
    assert tagebuch.typ is not None and tagebuch.typ.id == "notizen"
    assert (tagebuch.farbe, tagebuch.datenschutz) == ("rot", Stufe.VERTRAULICH)
    assert tagebuch.datenschutz_herkunft == "geerbt von Beispiel/Privat"


def test_demo_im_repo_ist_fehlerfrei() -> None:
    """test-workspace/bereiche: keine Fehler, keine Warnungen, Vererbung sichtbar."""
    workspace = Workspace.open(PROJECT_ROOT / "test-workspace")
    baum = lade_baum(workspace, eingebaute_typen())
    for knoten in baum.alle():
        assert knoten.fehler is None, knoten.pfad
        assert knoten.warnungen == [], (knoten.pfad, knoten.warnungen)
        assert not knoten.id_vorlaeufig, knoten.pfad
    _pruefe_beispiel(baum)


def test_erstbefuellung(workspace: Workspace) -> None:
    angelegt = erstbefuellung(workspace, eingebaute_typen(), HEUTE)
    assert angelegt == ["Beispiel", "Unternehmen", "Trading"]

    baum = lade_baum(workspace, eingebaute_typen())
    assert baum.wurzel.datenschutz is Stufe.OFFEN
    _pruefe_beispiel(baum)
    for name in ("Unternehmen", "Trading"):
        bereich = _k(baum, name)
        assert bereich.datenschutz is Stufe.VERTRAULICH
        assert bereich.grund is not None
        assert bereich.grund.text == "bei der Einrichtung festgelegt am 26.09.2026"
    assert all(k.fehler is None and not k.warnungen for k in baum.alle())


def test_erstbefuellung_nur_einmal(workspace: Workspace) -> None:
    """Geloeschte Bereiche kommen nicht ungefragt zurueck."""
    erstbefuellung(workspace, eingebaute_typen(), HEUTE)
    beispiel = workspace.root / "bereiche" / "Beispiel"
    for datei in sorted(beispiel.rglob("*"), reverse=True):
        datei.unlink() if datei.is_file() else datei.rmdir()
    beispiel.rmdir()

    assert erstbefuellung(workspace, eingebaute_typen(), HEUTE) == []
    assert not beispiel.exists()


def test_vorhandene_bereiche_bleiben_unberuehrt(workspace: Workspace) -> None:
    (workspace.root / "bereiche").mkdir()
    assert erstbefuellung(workspace, eingebaute_typen(), HEUTE) == []
    assert list((workspace.root / "bereiche").iterdir()) == []


def test_serverstart_richtet_den_workspace_ein(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, JARVIS_WORKSPACE_DIR=str(tmp_path / "ws"))  # type: ignore[call-arg]
    assert richte_workspace_ein(settings) == ["Beispiel", "Unternehmen", "Trading"]
    wurzel = json.loads((tmp_path / "ws" / "bereiche" / "folder.json").read_text("utf-8"))
    assert wurzel["datenschutz"] == "offen"
    assert richte_workspace_ein(settings) == []
