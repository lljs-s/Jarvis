"""Der Modul-Dienst - die EINZIGE Stelle, die folder.json und module.json schreibt.

Werkzeuge (also Agents) duerfen das nie (siehe zugriff.py). Sonst koennte
ein Agent einfach die Datenschutzstufe in der Datei herabsetzen.

Alle Aenderungen laufen nach demselben Muster:
    1. Baum frisch lesen (die Platte ist die Wahrheit, nicht ein Zwischenstand)
    2. pruefen (Name, Ziel, Stufe) - bei Problemen ModulFehler mit Klartext
    3. erst die JSON-Datei, dann das Dateisystem aendern - so bleibt bei
       einem Abbruch hoechstens eine STRENGERE Stufe stehen, nie eine lockerere
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from ...errors import ModulFehler, WorkspaceViolation
from ...workspace import Workspace, split_relative
from ..safety.datenschutz import Stufe, strengste
from .baum import BEREICHE_ORDNER, Baum, Knoten, lade_baum
from .formate import (
    MODUL_DATEI,
    ORDNER_DATEI,
    SCHEMA_AKTUELL,
    SYSTEM_DATEIEN,
    lies_json,
    neue_id,
    pruefe_schema,
    schreibe_json,
)
from .typen import TypRegister

MAX_NAME = 80


@dataclass
class Aenderung:
    """Was nach einer Aenderung zu sagen ist."""

    knoten_id: str | None = None
    warnungen: list[str] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)
    # Senken der Stufe: erst nachfragen, dann (mit bestaetigt=True) ausfuehren.
    braucht_bestaetigung: bool = False
    betroffene: list[str] = field(default_factory=list)


def pruefe_name(name: object) -> str:
    """Ein Name fuer einen Bereich oder ein Modul - genau ein gueltiger Ordnername."""
    if not isinstance(name, str) or not name:
        raise ModulFehler("Bitte einen Namen eingeben.")
    if len(name) > MAX_NAME:
        raise ModulFehler(f"Der Name ist zu lang (hoechstens {MAX_NAME} Zeichen).")
    try:
        teile = split_relative(name)
    except WorkspaceViolation as exc:
        raise ModulFehler(f"Dieser Name geht nicht: {exc}") from exc
    if teile != [name]:
        raise ModulFehler("Der Name darf keine Schraegstriche enthalten und nicht '.' sein.")
    if name.startswith("."):
        raise ModulFehler("Namen mit Punkt am Anfang sind fuer das System reserviert.")
    if name.casefold() in SYSTEM_DATEIEN:
        raise ModulFehler(f"'{name}' ist fuer das System reserviert.")
    return name


def _datum_text(tag: date) -> str:
    return tag.strftime("%d.%m.%Y")


class ModulDienst:
    """Liest und veraendert den Modulbaum."""

    def __init__(
        self,
        workspace: Workspace,
        typen: TypRegister,
        heute: Callable[[], date] = date.today,
    ) -> None:
        self.workspace = workspace
        self.typen = typen
        self._heute = heute

    # -- Lesen ---------------------------------------------------------------

    def baum(self) -> Baum:
        """Der aktuelle Baum. Fehlende oder doppelte ids werden dabei repariert."""
        baum = lade_baum(self.workspace, self.typen)
        reparaturen = baum.zu_reparieren()
        if not reparaturen:
            return baum
        for knoten in reparaturen:
            praefix = "mod" if knoten.art == "modul" else "ord"
            self._aktualisiere(knoten, {"id": neue_id(praefix)})
        return lade_baum(self.workspace, self.typen)

    # -- Anlegen -------------------------------------------------------------

    def ordner_anlegen(self, eltern_id: str, name: str) -> Aenderung:
        """Legt einen neuen Bereich an. Er erbt alles vom Elternbereich."""
        name = pruefe_name(name)
        eltern = self._bereich(self.baum(), eltern_id)
        ziel = self._freier_platz(eltern, name)
        neue = neue_id("ord")
        ziel.mkdir()
        schreibe_json(self.workspace, ziel / ORDNER_DATEI, {"schema": SCHEMA_AKTUELL, "id": neue})
        return Aenderung(knoten_id=neue)

    def modul_anlegen(self, eltern_id: str, name: str, typ_id: str) -> Aenderung:
        """Legt ein Modul eines Typs an - mit den Startordnern und -dateien des Typs."""
        name = pruefe_name(name)
        typ = self.typen.get(typ_id)
        if typ is None:
            raise ModulFehler(f"Den Modultyp '{typ_id}' gibt es nicht.")
        eltern = self._bereich(self.baum(), eltern_id)
        ziel = self._freier_platz(eltern, name)
        neue = neue_id("mod")
        ziel.mkdir()
        for unterordner in typ.startordner:
            self._im_modul(ziel, unterordner).mkdir(parents=True, exist_ok=True)
        for datei in typ.startdateien:
            pfad = self._im_modul(ziel, datei.pfad)
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(datei.inhalt, encoding="utf-8")
        # module.json zuletzt: bricht vorher etwas ab, bleibt nur ein Ordner
        # ohne JSON zurueck - der wird ignoriert, nicht halb angezeigt.
        schreibe_json(
            self.workspace,
            ziel / MODUL_DATEI,
            {
                "schema": SCHEMA_AKTUELL,
                "id": neue,
                "typ": typ.id,
                "typ_version": typ.version,
                "einstellungen": typ.standard_einstellungen(),
            },
        )
        hinweise = []
        if typ.mindest_datenschutz > eltern.datenschutz:
            hinweise.append(
                f"Der Typ {typ.name} verlangt mindestens '{typ.mindest_datenschutz.wert}'."
            )
        return Aenderung(knoten_id=neue, hinweise=hinweise)

    # -- Umbenennen und Verschieben -----------------------------------------

    def umbenennen(self, knoten_id: str, name: str) -> Aenderung:
        name = pruefe_name(name)
        knoten = self._aenderbar(self.baum(), knoten_id)
        eltern = knoten.eltern
        if eltern is None:
            raise ModulFehler("Die Wurzel kann man nicht umbenennen.")
        if name == knoten.name:
            return Aenderung(knoten_id=knoten.id)
        ziel = self._freier_platz(eltern, name, erlaubt=knoten.ordner)
        os.rename(knoten.ordner, ziel)
        return Aenderung(knoten_id=knoten.id)

    def verschieben(self, knoten_id: str, ziel_id: str) -> Aenderung:
        """Verschiebt einen Bereich oder ein Modul in einen anderen Bereich.

        Strengerer Bereich: die Stufe steigt von selbst (Vererbung).
        Lockererer Bereich: die bisherige Stufe wird mit Grund festgeschrieben.
        """
        baum = self.baum()
        knoten = self._aenderbar(baum, knoten_id)
        alt_eltern = knoten.eltern
        if alt_eltern is None:
            raise ModulFehler("Die Wurzel kann man nicht verschieben.")
        ziel = self._bereich(baum, ziel_id)
        if ziel is knoten or knoten.ist_vorfahr_von(ziel):
            raise ModulFehler("Ein Bereich kann nicht in sich selbst verschoben werden.")
        if ziel is alt_eltern:
            return Aenderung(knoten_id=knoten.id)
        neuer_ort = self._freier_platz(ziel, knoten.name)

        alt = knoten.datenschutz
        neu_geerbt = strengste(ziel.datenschutz, _typ_mindest(knoten))
        ergebnis = Aenderung(knoten_id=knoten.id)
        # Steht die Stufe schon als eigene Einstellung in der Datei, bleibt
        # sie samt ihrem Grund - nur Geerbtes muss festgeschrieben werden.
        schon_eigen = knoten.eigene_stufe is not None and knoten.eigene_stufe >= alt

        if alt > neu_geerbt and schon_eigen:
            ergebnis.warnungen.append(
                f"'{knoten.name}' behaelt seine eigene Stufe '{alt.wert}', obwohl "
                f"'{ziel.anzeige_pfad}' nur '{neu_geerbt.wert}' ist."
            )
        elif alt > neu_geerbt:
            heute = self._heute()
            self._aktualisiere(
                knoten,
                {
                    "datenschutz": alt.wert,
                    "datenschutz_grund": {
                        "art": "verschoben",
                        "text": (
                            f"festgeschrieben beim Verschieben aus {alt_eltern.anzeige_pfad} "
                            f"am {_datum_text(heute)}"
                        ),
                        "datum": heute.isoformat(),
                    },
                },
            )
            ergebnis.warnungen.append(
                f"'{knoten.name}' behaelt die Stufe '{alt.wert}', obwohl "
                f"'{ziel.anzeige_pfad}' nur '{neu_geerbt.wert}' ist. "
                "Der Grund ist gespeichert; du kannst die Stufe bewusst senken."
            )
        elif neu_geerbt > alt:
            ergebnis.hinweise.append(
                f"'{knoten.name}' ist jetzt '{neu_geerbt.wert}' (geerbt von {ziel.anzeige_pfad})."
            )

        os.rename(knoten.ordner, neuer_ort)
        return ergebnis

    # -- Datenschutz ----------------------------------------------------------

    def datenschutz_setzen(
        self, knoten_id: str, stufe: Stufe | None, *, bestaetigt: bool = False
    ) -> Aenderung:
        """Setzt die eigene Stufe (None = vom Bereich erben).

        Strenger geht immer. Tiefer als die geerbte Stufe geht nie. Wird durch
        die Aenderung irgendetwas lockerer (dieser Eintrag oder etwas darunter),
        braucht es eine ausdrueckliche Bestaetigung.
        """
        knoten = self._aenderbar(self.baum(), knoten_id)
        mindest = knoten.datenschutz_mindest
        if stufe is not None and stufe < mindest:
            raise ModulFehler(
                f"Tiefer als '{mindest.wert}' geht es hier nicht ({knoten.datenschutz_herkunft})."
            )

        neu = strengste(mindest, stufe)
        lockerer = [(knoten, knoten.datenschutz, neu)] if neu < knoten.datenschutz else []
        for kind in knoten.kinder:
            lockerer.extend(_simuliere(kind, neu))
        if lockerer and not bestaetigt:
            return Aenderung(
                knoten_id=knoten.id,
                braucht_bestaetigung=True,
                betroffene=[
                    f"{k.anzeige_pfad}: {vorher.wert} -> {nachher.wert}"
                    for k, vorher, nachher in lockerer
                ],
            )

        aenderungen: dict[str, Any]
        if stufe is None:
            aenderungen = {"datenschutz": None, "datenschutz_grund": None}
        else:
            heute = self._heute()
            aenderungen = {
                "datenschutz": stufe.wert,
                "datenschutz_grund": {
                    "art": "gesetzt",
                    "text": f"von dir gesetzt am {_datum_text(heute)}",
                    "datum": heute.isoformat(),
                },
            }
        self._aktualisiere(knoten, aenderungen)
        return Aenderung(knoten_id=knoten.id)

    # -- intern -----------------------------------------------------------------

    def _bereich(self, baum: Baum, knoten_id: str) -> Knoten:
        """Ein Bereich, in den man etwas legen darf."""
        knoten = baum.finde(knoten_id)
        if knoten.art != "bereich":
            raise ModulFehler("In ein Modul kann man nichts hineinlegen - nur in einen Bereich.")
        if knoten.fehler:
            raise ModulFehler(
                f"'{knoten.anzeige_pfad}' ist fehlerhaft ({knoten.fehler}). "
                "Bitte zuerst reparieren."
            )
        if knoten.ist_wurzel:
            self._sichere_wurzel()
        return knoten

    def _aenderbar(self, baum: Baum, knoten_id: str) -> Knoten:
        knoten = baum.finde(knoten_id)
        if knoten.fehler:
            raise ModulFehler(
                f"'{knoten.anzeige_pfad}' ist fehlerhaft ({knoten.fehler}). "
                "Jarvis aendert fehlerhafte Eintraege nicht - bitte zuerst die Datei reparieren."
            )
        if knoten.ist_wurzel:
            self._sichere_wurzel()
        return knoten

    def _sichere_wurzel(self) -> None:
        """Legt bereiche/ mit folder.json an, falls es noch fehlt."""
        ordner = self.workspace.resolve(BEREICHE_ORDNER)
        ordner.mkdir(exist_ok=True)
        if not os.path.lexists(ordner / ORDNER_DATEI):
            schreibe_json(
                self.workspace,
                ordner / ORDNER_DATEI,
                {
                    "schema": SCHEMA_AKTUELL,
                    "beschreibung": "Wurzel des Modulbaums",
                    "datenschutz": Stufe.OFFEN.wert,
                },
            )

    def _freier_platz(self, eltern: Knoten, name: str, erlaubt: Path | None = None) -> Path:
        """Der Pfad fuer `name` im Bereich `eltern` - geprueft vom Waechter."""
        rel = "/".join(p for p in (BEREICHE_ORDNER, eltern.pfad, name) if p)
        ziel = self.workspace.resolve(rel)
        if os.path.lexists(ziel):
            # Windows unterscheidet Gross/Klein nicht: "mathe" -> "Mathe" ist
            # dieselbe Stelle und beim Umbenennen erlaubt.
            if erlaubt is not None and os.path.samefile(ziel, erlaubt):
                return ziel.parent / name
            raise ModulFehler(f"In '{eltern.anzeige_pfad}' gibt es schon '{name}'.")
        return ziel

    def _im_modul(self, modul_ordner: Path, rel: str) -> Path:
        """Ein Pfad innerhalb eines Moduls - ebenfalls durch den Waechter."""
        basis = self.workspace.label(modul_ordner)
        return self.workspace.resolve(f"{basis}/{rel}")

    def _aktualisiere(self, knoten: Knoten, aenderungen: dict[str, Any]) -> None:
        """Aendert Felder der JSON-Datei; unbekannte Felder bleiben erhalten.

        `None` entfernt ein Feld. Eine Datei mit neuerer Schema-Version wird
        nie geschrieben - sonst gingen deren Felder verloren.
        """
        dateiname = MODUL_DATEI if knoten.art == "modul" else ORDNER_DATEI
        pfad = knoten.ordner / dateiname
        try:
            roh = lies_json(self.workspace, pfad)
            pruefe_schema(roh, dateiname)
        except (ValueError, OSError) as exc:
            raise ModulFehler(f"'{knoten.anzeige_pfad}' laesst sich nicht aendern: {exc}") from exc
        for schluessel, wert in aenderungen.items():
            if wert is None:
                roh.pop(schluessel, None)
            else:
                roh[schluessel] = wert
        schreibe_json(self.workspace, pfad, roh)


def _typ_mindest(knoten: Knoten) -> Stufe | None:
    """Mindeststufe durch den Typ; ein unbekannter Typ zaehlt als lokal (wie im Baum)."""
    if knoten.art != "modul":
        return None
    return knoten.typ.mindest_datenschutz if knoten.typ else Stufe.LOKAL


def _simuliere(knoten: Knoten, eltern_stufe: Stufe) -> list[tuple[Knoten, Stufe, Stufe]]:
    """Welche Eintraege wuerden lockerer, wenn der Elternbereich `eltern_stufe` haette?"""
    if knoten.fehler:
        return []  # fehlerhafte bleiben lokal
    neu = strengste(eltern_stufe, _typ_mindest(knoten), knoten.eigene_stufe)
    ergebnis = [(knoten, knoten.datenschutz, neu)] if neu < knoten.datenschutz else []
    for kind in knoten.kinder:
        ergebnis.extend(_simuliere(kind, neu))
    return ergebnis
