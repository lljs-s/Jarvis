"""Der Modulbaum - gelesen aus den echten Ordnern unter <Workspace>/bereiche/.

Nur lesen, nie schreiben: Aenderungen macht der Modul-Dienst (dienst.py).

Was ein Ordner ist, entscheidet sein Inhalt:
    folder.json          ->  Bereich (kann Bereiche und Module enthalten)
    module.json          ->  Modul   (ein Blatt; alles darin sind Daten)
    beides               ->  Fehler, zaehlt als "lokal"
    nichts davon         ->  wird ignoriert (mit Warnung am Elternbereich)

Beim Lesen wird gleich vererbt (CLAUDE.md 5.1):
    Symbol, Farbe, Standard-Agents  ->  der naechste gesetzte Wert gewinnt
    Datenschutz                     ->  immer das Strengste auf dem Weg
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ...errors import ModulFehler, WorkspaceViolation
from ...workspace import Workspace, split_relative
from ..safety.datenschutz import Stufe
from .formate import (
    MODUL_DATEI,
    ORDNER_DATEI,
    DatenschutzGrund,
    ModulDatei,
    OrdnerDatei,
    lies_json,
    modul_aus_json,
    ordner_aus_json,
)
from .typen import TypDefinition, TypRegister

BEREICHE_ORDNER = "bereiche"
SYSTEM_ORDNER = ".jarvis"
WURZEL_ID = "wurzel"

# Sicherheitsbremsen gegen absurde Ordnerstrukturen (oder Schleifen).
MAX_TIEFE = 32
MAX_KNOTEN = 5000

STANDARD_SYMBOL_BEREICH = "ordner"
STANDARD_SYMBOL_MODUL = "modul"
STANDARD_FARBE = "grau"

Art = Literal["bereich", "modul"]


@dataclass(eq=False)
class Knoten:
    """Ein Bereich oder Modul - mit den WIRKSAMEN (vererbten) Werten."""

    id: str
    art: Art
    name: str
    ordner: Path
    pfad: str  # relativ zu bereiche/, mit "/" - "" ist die Wurzel
    eltern: Knoten | None = field(repr=False)

    ordner_datei: OrdnerDatei | None = None
    modul_datei: ModulDatei | None = None
    typ: TypDefinition | None = None
    fehler: str | None = None
    warnungen: list[str] = field(default_factory=list)

    datenschutz: Stufe = Stufe.LOKAL
    # Was von oben (und vom Typ) kommt - tiefer darf die eigene Stufe nicht.
    datenschutz_mindest: Stufe = Stufe.LOKAL
    datenschutz_herkunft: str = ""
    symbol: str = STANDARD_SYMBOL_BEREICH
    farbe: str = STANDARD_FARBE
    standard_agents: tuple[str, ...] = ()

    kinder: list[Knoten] = field(default_factory=list)
    # True: die id fehlt oder ist doppelt - der Dienst vergibt eine neue.
    id_vorlaeufig: bool = False

    @property
    def ist_wurzel(self) -> bool:
        return self.eltern is None

    @property
    def eigene_stufe(self) -> Stufe | None:
        datei = self.ordner_datei or self.modul_datei
        return datei.datenschutz if datei else None

    @property
    def grund(self) -> DatenschutzGrund | None:
        datei = self.ordner_datei or self.modul_datei
        return datei.datenschutz_grund if datei else None

    @property
    def anzeige_pfad(self) -> str:
        return self.pfad or "Wurzel"

    def nachfahren(self) -> Iterator[Knoten]:
        for kind in self.kinder:
            yield kind
            yield from kind.nachfahren()

    def ist_vorfahr_von(self, anderer: Knoten) -> bool:
        k = anderer.eltern
        while k is not None:
            if k is self:
                return True
            k = k.eltern
        return False


@dataclass
class Baum:
    """Der ganze Baum plus Nachschlagetabelle nach id."""

    wurzel: Knoten
    nach_id: dict[str, Knoten] = field(default_factory=dict)
    anzahl: int = 0

    def finde(self, knoten_id: str) -> Knoten:
        try:
            return self.nach_id[knoten_id]
        except KeyError:
            raise ModulFehler(
                "Diesen Eintrag gibt es nicht mehr. Bitte den Baum neu laden."
            ) from None

    def alle(self) -> Iterator[Knoten]:
        yield self.wurzel
        yield from self.wurzel.nachfahren()

    def zu_reparieren(self) -> list[Knoten]:
        return [k for k in self.alle() if k.id_vorlaeufig]

    def _registriere(self, knoten: Knoten) -> None:
        self.anzahl += 1
        if knoten.id in self.nach_id:
            # Doppelte id (z. B. Ordner im Explorer kopiert): der zweite
            # bekommt eine vorlaeufige id, der Dienst vergibt dann eine neue.
            knoten.warnungen.append(f"Die id {knoten.id} gab es doppelt - wird neu vergeben")
            knoten.id = _vorlaeufige_id("dop", knoten.pfad)
            knoten.id_vorlaeufig = True
        self.nach_id[knoten.id] = knoten


def _vorlaeufige_id(praefix: str, pfad: str) -> str:
    """Stabil fuer denselben Pfad, damit die Oberflaeche den Knoten findet."""
    kurz = hashlib.sha256(pfad.casefold().encode("utf-8")).hexdigest()[:12]
    return f"{praefix}_{kurz}"


def ist_verknuepfung(pfad: Path) -> bool:
    """Symlink oder Junction? Beides wird im Baum nicht verfolgt.

    Eine Junction erkennt man daran, dass der aufgeloeste Pfad woanders
    hinfuehrt als der Pfad selbst.
    """
    if pfad.is_symlink():
        return True
    return os.path.normcase(os.path.realpath(pfad)) != os.path.normcase(os.path.abspath(pfad))


# ---------------------------------------------------------------------------
# Laden
# ---------------------------------------------------------------------------


def lade_baum(workspace: Workspace, typen: TypRegister) -> Baum:
    """Liest den ganzen Baum. Wirft nie wegen kaputter Dateien - die werden markiert."""
    ordner = workspace.resolve(BEREICHE_ORDNER)
    wurzel = Knoten(id=WURZEL_ID, art="bereich", name="Wurzel", ordner=ordner, pfad="", eltern=None)
    wurzel.symbol, wurzel.farbe = STANDARD_SYMBOL_BEREICH, STANDARD_FARBE
    wurzel.datenschutz = wurzel.datenschutz_mindest = Stufe.OFFEN
    wurzel.datenschutz_herkunft = "Standard der Wurzel"

    baum = Baum(wurzel=wurzel)
    baum.nach_id[WURZEL_ID] = wurzel
    baum.anzahl = 1
    if not ordner.is_dir():
        return baum

    datei_pfad = ordner / ORDNER_DATEI
    if os.path.lexists(datei_pfad):
        try:
            datei = ordner_aus_json(lies_json(workspace, datei_pfad))
        except (ValueError, OSError) as exc:
            _als_fehler(wurzel, str(exc))
        else:
            wurzel.ordner_datei = datei
            wurzel.warnungen.extend(datei.warnungen)
            if datei.datenschutz is not None:
                wurzel.datenschutz = datei.datenschutz
                wurzel.datenschutz_herkunft = "Einstellung der Wurzel"
            wurzel.symbol = datei.symbol or wurzel.symbol
            wurzel.farbe = datei.farbe or wurzel.farbe
            wurzel.standard_agents = datei.standard_agents or ()

    _lade_kinder(workspace, typen, baum, wurzel, tiefe=1)
    return baum


def _als_fehler(knoten: Knoten, grund: str) -> None:
    """Im Zweifel die strengste Stufe - und der Nutzer erfaehrt, warum."""
    knoten.fehler = grund
    knoten.datenschutz = Stufe.LOKAL
    knoten.datenschutz_mindest = Stufe.LOKAL
    knoten.datenschutz_herkunft = "Fehler in der Datei - im Zweifel lokal"


def _weitergabe(eltern: Knoten) -> str:
    """Wie die Herkunft der Stufe bei den Kindern heisst."""
    if eltern.fehler:
        return f"geerbt vom fehlerhaften Bereich {eltern.anzeige_pfad} - im Zweifel lokal"
    if eltern.datenschutz_herkunft.startswith("geerbt") or eltern.datenschutz_herkunft.startswith(
        "Standard"
    ):
        return eltern.datenschutz_herkunft
    return f"geerbt von {eltern.anzeige_pfad}"


def _setze_datenschutz(
    knoten: Knoten,
    eltern: Knoten,
    eigene: Stufe | None,
    typ_mindest: Stufe | None = None,
    typ_herkunft: str = "",
) -> None:
    geerbt, herkunft = eltern.datenschutz, _weitergabe(eltern)
    if typ_mindest is not None and typ_mindest > geerbt:
        geerbt, herkunft = typ_mindest, typ_herkunft

    knoten.datenschutz_mindest = geerbt
    knoten.datenschutz = geerbt
    knoten.datenschutz_herkunft = herkunft
    if eigene is None:
        return
    if eigene < geerbt:
        knoten.warnungen.append(
            f"Die eigene Stufe '{eigene.wert}' ist lockerer als '{geerbt.wert}' ({herkunft}) "
            "und wirkt deshalb nicht."
        )
        return
    knoten.datenschutz = eigene
    knoten.datenschutz_herkunft = "eigene Einstellung"


def _lade_kinder(
    workspace: Workspace, typen: TypRegister, baum: Baum, eltern: Knoten, tiefe: int
) -> None:
    try:
        eintraege = sorted(os.scandir(eltern.ordner), key=lambda e: e.name.casefold())
    except OSError as exc:
        eltern.warnungen.append(f"Ordner nicht lesbar: {exc}")
        return

    for eintrag in eintraege:
        name = eintrag.name
        if name.startswith("."):
            continue  # versteckt, z. B. unsere Zwischendateien beim Schreiben
        pfad = Path(eintrag.path)
        if ist_verknuepfung(pfad):
            eltern.warnungen.append(f"'{name}' ist eine Verknuepfung und wird nicht angezeigt")
            continue
        if not eintrag.is_dir(follow_symlinks=False):
            continue  # lose Dateien in einem Bereich gehoeren nicht in den Baum
        try:
            split_relative(name)
        except WorkspaceViolation:
            eltern.warnungen.append(f"Der Ordnername {name!r} ist ungueltig und wird ignoriert")
            continue

        hat_ordner = os.path.lexists(pfad / ORDNER_DATEI)
        hat_modul = os.path.lexists(pfad / MODUL_DATEI)
        if not hat_ordner and not hat_modul:
            eltern.warnungen.append(
                f"Ordner '{name}' hat weder folder.json noch module.json und wird ignoriert"
            )
            continue
        if tiefe > MAX_TIEFE:
            eltern.warnungen.append(f"'{name}' ist zu tief verschachtelt und wird nicht gezeigt")
            continue
        if baum.anzahl >= MAX_KNOTEN:
            baum.wurzel.warnungen.append(
                f"Mehr als {MAX_KNOTEN} Eintraege - der Rest wird nicht angezeigt"
            )
            return

        rel = f"{eltern.pfad}/{name}" if eltern.pfad else name
        art: Art = "modul" if hat_modul and not hat_ordner else "bereich"
        kind = Knoten(
            id=_vorlaeufige_id("fehler", rel),
            art=art,
            name=name,
            ordner=pfad,
            pfad=rel,
            eltern=eltern,
        )
        kind.farbe = eltern.farbe
        kind.standard_agents = eltern.standard_agents

        if hat_ordner and hat_modul:
            kind.symbol = STANDARD_SYMBOL_BEREICH
            _als_fehler(kind, "Enthaelt folder.json UND module.json - bitte eine davon entfernen")
        elif art == "bereich":
            _lade_bereich(workspace, kind, eltern)
        else:
            _lade_modul(workspace, typen, kind, eltern)

        eltern.kinder.append(kind)
        baum._registriere(kind)
        if art == "bereich" and not (hat_ordner and hat_modul):
            _lade_kinder(workspace, typen, baum, kind, tiefe + 1)


def _lade_bereich(workspace: Workspace, knoten: Knoten, eltern: Knoten) -> None:
    knoten.symbol = eltern.symbol
    try:
        datei = ordner_aus_json(lies_json(workspace, knoten.ordner / ORDNER_DATEI))
    except (ValueError, OSError) as exc:
        _als_fehler(knoten, str(exc))
        return
    knoten.ordner_datei = datei
    knoten.warnungen.extend(datei.warnungen)
    _uebernimm_id(knoten, datei.id)
    knoten.symbol = datei.symbol or eltern.symbol
    knoten.farbe = datei.farbe or eltern.farbe
    if datei.standard_agents is not None:
        knoten.standard_agents = datei.standard_agents
    _setze_datenschutz(knoten, eltern, datei.datenschutz)


def _lade_modul(workspace: Workspace, typen: TypRegister, knoten: Knoten, eltern: Knoten) -> None:
    knoten.symbol = STANDARD_SYMBOL_MODUL
    try:
        datei = modul_aus_json(lies_json(workspace, knoten.ordner / MODUL_DATEI))
    except (ValueError, OSError) as exc:
        _als_fehler(knoten, str(exc))
        return
    knoten.modul_datei = datei
    knoten.warnungen.extend(datei.warnungen)
    _uebernimm_id(knoten, datei.id)
    knoten.farbe = datei.farbe or knoten.farbe

    typ = typen.get(datei.typ)
    knoten.typ = typ
    if typ is None:
        knoten.warnungen.append(f"Der Modultyp '{datei.typ}' ist unbekannt")
        knoten.symbol = datei.symbol or STANDARD_SYMBOL_MODUL
        _setze_datenschutz(
            knoten,
            eltern,
            datei.datenschutz,
            Stufe.LOKAL,
            f"Modultyp '{datei.typ}' ist unbekannt - im Zweifel lokal",
        )
        return
    knoten.symbol = datei.symbol or typ.symbol
    _setze_datenschutz(
        knoten,
        eltern,
        datei.datenschutz,
        typ.mindest_datenschutz,
        f"Mindeststufe des Typs {typ.name}",
    )


def _uebernimm_id(knoten: Knoten, datei_id: str | None) -> None:
    if datei_id is None:
        knoten.id = _vorlaeufige_id("neu", knoten.pfad)
        knoten.id_vorlaeufig = True
    else:
        knoten.id = datei_id


def wirksame_stufe_unter(baum: Baum, pfad: Path) -> Stufe:
    """Die Stufe fuer eine Datei oder einen Ordner irgendwo im Workspace.

    Sucht den naechsten Bereich oder das naechste Modul darueber. Ordner
    ohne JSON erben so die Stufe ihres Bereichs; alles ausserhalb von
    bereiche/ hat die Stufe der Wurzel.
    """
    karte = {os.path.normcase(str(k.ordner)): k for k in baum.alle()}
    aktuell = pfad
    while True:
        treffer = karte.get(os.path.normcase(str(aktuell)))
        if treffer is not None:
            return treffer.datenschutz
        if aktuell.parent == aktuell:
            return baum.wurzel.datenschutz
        aktuell = aktuell.parent
