"""Die Dateiformate folder.json und module.json - lesen, pruefen, schreiben.

Grundsatz: Diese Dateien kann jeder im Explorer oder Editor aendern. Also
wird alles geprueft, und wo etwas nicht stimmt, gilt:

* Sicherheitsrelevantes (Schema-Version, Datenschutzstufe, Modultyp) ist
  falsch  ->  ValueError. Der Baum zeigt den Knoten dann als fehlerhaft an
  und behandelt ihn als "lokal" (im Zweifel die strengste Stufe).
* Nur Darstellung ist falsch (Farbe, Symbol, Beschreibung ...)  ->  der Wert
  wird ignoriert und eine Warnung angehaengt. Deswegen soll niemand einen
  kaputten Baum sehen.

Die Rohdaten (das dict) bleiben beim Schreiben erhalten, damit Felder, die
dieses Jarvis nicht kennt, nicht verloren gehen.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...errors import WorkspaceViolation
from ...workspace import Workspace
from ..safety.datenschutz import Stufe

SCHEMA_AKTUELL = 1
ORDNER_DATEI = "folder.json"
MODUL_DATEI = "module.json"
SYSTEM_DATEIEN = frozenset({ORDNER_DATEI, MODUL_DATEI})

# Groessere Konfigurationsdateien sind kein Versehen mehr, sondern Unfug.
MAX_JSON_BYTES = 64 * 1024

FARBEN = frozenset({"grau", "rot", "orange", "gelb", "gruen", "blau", "lila", "pink"})

_ID_MUSTER = re.compile(r"^[a-z]{3}_[a-z0-9]{4,32}$")
_KENNUNG_MUSTER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")  # Typ-, Symbol-, Agent-Namen


def neue_id(praefix: str) -> str:
    """Eine zufaellige, feste Kennung wie 'mod_4k9x2m7q'."""
    return f"{praefix}_{secrets.token_hex(4)}"


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DatenschutzGrund:
    """Warum eine Stufe festgeschrieben wurde - damit man es spaeter noch weiss."""

    art: str  # "verschoben" | "gesetzt"
    text: str
    datum: str  # ISO-Datum, z. B. "2026-09-26"

    def als_json(self) -> dict[str, str]:
        return {"art": self.art, "text": self.text, "datum": self.datum}


@dataclass(frozen=True)
class Abteilung:
    """Ein Modul, das Auftraege annimmt (umgesetzt in Etappe 6)."""

    beschreibung: str
    auftragsarten: tuple[str, ...]


@dataclass(frozen=True)
class OrdnerDatei:
    """Inhalt einer folder.json. `None` heisst immer: vom Elternbereich erben."""

    id: str | None
    beschreibung: str = ""
    datenschutz: Stufe | None = None
    datenschutz_grund: DatenschutzGrund | None = None
    symbol: str | None = None
    farbe: str | None = None
    standard_agents: tuple[str, ...] | None = None
    layout: Any = None
    warnungen: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModulDatei:
    """Inhalt einer module.json."""

    id: str | None
    typ: str
    typ_version: int = 1
    beschreibung: str = ""
    datenschutz: Stufe | None = None
    datenschutz_grund: DatenschutzGrund | None = None
    symbol: str | None = None
    farbe: str | None = None
    einstellungen: dict[str, Any] = field(default_factory=dict)
    abteilung: Abteilung | None = None
    warnungen: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------


def lies_json(workspace: Workspace, pfad: Path) -> dict[str, Any]:
    """Liest eine Konfigurationsdatei - nur wenn sie echt im Workspace liegt.

    Eine folder.json, die in Wahrheit ein Symlink auf eine Datei ausserhalb
    ist, wird abgelehnt: sonst koennte man dem Baum fremde Einstellungen
    unterschieben.
    """
    if pfad.is_symlink():
        raise ValueError(f"{pfad.name} ist eine Verknuepfung statt einer echten Datei")
    echt = Path(os.path.realpath(pfad))
    if not workspace.contains(echt):
        raise ValueError(f"{pfad.name} zeigt aus dem Workspace heraus")
    groesse = echt.stat().st_size
    if groesse > MAX_JSON_BYTES:
        raise ValueError(f"{pfad.name} ist zu gross ({groesse} Bytes, erlaubt {MAX_JSON_BYTES})")
    try:
        # utf-8-sig: Windows-Editoren schreiben gern ein BOM an den Anfang.
        text = echt.read_text(encoding="utf-8-sig")
        daten = json.loads(text)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{pfad.name} ist keine UTF-8-Textdatei") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{pfad.name} ist kein gueltiges JSON (Zeile {exc.lineno}: {exc.msg})"
        ) from exc
    if not isinstance(daten, dict):
        raise ValueError(f"{pfad.name} muss ein JSON-Objekt {{...}} enthalten")
    return daten


def pruefe_schema(roh: dict[str, Any], dateiname: str) -> None:
    """Schema-Version pruefen - nicht raten (CLAUDE.md 5.2)."""
    schema = roh.get("schema")
    if schema is None:
        raise ValueError(f'{dateiname}: "schema" fehlt - trage "schema": {SCHEMA_AKTUELL} ein')
    if isinstance(schema, bool) or not isinstance(schema, int) or schema < 1:
        raise ValueError(f'{dateiname}: "schema" muss eine ganze Zahl ab 1 sein, nicht {schema!r}')
    if schema > SCHEMA_AKTUELL:
        raise ValueError(
            f"{dateiname} ist neuer als dieses Jarvis (schema {schema}, bekannt bis "
            f"{SCHEMA_AKTUELL}). Bitte Jarvis aktualisieren. Die Datei wurde nicht veraendert."
        )


def _stufe(roh: dict[str, Any], dateiname: str) -> Stufe | None:
    wert = roh.get("datenschutz")
    if wert is None:
        return None
    try:
        return Stufe.aus_text(wert)
    except ValueError as exc:
        raise ValueError(f"{dateiname}: {exc}") from exc


def _id(roh: dict[str, Any], warnungen: list[str]) -> str | None:
    wert = roh.get("id")
    if isinstance(wert, str) and _ID_MUSTER.match(wert):
        return wert
    if wert is not None:
        warnungen.append(f"Ungueltige id {wert!r} - wird neu vergeben")
    return None


def _text(roh: dict[str, Any], schluessel: str, warnungen: list[str], laenge: int = 500) -> str:
    wert = roh.get(schluessel, "")
    if wert is None:
        return ""
    if not isinstance(wert, str) or len(wert) > laenge:
        warnungen.append(f'"{schluessel}" ignoriert: Text mit hoechstens {laenge} Zeichen erwartet')
        return ""
    return wert


def _symbol(roh: dict[str, Any], warnungen: list[str]) -> str | None:
    wert = roh.get("symbol")
    if wert is None:
        return None
    if isinstance(wert, str) and _KENNUNG_MUSTER.match(wert):
        return wert
    warnungen.append(f"Symbol {wert!r} ignoriert")
    return None


def _farbe(roh: dict[str, Any], warnungen: list[str]) -> str | None:
    wert = roh.get("farbe")
    if wert is None:
        return None
    if isinstance(wert, str) and wert in FARBEN:
        return wert
    warnungen.append(f"Farbe {wert!r} ignoriert (erlaubt: {', '.join(sorted(FARBEN))})")
    return None


def _grund(roh: dict[str, Any], warnungen: list[str]) -> DatenschutzGrund | None:
    wert = roh.get("datenschutz_grund")
    if wert is None:
        return None
    if (
        isinstance(wert, dict)
        and all(isinstance(wert.get(k), str) for k in ("art", "text", "datum"))
        and len(wert["text"]) <= 300
    ):
        return DatenschutzGrund(art=wert["art"], text=wert["text"], datum=wert["datum"])
    warnungen.append('"datenschutz_grund" ist unlesbar und wird ignoriert')
    return None


def _kennungen(wert: object) -> tuple[str, ...] | None:
    if isinstance(wert, list) and all(
        isinstance(x, str) and _KENNUNG_MUSTER.match(x) for x in wert
    ):
        return tuple(wert)
    return None


def ordner_aus_json(roh: dict[str, Any]) -> OrdnerDatei:
    """Wandelt eine gelesene folder.json in eine OrdnerDatei."""
    pruefe_schema(roh, ORDNER_DATEI)
    warnungen: list[str] = []
    agents: tuple[str, ...] | None = None
    if roh.get("standard_agents") is not None:
        agents = _kennungen(roh["standard_agents"])
        if agents is None:
            warnungen.append('"standard_agents" ignoriert: Liste von Agent-Namen erwartet')
    return OrdnerDatei(
        id=_id(roh, warnungen),
        beschreibung=_text(roh, "beschreibung", warnungen),
        datenschutz=_stufe(roh, ORDNER_DATEI),
        datenschutz_grund=_grund(roh, warnungen),
        symbol=_symbol(roh, warnungen),
        farbe=_farbe(roh, warnungen),
        standard_agents=agents,
        layout=roh.get("layout"),
        warnungen=tuple(warnungen),
    )


def modul_aus_json(roh: dict[str, Any]) -> ModulDatei:
    """Wandelt eine gelesene module.json in eine ModulDatei."""
    pruefe_schema(roh, MODUL_DATEI)
    warnungen: list[str] = []

    typ = roh.get("typ")
    if not isinstance(typ, str) or not _KENNUNG_MUSTER.match(typ):
        raise ValueError(f'{MODUL_DATEI}: "typ" fehlt oder ist ungueltig ({typ!r})')

    typ_version = roh.get("typ_version", 1)
    if isinstance(typ_version, bool) or not isinstance(typ_version, int) or typ_version < 1:
        warnungen.append('"typ_version" ungueltig - nehme 1')
        typ_version = 1

    einstellungen = roh.get("einstellungen") or {}
    if not isinstance(einstellungen, dict):
        warnungen.append('"einstellungen" ignoriert: JSON-Objekt erwartet')
        einstellungen = {}

    abteilung: Abteilung | None = None
    roh_abteilung = roh.get("abteilung")
    if roh_abteilung is not None:
        arten = (
            _kennungen(roh_abteilung.get("auftragsarten", []))
            if isinstance(roh_abteilung, dict)
            else None
        )
        beschreibung = (
            roh_abteilung.get("beschreibung", "") if isinstance(roh_abteilung, dict) else None
        )
        if arten is None or not isinstance(beschreibung, str):
            warnungen.append('"abteilung" ist unlesbar und wird ignoriert')
        else:
            abteilung = Abteilung(beschreibung=beschreibung[:500], auftragsarten=arten)

    return ModulDatei(
        id=_id(roh, warnungen),
        typ=typ,
        typ_version=typ_version,
        beschreibung=_text(roh, "beschreibung", warnungen),
        datenschutz=_stufe(roh, MODUL_DATEI),
        datenschutz_grund=_grund(roh, warnungen),
        symbol=_symbol(roh, warnungen),
        farbe=_farbe(roh, warnungen),
        einstellungen=dict(einstellungen),
        abteilung=abteilung,
        warnungen=tuple(warnungen),
    )


# ---------------------------------------------------------------------------
# Schreiben
# ---------------------------------------------------------------------------


def schreibe_json(workspace: Workspace, pfad: Path, daten: dict[str, Any]) -> None:
    """Schreibt eine Konfigurationsdatei atomar.

    Erst in eine Nachbardatei, dann in einem Schritt umbenennen: bricht
    mitten drin der Strom weg, bleibt die alte Datei heil statt halb
    geschrieben. Nur der Modul-Dienst im Kern ruft das auf - Werkzeuge
    duerfen diese Dateien nie schreiben (siehe zugriff.py).
    """
    ordner = Path(os.path.realpath(pfad.parent))
    if not workspace.contains(ordner):
        raise WorkspaceViolation(f"Ziel liegt ausserhalb des Workspace: {pfad}")
    if pfad.is_symlink():
        raise WorkspaceViolation(f"{pfad.name} ist eine Verknuepfung - wird nicht ueberschrieben")
    ziel = ordner / pfad.name
    zwischen = ordner / f".{pfad.name}.neu"
    text = json.dumps(daten, ensure_ascii=False, indent=2) + "\n"
    zwischen.write_text(text, encoding="utf-8")
    os.replace(zwischen, ziel)
