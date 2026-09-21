"""Die Tuersteher des lokalen Servers.

Jarvis laeuft auf deinem eigenen Rechner. Das klingt sicher, ist es aber
nicht von allein: jede Webseite, die du im Browser offen hast, kann
Anfragen an "http://127.0.0.1:8765" schicken. Ohne Schutz koennte also eine
fremde Seite im Hintergrund deine Dateien lesen lassen.

Drei Schranken verhindern das:

1. **Sitzungs-Token** - beim Start wuerfelt Jarvis ein Geheimnis aus. Ohne
   dieses Token antwortet weder REST noch WebSocket. Eine fremde Seite
   kennt es nicht und kann es auch nicht erraten.
2. **Origin-Pruefung** - der Browser schreibt bei jeder seitenfremden
   Anfrage und bei JEDEM WebSocket hinein, von welcher Seite sie kommt.
   Wir lassen nur unsere eigene Oberflaeche zu. Das ist der Schutz gegen
   Cross-Site-WebSocket-Hijacking: ein WebSocket kennt keine
   Same-Origin-Regel des Browsers, deshalb muessen wir selbst hinsehen.
3. **Host-Pruefung** - ein Angreifer kann einen Namen wie "boese.de" auf
   127.0.0.1 zeigen lassen (DNS-Rebinding) und damit die Origin-Pruefung
   umgehen. Steht dann aber "boese.de" im Host-Header, und den lassen wir
   nicht durch.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from pydantic import SecretStr
from starlette.types import ASGIApp, Receive, Scope, Send

from ..config import Settings

TOKEN_HEADER = "x-jarvis-token"
TOKEN_QUERY = "token"


def create_session_token(settings: Settings) -> str:
    """Nimmt das Token aus der Umgebung oder wuerfelt ein neues.

    Ein gesetztes JARVIS_SESSION_TOKEN braucht nur das Startskript, damit es
    dir die fertige Adresse anzeigen kann. Sonst ist ein frisches Token pro
    Start das Sicherste: nach einem Neustart gilt das alte nicht mehr.
    """
    if isinstance(settings.session_token, SecretStr):
        vorhanden = settings.session_token.get_secret_value().strip()
        if vorhanden:
            return vorhanden
    return secrets.token_urlsafe(32)


def token_ist_gueltig(gesendet: str | None, erwartet: str) -> bool:
    """Vergleicht zwei Token in konstanter Zeit.

    secrets.compare_digest braucht immer gleich lang, egal wie viele Zeichen
    stimmen. Ein normaler Vergleich (==) waere schneller fertig, sobald das
    erste Zeichen abweicht - daraus koennte jemand das Token zeichenweise
    erraten.
    """
    if not gesendet:
        return False
    return secrets.compare_digest(gesendet, erwartet)


@dataclass(frozen=True)
class Tuersteher:
    """Prueft Origin, Host und Token. Kennt kein HTTP - nur Werte."""

    token: str
    erlaubte_origins: frozenset[str]
    erlaubte_hosts: frozenset[str]

    @classmethod
    def aus_settings(cls, settings: Settings, token: str) -> Tuersteher:
        return cls(
            token=token,
            erlaubte_origins=frozenset(settings.allowed_origins),
            erlaubte_hosts=frozenset(h.lower() for h in settings.allowed_hosts),
        )

    def pruefe_host(self, host: str | None) -> str | None:
        """Gibt None zurueck, wenn alles in Ordnung ist - sonst den Grund."""
        if host is None:
            return "Kein Host-Header"
        if host.lower() not in self.erlaubte_hosts:
            return f"Host {host!r} ist nicht erlaubt (nur der eigene Rechner)"
        return None

    def pruefe_origin(self, origin: str | None, *, pflicht: bool) -> str | None:
        """Prueft die Herkunftsseite.

        `pflicht=True` gilt fuer WebSockets: Browser schicken dort immer
        einen Origin. Fehlt er, ist es kein Browser - und dann wollen wir
        ihn erst recht nicht.
        """
        if origin is None:
            return "Kein Origin-Header" if pflicht else None
        if origin not in self.erlaubte_origins:
            return f"Origin {origin!r} ist nicht erlaubt"
        return None

    def pruefe_token(self, gesendet: str | None) -> str | None:
        if not token_ist_gueltig(gesendet, self.token):
            return "Ungueltiges oder fehlendes Sitzungs-Token"
        return None


class LocalGuardMiddleware:
    """Setzt den Tuersteher fuer alle HTTP-Anfragen durch.

    Bewusst als reine ASGI-Middleware geschrieben (kein BaseHTTPMiddleware):
    so laeuft sie vor allem anderen, kann nicht von einer Route umgangen
    werden und braucht keinen zusaetzlichen Task pro Anfrage.
    """

    def __init__(self, app: ASGIApp, tuersteher: Tuersteher) -> None:
        self.app = app
        self.tuersteher = tuersteher

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # WebSockets pruefen sich in ihrer eigenen Route (dort koennen
            # wir mit einem sprechenden Code schliessen statt 403 zu senden).
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        methode = scope.get("method", "GET")

        grund = self.tuersteher.pruefe_host(headers.get("host"))
        if grund is None:
            grund = self.tuersteher.pruefe_origin(headers.get("origin"), pflicht=False)
        if grund is not None:
            await _antworte(send, 403, grund)
            return

        # CORS-Vorabfragen (OPTIONS) duerfen keinen Token tragen: der
        # Browser schickt bei ihnen grundsaetzlich keine eigenen Header.
        # Origin und Host sind oben bereits geprueft.
        if methode == "OPTIONS":
            await self.app(scope, receive, send)
            return

        gesendetes_token = headers.get(TOKEN_HEADER) or _token_aus_query(scope.get("query_string"))
        grund = self.tuersteher.pruefe_token(gesendetes_token)
        if grund is not None:
            await _antworte(send, 401, grund)
            return

        await self.app(scope, receive, send)


def _token_aus_query(query_string: bytes | None) -> str | None:
    """Liest ?token=... aus der Adresse.

    Noetig, weil die Oberflaeche beim ersten Aufruf noch keinen Header
    setzen kann - sie bekommt das Token ueber die Adresszeile.
    """
    if not query_string:
        return None
    from urllib.parse import parse_qs

    werte = parse_qs(query_string.decode("latin-1")).get(TOKEN_QUERY)
    return werte[0] if werte else None


async def _antworte(send: Send, status: int, grund: str) -> None:
    """Kurze JSON-Absage. Verraet nichts ueber das erwartete Token."""
    import json

    koerper = json.dumps({"fehler": grund}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(koerper)).encode("latin-1")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": koerper})
