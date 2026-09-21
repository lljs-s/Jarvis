"""Start des lokalen Servers - mit Token und fertiger Adresse.

Getrennt von der CLI gehalten, damit `jarvis serve` und `jarvis dev`
dieselbe Logik benutzen und Tests sie ohne Typer aufrufen koennen.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..config import PROJECT_ROOT, Settings, load_settings
from .security import create_session_token


def startadresse(settings: Settings, token: str, *, dev: bool) -> str:
    """Die Adresse, die der Nutzer im Browser oeffnen muss - inklusive Token.

    Im Entwicklungsbetrieb liefert Vite die Oberflaeche aus (Port 5173), im
    fertigen Betrieb der Server selbst.
    """
    port = settings.ui_dev_port if dev else settings.port
    return f"http://127.0.0.1:{port}/?token={token}"


def serve(settings: Settings | None = None, token: str | None = None) -> None:
    """Startet nur den Server (ohne Oberflaeche)."""
    import uvicorn

    settings = settings or load_settings()
    token = token or create_session_token(settings)
    # Das Token an die App weiterreichen, ohne es auf die Kommandozeile zu
    # schreiben - dort koennten es andere Prozesse mitlesen.
    os.environ["JARVIS_SESSION_TOKEN"] = token

    from .app import create_app

    uvicorn.run(
        create_app(settings, token=token),
        host=settings.host,
        port=settings.port,
        log_level="warning",
    )


def frontend_ordner() -> Path:
    return PROJECT_ROOT / "frontend"


def npm_befehl() -> str:
    """Unter Windows heisst es npm.cmd, sonst npm."""
    return "npm.cmd" if os.name == "nt" else "npm"


def starte_vite(token: str, settings: Settings) -> subprocess.Popen[bytes]:
    """Startet den Vite-Entwicklungsserver als eigenen Prozess."""
    umgebung = os.environ.copy()
    umgebung["VITE_JARVIS_PORT"] = str(settings.port)
    umgebung["VITE_JARVIS_TOKEN"] = token
    return subprocess.Popen(
        [npm_befehl(), "run", "dev", "--", "--port", str(settings.ui_dev_port), "--strictPort"],
        cwd=frontend_ordner(),
        env=umgebung,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
