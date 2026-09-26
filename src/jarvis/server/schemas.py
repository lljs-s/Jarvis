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


StufeName = Literal["offen", "vertraulich", "lokal"]


class GrundInfo(BaseModel):
    """Warum eine Datenschutzstufe festgeschrieben wurde."""

    art: str
    text: str
    datum: str


class KnotenInfo(BaseModel):
    """Ein Bereich oder Modul im Baum - mit den wirksamen (vererbten) Werten.

    `pfad` ist relativ zu bereiche/ - absolute Pfade des Rechners bekommt
    die Oberflaeche nie zu sehen.
    """

    id: str
    art: Literal["bereich", "modul"]
    name: str
    pfad: str
    beschreibung: str
    symbol: str
    farbe: str
    datenschutz: StufeName
    datenschutz_eigen: StufeName | None
    datenschutz_mindest: StufeName
    datenschutz_herkunft: str
    datenschutz_grund: GrundInfo | None
    typ: str | None
    typ_name: str | None
    abteilung: bool
    fehler: str | None
    warnungen: list[str]
    kinder: list[KnotenInfo] = Field(default_factory=list)


class TypInfo(BaseModel):
    """Ein Modultyp fuer die Auswahl beim Anlegen."""

    id: str
    name: str
    beschreibung: str
    symbol: str
    mindest_datenschutz: StufeName


# Eingaben: Laengen begrenzen, damit niemand Megabytes an Namen schickt.
_Id = Field(min_length=1, max_length=64)
_Name = Field(min_length=1, max_length=80)


class OrdnerAnlegen(BaseModel):
    eltern_id: str = _Id
    name: str = _Name


class ModulAnlegen(BaseModel):
    eltern_id: str = _Id
    name: str = _Name
    typ: str = Field(min_length=1, max_length=40)


class Umbenennen(BaseModel):
    id: str = _Id
    name: str = _Name


class Verschieben(BaseModel):
    id: str = _Id
    ziel_id: str = _Id


class DatenschutzSetzen(BaseModel):
    id: str = _Id
    stufe: StufeName | None
    bestaetigt: bool = False


class AenderungsAntwort(BaseModel):
    """Antwort auf jede Aenderung: der neue Baum plus alles, was zu sagen ist."""

    baum: KnotenInfo
    knoten_id: str | None = None
    warnungen: list[str] = Field(default_factory=list)
    hinweise: list[str] = Field(default_factory=list)
    braucht_bestaetigung: bool = False
    betroffene: list[str] = Field(default_factory=list)


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
