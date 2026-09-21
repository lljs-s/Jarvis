"""Der zweitwichtigste Test des Projekts: kommt jemand Fremdes an den Server?

Jarvis laeuft auf 127.0.0.1. Jede Webseite in deinem Browser darf dorthin
Anfragen schicken - deshalb muss der Server selbst entscheiden, wem er
antwortet. Diese Tests spielen genau die Angriffe durch, die es real gibt.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from jarvis.config import Settings
from jarvis.server import create_app
from jarvis.server.security import Tuersteher, create_session_token, token_ist_gueltig

TOKEN = "test-token-nur-fuer-tests"  # noqa: S105
EIGENE_ADRESSE = "http://127.0.0.1:8765"
EIGENE_ORIGIN = "http://127.0.0.1:5173"  # der Vite-Entwicklungsserver
FREMDE_ORIGIN = "https://boese-seite.example"

# Eigenheit des Testwerkzeugs: bei WebSockets traegt der Starlette-TestClient
# "testserver" als Host ein, statt die base_url zu benutzen. Ein echter
# Browser schickt immer den richtigen Host - deshalb setzen wir ihn hier von
# Hand, damit jeder Test aus dem Grund fehlschlaegt, den er pruefen will.
WS_KOPF = {"Origin": EIGENE_ORIGIN, "Host": "127.0.0.1:8765"}


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """Ein Client, der sich wie ein Browser auf dem eigenen Rechner verhaelt."""
    app = create_app(settings, token=TOKEN)
    return TestClient(app, base_url=EIGENE_ADRESSE)


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


def test_ohne_token_keine_antwort(client: TestClient) -> None:
    antwort = client.get("/api/health")
    assert antwort.status_code == 401
    assert "Token" in antwort.json()["fehler"]


def test_falsches_token_wird_abgelehnt(client: TestClient) -> None:
    antwort = client.get("/api/health", headers={"X-Jarvis-Token": "geraten"})
    assert antwort.status_code == 401


def test_richtiges_token_im_header(client: TestClient) -> None:
    antwort = client.get("/api/health", headers={"X-Jarvis-Token": TOKEN})
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "ok"


def test_richtiges_token_in_der_adresse(client: TestClient) -> None:
    """Beim ersten Aufruf kann die Oberflaeche noch keinen Header setzen."""
    antwort = client.get(f"/api/health?token={TOKEN}")
    assert antwort.status_code == 200


@pytest.mark.parametrize("pfad", ["/api/health", "/api/settings", "/api/agents", "/api/modules"])
def test_jeder_endpunkt_verlangt_ein_token(client: TestClient, pfad: str) -> None:
    assert client.get(pfad).status_code == 401
    assert client.get(pfad, headers={"X-Jarvis-Token": TOKEN}).status_code == 200


def test_token_vergleich_ist_zeitkonstant() -> None:
    assert token_ist_gueltig("abc", "abc")
    assert not token_ist_gueltig("abd", "abc")
    assert not token_ist_gueltig("", "abc")
    assert not token_ist_gueltig(None, "abc")


def test_token_wird_gewuerfelt_wenn_keins_gesetzt_ist(settings: Settings) -> None:
    erstes = create_session_token(settings)
    zweites = create_session_token(settings)
    assert erstes != zweites  # jeder Start ein neues Geheimnis
    assert len(erstes) >= 32


def test_gesetztes_token_wird_uebernommen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Startskript setzt das Token, damit es die Adresse anzeigen kann."""
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "vom-startskript")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert create_session_token(settings) == "vom-startskript"


# ---------------------------------------------------------------------------
# Origin - Schutz gegen fremde Webseiten
# ---------------------------------------------------------------------------


def test_fremde_origin_wird_abgewiesen(client: TestClient) -> None:
    """Selbst MIT gueltigem Token: eine fremde Seite kommt nicht durch."""
    antwort = client.get(
        "/api/health",
        headers={"X-Jarvis-Token": TOKEN, "Origin": FREMDE_ORIGIN},
    )
    assert antwort.status_code == 403
    assert "Origin" in antwort.json()["fehler"]


def test_eigene_origin_kommt_durch(client: TestClient) -> None:
    antwort = client.get(
        "/api/health",
        headers={"X-Jarvis-Token": TOKEN, "Origin": EIGENE_ORIGIN},
    )
    assert antwort.status_code == 200


def test_aehnliche_origin_reicht_nicht(client: TestClient) -> None:
    """ "127.0.0.1.boese.de" faengt mit unserer Adresse an - und ist trotzdem fremd."""
    for fremd in (
        "http://127.0.0.1.boese-seite.example",
        "http://localhost.boese-seite.example:5173",
        "https://127.0.0.1:5173",  # https statt http: anderer Origin
        "http://127.0.0.1:9999",  # anderer Port
    ):
        antwort = client.get("/api/health", headers={"X-Jarvis-Token": TOKEN, "Origin": fremd})
        assert antwort.status_code == 403, f"{fremd} haette abgelehnt werden muessen"


# ---------------------------------------------------------------------------
# Host - Schutz gegen DNS-Rebinding
# ---------------------------------------------------------------------------


def test_fremder_host_header_wird_abgewiesen(settings: Settings) -> None:
    """DNS-Rebinding: "boese.de" zeigt auf 127.0.0.1, der Host verraet es."""
    app = create_app(settings, token=TOKEN)
    fremder_client = TestClient(app, base_url="http://boese-seite.example:8765")
    antwort = fremder_client.get("/api/health", headers={"X-Jarvis-Token": TOKEN})
    assert antwort.status_code == 403
    assert "Host" in antwort.json()["fehler"]


def test_vite_entwicklungsserver_ist_erlaubt(settings: Settings) -> None:
    """Im Entwicklungsbetrieb kommt die Anfrage ueber Port 5173 herein.

    Gefunden durch einen echten Rauchtest: Unit-Tests sprachen den Server
    direkt an, der Browser tut das nicht.
    """
    app = create_app(settings, token=TOKEN)
    ueber_vite = TestClient(app, base_url="http://127.0.0.1:5173")
    antwort = ueber_vite.get("/api/health", headers={"X-Jarvis-Token": TOKEN})
    assert antwort.status_code == 200


def test_andere_ports_bleiben_verboten(settings: Settings) -> None:
    """Nur die zwei eigenen Ports, nicht irgendein Port auf 127.0.0.1."""
    app = create_app(settings, token=TOKEN)
    fremd = TestClient(app, base_url="http://127.0.0.1:9999")
    assert fremd.get("/api/health", headers={"X-Jarvis-Token": TOKEN}).status_code == 403


def test_localhost_ist_auch_erlaubt(settings: Settings) -> None:
    app = create_app(settings, token=TOKEN)
    lokal = TestClient(app, base_url="http://localhost:8765")
    assert lokal.get("/api/health", headers={"X-Jarvis-Token": TOKEN}).status_code == 200


# ---------------------------------------------------------------------------
# WebSocket - Cross-Site-WebSocket-Hijacking
# ---------------------------------------------------------------------------


def test_websocket_ohne_token_wird_geschlossen(client: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/chat", headers=WS_KOPF) as ws,
    ):
        ws.receive_json()


def test_websocket_mit_fremder_origin_wird_geschlossen(client: TestClient) -> None:
    """Der eigentliche Angriff: fremde Seite oeffnet still einen WebSocket.

    Ein WebSocket unterliegt NICHT der Same-Origin-Regel des Browsers.
    Ohne diese Pruefung koennte jede offene Webseite mitreden.
    """
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/chat?token={TOKEN}", headers={**WS_KOPF, "Origin": FREMDE_ORIGIN}
        ) as ws,
    ):
        ws.receive_json()


def test_websocket_ohne_origin_wird_geschlossen(client: TestClient) -> None:
    """Ein Browser schickt immer einen Origin. Fehlt er, ist es keiner."""
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/chat?token={TOKEN}", headers={"Host": "127.0.0.1:8765"}
        ) as ws,
    ):
        ws.receive_json()


def test_websocket_mit_fremdem_host_wird_geschlossen(client: TestClient) -> None:
    """DNS-Rebinding gilt auch fuer WebSockets."""
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/chat?token={TOKEN}",
            headers={"Origin": EIGENE_ORIGIN, "Host": "boese-seite.example"},
        ) as ws,
    ):
        ws.receive_json()


def test_websocket_mit_token_und_eigener_origin_antwortet(client: TestClient) -> None:
    with client.websocket_connect(f"/ws/chat?token={TOKEN}", headers=WS_KOPF) as ws:
        ws.send_json({"typ": "nachricht", "text": "Hallo Jarvis"})
        start = ws.receive_json()
        assert start["typ"] == "start"

        text = ""
        while True:
            ereignis = ws.receive_json()
            if ereignis["typ"] == "ende":
                break
            text += ereignis["text"]

        assert "Hallo Jarvis" in text
        assert "Etappe 3" in text  # ehrlicher Hinweis statt erfundener Antwort


def test_websocket_meldet_unverstandene_nachricht(client: TestClient) -> None:
    with client.websocket_connect(f"/ws/chat?token={TOKEN}", headers=WS_KOPF) as ws:
        ws.send_json({"typ": "nachricht"})  # 'text' fehlt
        antwort = ws.receive_json()
        assert antwort["typ"] == "fehler"


# ---------------------------------------------------------------------------
# Keine Geheimnisse nach draussen
# ---------------------------------------------------------------------------


def test_antworten_enthalten_keine_schluessel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-streng-geheim")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-streng-geheim")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    client = TestClient(create_app(settings, token=TOKEN), base_url=EIGENE_ADRESSE)

    for pfad in ("/api/health", "/api/settings"):
        antwort = client.get(pfad, headers={"X-Jarvis-Token": TOKEN})
        assert antwort.status_code == 200
        assert "geheim" not in antwort.text
    # Stattdessen nur die Ja/Nein-Information:
    gesundheit = client.get("/api/health", headers={"X-Jarvis-Token": TOKEN}).json()
    assert gesundheit["hat_anthropic_key"] is True
    assert gesundheit["hat_gemini_key"] is True


def test_es_gibt_keine_oeffentliche_api_dokumentation(client: TestClient) -> None:
    """/docs und /openapi.json wuerden die ganze Schnittstelle verraten."""
    for pfad in ("/docs", "/openapi.json", "/redoc"):
        assert client.get(pfad, headers={"X-Jarvis-Token": TOKEN}).status_code == 404


# ---------------------------------------------------------------------------
# Der Tuersteher fuer sich allein
# ---------------------------------------------------------------------------


def test_tuersteher_kennt_nur_lokale_hosts(settings: Settings) -> None:
    tuersteher = Tuersteher.aus_settings(settings, TOKEN)
    assert tuersteher.pruefe_host("127.0.0.1:8765") is None
    assert tuersteher.pruefe_host("LOCALHOST:8765") is None  # Gross/klein egal
    assert tuersteher.pruefe_host("boese.example") is not None
    assert tuersteher.pruefe_host(None) is not None
