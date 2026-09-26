"""Datenschutzstufen - wer darf welche Daten sehen?

Drei Stufen, als Leiter mit Rang. "Strenger" heisst immer: hoeherer Rang.

    offen        (0)  alle Modelle, auch Cloud
    vertraulich  (1)  Cloud nur nach Freigabe pro Aufgabe (ab Etappe 4)
    lokal        (2)  nur Ollama - solange Ollama fehlt: gar kein Modell

Zwei Regeln, die ueberall gelten:

1. Vererbung: nach unten zaehlt immer das Strengste (`strengste`).
2. Datenfluss: Daten duerfen nur dorthin, wo die Stufe mindestens so hoch
   ist wie die der Daten (`darf_fliessen`). Nie von hoeher nach niedriger.
"""

from __future__ import annotations

from enum import IntEnum


class Stufe(IntEnum):
    """Eine Datenschutzstufe. Groesser = strenger."""

    OFFEN = 0
    VERTRAULICH = 1
    LOKAL = 2

    @property
    def wert(self) -> str:
        """Der Name, wie er in den JSON-Dateien steht."""
        return self.name.lower()

    @classmethod
    def aus_text(cls, text: object) -> Stufe:
        """Liest eine Stufe aus einer JSON-Datei. Unbekanntes wird abgelehnt.

        Bewusst ohne Nachsicht bei Gross-/Kleinschreibung: "Offen" ist ein
        Tippfehler, und bei Tippfehlern raten wir nicht.
        """
        if isinstance(text, str):
            for stufe in cls:
                if stufe.wert == text:
                    return stufe
        erlaubt = ", ".join(s.wert for s in cls)
        raise ValueError(f"Unbekannte Datenschutzstufe {text!r} (erlaubt: {erlaubt})")


def strengste(*stufen: Stufe | None) -> Stufe:
    """Die strengste der angegebenen Stufen; fehlende (None) zaehlen nicht."""
    vorhanden = [s for s in stufen if s is not None]
    return max(vorhanden, default=Stufe.OFFEN)


def darf_fliessen(daten: Stufe, empfaenger: Stufe) -> bool:
    """Duerfen Daten der Stufe `daten` zu einem Empfaenger mit `empfaenger`?

    Nur wenn der Empfaenger mindestens so streng ist. Das ist die feste
    Regel "nie von hoeher nach niedriger".
    """
    return empfaenger >= daten
