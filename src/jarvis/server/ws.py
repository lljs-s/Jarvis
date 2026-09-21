"""Der Chat-WebSocket.

In Etappe 1 antwortet hier noch kein Modell. Stattdessen kommt eine
Platzhalter-Antwort Stueck fuer Stueck zurueck - damit ist der komplette Weg
Oberflaeche -> Server -> Oberflaeche sichtbar und getestet, bevor in
Etappe 3 Gemini dahintergehaengt wird. Dann aendert sich nur, WER den Text
erzeugt, nicht wie er uebertragen wird.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket
from pydantic import ValidationError

from .schemas import ChatAnfrage, ChatEreignis
from .security import TOKEN_QUERY, Tuersteher

router = APIRouter()

# Schliesscodes: 1008 heisst laut Standard "Verstoss gegen die Regeln".
# Eigene Codes ab 4000 erlauben es der Oberflaeche, den Grund anzuzeigen.
CODE_ORIGIN = 4403
CODE_TOKEN = 4401

PLATZHALTER = (
    "Ich habe dich gehoert - aber ich bin noch nicht an ein Modell "
    "angeschlossen. Das kommt in Etappe 3 (Gemini). Bis dahin kannst du die "
    "Oberflaeche ausprobieren: Strg+K oeffnet die Befehlspalette, Strg+J "
    "springt hierher ins Eingabefeld, und /hilfe zeigt alle Slash-Befehle."
)


@router.websocket("/ws/chat")
async def chat(websocket: WebSocket) -> None:
    tuersteher: Tuersteher = websocket.app.state.tuersteher

    # WICHTIG: erst pruefen, dann accept(). Ein angenommener WebSocket
    # umgeht die Same-Origin-Regel des Browsers vollstaendig - deshalb ist
    # der Origin hier Pflicht und nicht optional wie bei REST.
    origin = websocket.headers.get("origin")
    if tuersteher.pruefe_origin(origin, pflicht=True) is not None:
        await websocket.close(code=CODE_ORIGIN, reason="Origin nicht erlaubt")
        return

    if tuersteher.pruefe_host(websocket.headers.get("host")) is not None:
        await websocket.close(code=CODE_ORIGIN, reason="Host nicht erlaubt")
        return

    token = websocket.query_params.get(TOKEN_QUERY) or websocket.headers.get("x-jarvis-token")
    if tuersteher.pruefe_token(token) is not None:
        await websocket.close(code=CODE_TOKEN, reason="Sitzungs-Token fehlt oder ist falsch")
        return

    await websocket.accept()
    try:
        while True:
            rohdaten = await websocket.receive_json()
            try:
                anfrage = ChatAnfrage.model_validate(rohdaten)
            except ValidationError as exc:
                await _sende(websocket, "fehler", f"Nachricht nicht verstanden: {exc.error_count()} Feldfehler")
                continue
            await _antworte_platzhalter(websocket, anfrage.text)
    except Exception:  # noqa: BLE001 - Verbindungsabbruch ist normal, nicht schlimm
        return


async def _antworte_platzhalter(websocket: WebSocket, frage: str) -> None:
    """Schickt die Platzhalter-Antwort wortweise, wie es spaeter das Modell tut."""
    await _sende(websocket, "start")
    text = f'Du hast geschrieben: "{frage.strip()}"\n\n{PLATZHALTER}'
    for wort in text.split(" "):
        await _sende(websocket, "stueck", wort + " ")
        await asyncio.sleep(0)  # Punkt zum Abgeben - der Server bleibt ansprechbar
    await _sende(websocket, "ende")


async def _sende(websocket: WebSocket, typ: str, text: str = "") -> None:
    ereignis = ChatEreignis(typ=typ, text=text)  # type: ignore[arg-type]
    await websocket.send_json(ereignis.model_dump())
