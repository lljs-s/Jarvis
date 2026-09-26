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
from ..errors import ConfigError
from .security import create_session_token


def startadresse(settings: Settings, token: str, *, dev: bool) -> str:
    """Die Adresse, die der Nutzer im Browser oeffnen muss - inklusive Token.

    Im Entwicklungsbetrieb liefert Vite die Oberflaeche aus (Port 5173), im
    fertigen Betrieb der Server selbst.
    """
    port = settings.ui_dev_port if dev else settings.port
    return f"http://127.0.0.1:{port}/?token={token}"


def pruefadresse(settings: Settings, token: str) -> str:
    """Adresse zum Nachsehen, ob der Server antwortet."""
    return f"http://127.0.0.1:{settings.port}/api/health?token={token}"


def pruefe_port_frei(host: str, port: int) -> None:
    """Prueft vorab, ob der Port noch frei ist.

    Ohne diese Pruefung bekommt der Nutzer eine rohe Zeile von uvicorn
    ("[Errno 98] error while attempting to bind ...") und weiss nicht, was
    er tun soll. Meistens laeuft nur noch ein alter Jarvis im Hintergrund.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as pruefer:
        pruefer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            pruefer.bind((host, port))
        except OSError as exc:
            raise ConfigError(
                f"Port {port} ist schon belegt.\n"
                "  Moegliche Gruende:\n"
                "    1. Jarvis laeuft noch in einem anderen Fenster -> dort Strg+C\n"
                "    2. Ein alter Jarvis-Prozess haengt -> im Task-Manager beenden\n"
                f"    3. Ein anderes Programm benutzt Port {port}\n"
                f"  Oder nimm einen anderen Port: JARVIS_PORT in der .env aendern."
            ) from exc


def richte_workspace_ein(settings: Settings) -> list[str]:
    """Beim allerersten Start: Wurzel, Beispiel und die vertraulichen Startbereiche.

    Existiert <Workspace>/bereiche schon, passiert nichts - geloeschte
    Bereiche kommen also nicht ungefragt zurueck.
    """
    from ..core.modules.demo import erstbefuellung
    from ..core.modules.typen import eingebaute_typen
    from ..workspace import Workspace

    return erstbefuellung(Workspace.open(settings.workspace_path), eingebaute_typen())


def serve(settings: Settings | None = None, token: str | None = None) -> None:
    """Startet nur den Server (ohne Oberflaeche)."""
    import uvicorn

    settings = settings or load_settings()
    pruefe_port_frei(settings.host, settings.port)
    angelegt = richte_workspace_ein(settings)
    if angelegt:
        print(f"Workspace eingerichtet - neue Bereiche: {', '.join(angelegt)}")  # noqa: T201
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


def beende_vite(vite: subprocess.Popen[bytes], *, frist: float = 10.0) -> None:
    """Beendet den Vite-Prozess - notfalls hart.

    Wichtig, weil Vite sonst weiterlaeuft und Port 5173 belegt: der
    naechste `jarvis dev` scheitert dann mit "Port already in use", und
    der Grund ist ein unsichtbarer Prozess von vorhin.
    """
    if vite.poll() is not None:
        return  # laeuft schon nicht mehr
    vite.terminate()
    try:
        vite.wait(timeout=frist)
    except subprocess.TimeoutExpired:
        vite.kill()


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
    # Feste Argumente, nichts davon stammt aus einer Modell- oder
    # Nutzereingabe - deshalb ist der Unterprozess hier unbedenklich.
    return subprocess.Popen(  # noqa: S603
        [npm_befehl(), "run", "dev", "--", "--port", str(settings.ui_dev_port), "--strictPort"],
        cwd=frontend_ordner(),
        env=umgebung,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
