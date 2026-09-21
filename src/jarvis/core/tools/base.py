"""Basis fuer alle Werkzeuge.

Jedes Werkzeug beschreibt sich selbst (Name, Beschreibung, Eingabe-Schema)
und traegt eine Risikostufe. Die Risikostufe ist schon jetzt da, obwohl das
Approval-Gate erst in Etappe 2 kommt: der Agent fuehrt in Etappe 1 nur
LOW-Werkzeuge aus, alles andere wird abgelehnt statt still erlaubt.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, ClassVar


class RiskLevel(IntEnum):
    """Wie gefaehrlich ist eine Aktion? Groesser = gefaehrlicher."""

    LOW = 0  # nur lesen, nichts veraendert sich
    MEDIUM = 1  # neue Dateien anlegen, Netzwerk lesen
    HIGH = 2  # ueberschreiben, loeschen, Code ausfuehren, Geld kosten

    @property
    def label(self) -> str:
        return self.name


@dataclass(frozen=True)
class ToolResult:
    """Ergebnis eines Werkzeugs - genau das sieht das Modell."""

    content: str
    is_error: bool = False

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(content=f"FEHLER: {message}", is_error=True)


class Tool(ABC):
    """Ein Werkzeug. Unterklassen setzen die vier Attribute und `run`."""

    name: str
    description: str
    risk: RiskLevel
    input_schema: ClassVar[dict[str, Any]]

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Fuehrt das Werkzeug aus. Darf ToolError/WorkspaceViolation werfen."""

    def spec(self) -> dict[str, Any]:
        """Beschreibung im Format, das die Modell-Adapter erwarten."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
