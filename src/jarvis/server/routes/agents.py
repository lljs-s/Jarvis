"""Agents-Tab. In Etappe 1 nur eine feste Liste als Anschauungsmaterial.

Echte Agents kommen aus agent.yaml-Dateien (Etappe 6). Die Endpunkte gibt es
aber schon, damit die Oberflaeche gegen echte Adressen entwickelt wird und
spaeter nur der Inhalt getauscht werden muss.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import AgentInfo

router = APIRouter(prefix="/api/agents", tags=["agents"])

VORLAGEN_AGENTS = [
    AgentInfo(
        id="recherche",
        name="Recherche",
        rolle="Sucht Informationen zusammen und fasst sie zusammen.",
        modell="gemini",
        status="idle",
        max_risiko="LOW",
        notiz="Vorlage - noch nicht aktiv (Etappe 6)",
    ),
    AgentInfo(
        id="schreiben",
        name="Schreiber",
        rolle="Formuliert Texte aus Stichpunkten.",
        modell="gemini",
        status="idle",
        max_risiko="MEDIUM",
        notiz="Vorlage - noch nicht aktiv (Etappe 6)",
    ),
    AgentInfo(
        id="pruefer",
        name="Pruefer",
        rolle="Prueft Ergebnisse, bevor sie dir vorgelegt werden.",
        modell="claude",
        status="idle",
        max_risiko="LOW",
        notiz="Vorlage - noch nicht aktiv (Etappe 6)",
    ),
]


@router.get("", response_model=list[AgentInfo])
def liste() -> list[AgentInfo]:
    return VORLAGEN_AGENTS
