"""Modultypen - die Bauanleitungen fuer Module.

Ein Typ ist reine Beschreibung, kein Code: welche Widgets, welche
Startordner und -dateien, welche Einstellungen, welche Werkzeuge hoechstens,
welche Mindeststufe. Den Code der Widgets liefert das Widget-Register
(`WIDGETS`) im Kern. Ein neuer Typ ist damit nur eine neue JSON-Datei.

Die eingebauten Typen liegen in `typen/*.json` neben dieser Datei.
Spaeter koennen eigene Typen aus `<Workspace>/.jarvis/typen/` dazukommen -
deshalb wird auch hier alles so streng geprueft, als kaeme es von aussen.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

from ...errors import WorkspaceViolation
from ...workspace import split_relative
from ..safety.datenschutz import Stufe
from ..tools.base import KERN_WERKZEUGE
from .formate import SYSTEM_DATEIEN, pruefe_schema

# Das Widget-Register: alle Widgets, fuer die der Kern (bzw. die Oberflaeche)
# Code mitbringt. Ein Typ, der ein anderes Widget nennt, wird abgelehnt.
WIDGETS = frozenset(
    {
        "notizliste",
        "markdown_editor",
        "quellenliste",
        "aufgabenliste",
        "dateiliste",
        "dateivorschau",
    }
)
PLAETZE = frozenset({"haupt", "seite"})
EINSTELLUNGS_ARTEN = frozenset({"auswahl", "text", "zahl", "schalter"})
MAX_STARTDATEI_BYTES = 64 * 1024

_TYP_ID = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")


@dataclass(frozen=True)
class WidgetPlatz:
    widget: str
    platz: str


@dataclass(frozen=True)
class Startdatei:
    pfad: str
    inhalt: str


@dataclass(frozen=True)
class EinstellungsVorgabe:
    name: str
    art: str
    standard: Any
    werte: tuple[str, ...] = ()


@dataclass(frozen=True)
class TypDefinition:
    id: str
    version: int
    name: str
    beschreibung: str
    symbol: str
    widgets: tuple[WidgetPlatz, ...]
    startordner: tuple[str, ...]
    startdateien: tuple[Startdatei, ...]
    einstellungen: tuple[EinstellungsVorgabe, ...]
    werkzeuge: frozenset[str]
    mindest_datenschutz: Stufe

    def standard_einstellungen(self) -> dict[str, Any]:
        return {e.name: e.standard for e in self.einstellungen}


def _relativer_pfad(pfad: object, typ_id: str) -> str:
    """Start-Pfade muessen harmlos sein: relativ, im Modul, keine Systemdatei."""
    if not isinstance(pfad, str):
        raise ValueError(f"Typ {typ_id}: Pfad muss Text sein, nicht {pfad!r}")
    try:
        teile = split_relative(pfad)
    except WorkspaceViolation as exc:
        raise ValueError(f"Typ {typ_id}: unzulaessiger Pfad {pfad!r} ({exc})") from exc
    if not teile:
        raise ValueError(f"Typ {typ_id}: leerer Pfad")
    if any(t.casefold() in SYSTEM_DATEIEN or t.startswith(".") for t in teile):
        raise ValueError(f"Typ {typ_id}: {pfad!r} ist fuer das System reserviert")
    return "/".join(teile)


def _einstellung(name: str, roh: object, typ_id: str) -> EinstellungsVorgabe:
    if not isinstance(roh, dict) or roh.get("art") not in EINSTELLUNGS_ARTEN:
        raise ValueError(f"Typ {typ_id}: Einstellung {name!r} braucht eine gueltige 'art'")
    art: str = roh["art"]
    standard = roh.get("standard")
    werte: tuple[str, ...] = ()
    if art == "auswahl":
        roh_werte = roh.get("werte")
        if not isinstance(roh_werte, list) or not all(isinstance(w, str) for w in roh_werte):
            raise ValueError(f"Typ {typ_id}: Auswahl {name!r} braucht eine Liste 'werte'")
        werte = tuple(roh_werte)
        if standard not in werte:
            raise ValueError(f"Typ {typ_id}: Standard von {name!r} steht nicht in 'werte'")
    elif art == "schalter" and not isinstance(standard, bool):
        raise ValueError(f"Typ {typ_id}: Schalter {name!r} braucht true/false als Standard")
    elif art == "zahl" and (isinstance(standard, bool) or not isinstance(standard, int | float)):
        raise ValueError(f"Typ {typ_id}: Zahl {name!r} braucht eine Zahl als Standard")
    elif art == "text" and not isinstance(standard, str):
        raise ValueError(f"Typ {typ_id}: Text {name!r} braucht einen Text als Standard")
    return EinstellungsVorgabe(name=name, art=art, standard=standard, werte=werte)


def typ_aus_json(roh: dict[str, Any]) -> TypDefinition:
    """Prueft eine Typ-Definition vollstaendig. Wirft ValueError bei jedem Fehler."""
    pruefe_schema(roh, "Typ-Definition")
    typ_id = roh.get("id")
    if not isinstance(typ_id, str) or not _TYP_ID.match(typ_id):
        raise ValueError(f"Typ-Definition: ungueltige id {typ_id!r}")

    for feld in ("name", "beschreibung", "symbol"):
        if not isinstance(roh.get(feld), str) or not roh[feld]:
            raise ValueError(f"Typ {typ_id}: Feld {feld!r} fehlt")

    version = roh.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValueError(f"Typ {typ_id}: 'version' muss eine ganze Zahl ab 1 sein")

    widgets: list[WidgetPlatz] = []
    for eintrag in roh.get("widgets", []):
        if not isinstance(eintrag, dict):
            raise ValueError(f"Typ {typ_id}: Widget-Eintrag muss ein Objekt sein")
        widget, platz = eintrag.get("widget"), eintrag.get("platz")
        if widget not in WIDGETS:
            raise ValueError(f"Typ {typ_id}: unbekanntes Widget {widget!r}")
        if platz not in PLAETZE:
            raise ValueError(f"Typ {typ_id}: unbekannter Platz {platz!r}")
        widgets.append(WidgetPlatz(widget=widget, platz=platz))
    if not widgets:
        raise ValueError(f"Typ {typ_id}: mindestens ein Widget noetig")

    startordner = tuple(_relativer_pfad(p, typ_id) for p in roh.get("startordner", []))
    startdateien: list[Startdatei] = []
    for eintrag in roh.get("startdateien", []):
        if not isinstance(eintrag, dict) or not isinstance(eintrag.get("inhalt"), str):
            raise ValueError(f"Typ {typ_id}: Startdatei braucht 'pfad' und 'inhalt'")
        if len(eintrag["inhalt"].encode("utf-8")) > MAX_STARTDATEI_BYTES:
            raise ValueError(f"Typ {typ_id}: Startdatei zu gross")
        startdateien.append(
            Startdatei(pfad=_relativer_pfad(eintrag.get("pfad"), typ_id), inhalt=eintrag["inhalt"])
        )

    roh_einstellungen = roh.get("einstellungen", {})
    if not isinstance(roh_einstellungen, dict):
        raise ValueError(f"Typ {typ_id}: 'einstellungen' muss ein Objekt sein")
    einstellungen = tuple(_einstellung(n, v, typ_id) for n, v in roh_einstellungen.items())

    werkzeuge = roh.get("werkzeuge", [])
    if not isinstance(werkzeuge, list) or not all(isinstance(w, str) for w in werkzeuge):
        raise ValueError(f"Typ {typ_id}: 'werkzeuge' muss eine Liste von Namen sein")
    fremde = sorted(set(werkzeuge) - KERN_WERKZEUGE)
    if fremde:
        raise ValueError(
            f"Typ {typ_id}: diese Werkzeuge gibt es im Kern nicht: {', '.join(fremde)}"
        )

    return TypDefinition(
        id=typ_id,
        version=version,
        name=roh["name"],
        beschreibung=roh["beschreibung"],
        symbol=roh["symbol"],
        widgets=tuple(widgets),
        startordner=startordner,
        startdateien=tuple(startdateien),
        einstellungen=einstellungen,
        werkzeuge=frozenset(werkzeuge),
        mindest_datenschutz=Stufe.aus_text(roh.get("mindest_datenschutz", "offen")),
    )


class TypRegister:
    """Alle bekannten Modultypen, nach id."""

    def __init__(self, typen: list[TypDefinition] | None = None) -> None:
        self._typen: dict[str, TypDefinition] = {}
        for typ in typen or []:
            if typ.id in self._typen:
                raise ValueError(f"Modultyp {typ.id!r} ist doppelt")
            self._typen[typ.id] = typ

    def get(self, typ_id: str) -> TypDefinition | None:
        return self._typen.get(typ_id)

    def alle(self) -> list[TypDefinition]:
        return [self._typen[k] for k in sorted(self._typen)]


def eingebaute_typen() -> TypRegister:
    """Laedt die Typen, die mit Jarvis ausgeliefert werden.

    Ein Fehler hier ist ein Programmierfehler (die Dateien gehoeren zum
    Programm) - deshalb bricht er laut ab, statt still einen Typ zu verlieren.
    """
    ordner = resources.files("jarvis.core.modules").joinpath("typen")
    typen = []
    for eintrag in sorted(ordner.iterdir(), key=lambda e: e.name):
        if eintrag.name.endswith(".json"):
            typen.append(typ_aus_json(json.loads(eintrag.read_text(encoding="utf-8"))))
    return TypRegister(typen)
