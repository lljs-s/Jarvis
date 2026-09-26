"""Erstbefuellung eines leeren Workspace und der Beispielbereich.

Der Beispielbereich zeigt die Vererbung auf einen Blick:

    Beispiel            gruen, Stern, offen
    +- Oeffentlich      erbt alles        -> Linksammlung (Recherche): gruen, offen
    +- Privat           rot, vertraulich  -> Tagebuch (Notizen): rot, vertraulich

Keine echten Daten - er darf jederzeit geloescht werden.
"""

from __future__ import annotations

from datetime import date

from ...workspace import Workspace
from ..safety.datenschutz import Stufe
from .baum import BEREICHE_ORDNER
from .dienst import ModulDienst
from .formate import ORDNER_DATEI, SCHEMA_AKTUELL, neue_id, schreibe_json
from .typen import TypRegister

# Nutzertexte mit Umlauten - im Quelltext als Escape (Encoding-Ruhe unter Windows).
OEFFENTLICH = "Öffentlich"

# Bereiche, die im echten Workspace von Anfang an vertraulich sind, damit
# dort nie versehentlich offene Daten landen (Wunsch des Nutzers).
VERTRAULICHE_START_BEREICHE = ("Unternehmen", "Trading")


def _bereich(
    workspace: Workspace,
    rel: str,
    heute: date,
    *,
    beschreibung: str = "",
    stufe: Stufe | None = None,
    grund: str = "",
    symbol: str | None = None,
    farbe: str | None = None,
) -> None:
    """Schreibt eine folder.json - nur fuer die Erstbefuellung (Kern, kein Werkzeug)."""
    ordner = workspace.resolve(f"{BEREICHE_ORDNER}/{rel}")
    ordner.mkdir(parents=True, exist_ok=True)
    daten: dict[str, object] = {"schema": SCHEMA_AKTUELL, "id": neue_id("ord")}
    if beschreibung:
        daten["beschreibung"] = beschreibung
    if stufe is not None:
        daten["datenschutz"] = stufe.wert
        daten["datenschutz_grund"] = {
            "art": "gesetzt",
            "text": f"{grund} am {heute.strftime('%d.%m.%Y')}",
            "datum": heute.isoformat(),
        }
    if symbol:
        daten["symbol"] = symbol
    if farbe:
        daten["farbe"] = farbe
    schreibe_json(workspace, ordner / ORDNER_DATEI, daten)


def lege_beispiel_an(workspace: Workspace, typen: TypRegister, heute: date) -> None:
    """Der Beispielbereich mit zwei Unterbereichen und je einem Modul."""
    _bereich(
        workspace,
        "Beispiel",
        heute,
        beschreibung="Demo: zeigt, wie Einstellungen vererbt werden. Darf geloescht werden.",
        symbol="stern",
        farbe="gruen",
    )
    _bereich(workspace, f"Beispiel/{OEFFENTLICH}", heute, beschreibung="Erbt alles.")
    _bereich(
        workspace,
        "Beispiel/Privat",
        heute,
        beschreibung="Strenger als der Bereich darueber, andere Farbe.",
        stufe=Stufe.VERTRAULICH,
        grund="im Beispiel festgelegt",
        farbe="rot",
    )

    dienst = ModulDienst(workspace, typen, heute=lambda: heute)
    baum = dienst.baum()
    nach_pfad = {k.pfad: k.id for k in baum.alle()}
    dienst.modul_anlegen(nach_pfad[f"Beispiel/{OEFFENTLICH}"], "Linksammlung", "recherche")
    dienst.modul_anlegen(nach_pfad["Beispiel/Privat"], "Tagebuch", "notizen")

    beispiel = workspace.resolve(f"{BEREICHE_ORDNER}/Beispiel/Privat/Tagebuch/notizen/beispiel.md")
    beispiel.write_text(
        "# Nur ein Beispiel\n\n"
        "Dieses Modul erbt 'vertraulich' vom Bereich Privat.\n"
        "Keine echten Daten.\n",
        encoding="utf-8",
    )


def erstbefuellung(
    workspace: Workspace, typen: TypRegister, heute: date | None = None
) -> list[str]:
    """Richtet einen frischen Workspace ein. Tut nichts, wenn bereiche/ schon existiert.

    Gibt zurueck, was angelegt wurde (fuer die Anzeige beim Start).
    """
    ordner = workspace.resolve(BEREICHE_ORDNER)
    if ordner.exists():
        return []
    tag = heute or date.today()
    dienst = ModulDienst(workspace, typen, heute=lambda: tag)

    # Wurzel ("offen") ueber den Dienst, damit sie genau so aussieht wie sonst.
    dienst.sichere_wurzel()
    lege_beispiel_an(workspace, typen, tag)

    for name in VERTRAULICHE_START_BEREICHE:
        _bereich(
            workspace,
            name,
            tag,
            stufe=Stufe.VERTRAULICH,
            grund="bei der Einrichtung festgelegt",
        )
    return ["Beispiel", *VERTRAULICHE_START_BEREICHE]
