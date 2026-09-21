"""Der Vertrag zwischen Server und Oberflaeche.

Jede dieser Klassen entspricht genau einem TypeScript-Typ im Frontend
(frontend/src/lib/api.ts). Wer hier etwas aendert, aendert es dort mit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentStatus = Literal["idle", "laeuft", "wartet", "fertig", "fehler"]
RiskName = Literal["LOW", "MEDIUM", "HIGH"]


class HealthInfo(BaseModel):
    """Antwort von /api/health - was die Oberflaeche beim Start wissen muss."""

    status: Literal["ok"] = "ok"
    version: str
    etappe: str
    workspace: str
    workspace_existiert: bool
    modell: str
    hat_anthropic_key: bool
    hat_gemini_key: bool
    ki_verbunden: bool = Field(
        default=False,
        description="Ab Etappe 3 true. Vorher antwortet Jarvis mit einem Platzhalter.",
    )


class KostenInfo(BaseModel):
    """Kosten werden intern in USD gezaehlt, angezeigt wird EUR."""

    heute_usd: float
    heute_eur: float
    limit_tag_usd: float
    limit_tag_eur: float
    limit_aufgabe_usd: float
    kurs_usd_zu_eur: float


class EinstellungenInfo(BaseModel):
    """Was die Oberflaeche ueber die Einstellungen anzeigen darf.

    Bewusst ohne API-Keys: das Frontend bekommt nie ein Geheimnis zu sehen.
    """

    modell: str
    max_steps: int
    max_read_bytes: int
    kosten: KostenInfo


class AgentInfo(BaseModel):
    """Ein Agent im Agents-Tab."""

    id: str
    name: str
    rolle: str
    modell: str
    status: AgentStatus
    max_risiko: RiskName
    notiz: str = ""


class ModulInfo(BaseModel):
    """Ein Modul in der Seitenleiste (ab Etappe 2 aus module.json)."""

    id: str
    name: str
    symbol: str
    typ: Literal["ordner", "modul"]
    kinder: list[ModulInfo] = Field(default_factory=list)


class ChatAnfrage(BaseModel):
    """Was die Oberflaeche ueber den WebSocket schickt."""

    typ: Literal["nachricht"] = "nachricht"
    text: str = Field(min_length=1, max_length=20_000)


class ChatEreignis(BaseModel):
    """Was der Server zurueckschickt - Stueck fuer Stueck.

    `start` -> `stueck`* -> `ende`, oder `fehler`.
    """

    typ: Literal["start", "stueck", "ende", "fehler", "hinweis"]
    text: str = ""
    absender: Literal["jarvis", "system"] = "jarvis"
