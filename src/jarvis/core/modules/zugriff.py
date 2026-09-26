"""Schranken zwischen Werkzeugen (also Agents) und dem Modulsystem.

1. Schreibsperre: folder.json, module.json und alles unter .jarvis/ darf
   kein Werkzeug schreiben - nur der Modul-Dienst. Sonst koennte ein Agent
   seine eigene Datenschutzstufe senken oder sich Auftraege zuschieben.
   Schreib-Werkzeuge kommen erst in Etappe 4; sie MUESSEN dann
   `pruefe_schreibzugriff` benutzen. Die Tests dafuer stehen schon jetzt.

2. Datenschutz-Sperre: ein Werkzeug gibt nur Dateien heraus, deren Stufe
   das Modell sehen darf. Cloud-Modelle sehen bis zum Freigabe-Gate
   (Etappe 4) nur "offen".
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ...errors import DatenschutzVerstoss, WorkspaceViolation
from ...workspace import Workspace, split_relative
from ..safety.datenschutz import Stufe
from .baum import SYSTEM_ORDNER, Baum, lade_baum, wirksame_stufe_unter
from .formate import SYSTEM_DATEIEN
from .typen import TypRegister, eingebaute_typen


def _im_systemordner(workspace: Workspace, pfad: Path) -> bool:
    try:
        erster = pfad.relative_to(workspace.root).parts[:1]
    except ValueError:
        return False
    return bool(erster) and erster[0].casefold() == SYSTEM_ORDNER


def ist_geschuetzt(workspace: Workspace, pfad: Path) -> bool:
    """Gehoert der Pfad dem System (Konfiguration oder Systemordner)?

    Vergleich ohne Gross/Klein: unter Windows ist MODULE.JSON dieselbe Datei.
    """
    return pfad.name.casefold() in SYSTEM_DATEIEN or _im_systemordner(workspace, pfad)


def pruefe_schreibzugriff(workspace: Workspace, relative: str) -> Path:
    """Fuer jedes kuenftige Schreib-Werkzeug: Waechter UND Systemsperre.

    Geprueft wird sowohl der angegebene als auch der aufgeloeste Pfad. Der
    aufgeloeste faengt Umwege ab, etwa den kurzen 8.3-Namen "MODULE~1.JSO",
    den Windows fuer module.json vergeben kann.
    """
    ziel = workspace.resolve(relative)
    angegeben = workspace.root.joinpath(*split_relative(relative))
    echt = Path(os.path.realpath(ziel)) if os.path.lexists(ziel) else ziel
    for pfad in (angegeben, ziel, echt):
        if ist_geschuetzt(workspace, pfad):
            raise WorkspaceViolation(
                f"{relative!r} gehoert zur Verwaltung von Jarvis (Bereiche, Module, "
                "Systemdaten) und darf von keinem Werkzeug geschrieben werden."
            )
    return ziel


@dataclass
class Sichtpruefung:
    """Ein Blick auf den Baum fuer EINEN Werkzeugaufruf.

    Pro Aufruf frisch gelesen - der Baum kann sich zwischen zwei Aufrufen
    aendern, und eine veraltete Stufe waere hier gefaehrlich.
    """

    workspace: Workspace
    erlaubt: Stufe
    baum: Baum
    ausgeblendet: int = 0
    _stufen: dict[str, Stufe] = field(default_factory=dict)

    def stufe(self, pfad: Path) -> Stufe:
        echt = Path(os.path.realpath(pfad))
        schluessel = os.path.normcase(str(echt))
        if schluessel not in self._stufen:
            if _im_systemordner(self.workspace, echt):
                self._stufen[schluessel] = Stufe.LOKAL
            else:
                self._stufen[schluessel] = wirksame_stufe_unter(self.baum, echt)
        return self._stufen[schluessel]

    def darf_sehen(self, pfad: Path) -> bool:
        return self.stufe(pfad) <= self.erlaubt

    def pruefe(self, pfad: Path) -> None:
        stufe = self.stufe(pfad)
        if stufe > self.erlaubt:
            raise DatenschutzVerstoss(
                f"{self.workspace.label(pfad)} hat die Datenschutzstufe '{stufe.wert}'. "
                f"Dieses Modell darf nur '{self.erlaubt.wert}' sehen."
            )

    def filtere(self, pfade: list[Path]) -> list[Path]:
        """Nur die sichtbaren Pfade; die Zahl der ausgeblendeten wird gemerkt."""
        sichtbar = [p for p in pfade if self.darf_sehen(p)]
        self.ausgeblendet += len(pfade) - len(sichtbar)
        return sichtbar


class DatenschutzFilter:
    """Wie streng ein Werkzeug filtern muss - je nach Modell.

    `erlaubt` ist die hoechste Stufe, die das Modell sehen darf. Standard ist
    OFFEN: sicher by default, auch wenn jemand vergisst, es anzugeben.
    """

    def __init__(
        self,
        workspace: Workspace,
        erlaubt: Stufe = Stufe.OFFEN,
        typen: TypRegister | None = None,
    ) -> None:
        self.workspace = workspace
        self.erlaubt = erlaubt
        self.typen = typen or eingebaute_typen()

    def sicht(self) -> Sichtpruefung:
        return Sichtpruefung(
            workspace=self.workspace,
            erlaubt=self.erlaubt,
            baum=lade_baum(self.workspace, self.typen),
        )
