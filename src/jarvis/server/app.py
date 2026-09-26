"""Die FastAPI-Anwendung - zusammengesteckt, nicht ausgedacht.

Reihenfolge der Schichten (von aussen nach innen):

    CORS  ->  LocalGuardMiddleware  ->  Routen

CORS steht aussen, damit Vorabfragen (OPTIONS) beantwortet werden, ohne dass
der Browser dafuer ein Token mitschicken muesste. Der Tuersteher steht davor
- genauer: dahinter - und laesst ohne gueltiges Token nichts durch.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__
from ..config import Settings, load_settings
from ..core.modules.typen import eingebaute_typen
from ..errors import ModulFehler, WorkspaceViolation
from .routes import agents, modules, system
from .security import TOKEN_HEADER, LocalGuardMiddleware, Tuersteher, create_session_token
from .ws import router as ws_router


def create_app(settings: Settings | None = None, token: str | None = None) -> FastAPI:
    """Baut die Anwendung. Tests geben eigene Einstellungen und Token mit."""
    settings = settings or load_settings()
    token = token or create_session_token(settings)
    tuersteher = Tuersteher.aus_settings(settings, token)

    app = FastAPI(
        title="Jarvis",
        version=__version__,
        description="Lokale KI-Zentrale. Laeuft nur auf diesem Rechner.",
        docs_url=None,  # keine oeffentliche API-Dokumentation
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.token = token
    app.state.tuersteher = tuersteher
    app.state.typen = eingebaute_typen()

    # Abgelehnte Aenderungen sind kein Serverfehler: 400 mit Klartext, den
    # die Oberflaeche direkt anzeigen kann. Gleiche Form wie der Tuersteher.
    async def _abgelehnt(_: Request, fehler: Exception) -> JSONResponse:
        return JSONResponse(status_code=400, content={"fehler": str(fehler)})

    app.add_exception_handler(ModulFehler, _abgelehnt)
    app.add_exception_handler(WorkspaceViolation, _abgelehnt)

    app.include_router(system.router)
    app.include_router(agents.router)
    app.include_router(modules.router)
    app.include_router(ws_router)

    # Zuerst hinzugefuegt = weiter innen. CORS kommt also nach aussen.
    app.add_middleware(LocalGuardMiddleware, tuersteher=tuersteher)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[TOKEN_HEADER, "content-type"],
    )
    return app
