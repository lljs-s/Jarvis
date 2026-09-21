"""Endpunkte ueber Jarvis selbst: Zustand, Einstellungen."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ... import __version__
from ...config import Settings
from ..schemas import EinstellungenInfo, HealthInfo, KostenInfo

router = APIRouter(prefix="/api", tags=["system"])


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


@router.get("/health", response_model=HealthInfo)
def health(request: Request) -> HealthInfo:
    """Lebt der Server, und womit arbeitet er gerade?"""
    settings = _settings(request)
    workspace = settings.workspace_path
    return HealthInfo(
        version=__version__,
        etappe="1 - Grundgeruest der Oberflaeche (noch ohne KI)",
        workspace=str(workspace),
        workspace_existiert=workspace.is_dir(),
        modell=settings.model,
        hat_anthropic_key=settings.anthropic_api_key is not None,
        hat_gemini_key=settings.gemini_api_key is not None,
        ki_verbunden=False,
    )


@router.get("/settings", response_model=EinstellungenInfo)
def einstellungen(request: Request) -> EinstellungenInfo:
    """Anzeigbare Einstellungen - niemals Geheimnisse."""
    settings = _settings(request)
    return EinstellungenInfo(
        modell=settings.model,
        max_steps=settings.max_steps,
        max_read_bytes=settings.max_read_bytes,
        kosten=KostenInfo(
            # Echte Zahlen kommen mit dem Kostenzaehler in Etappe 4.
            heute_usd=0.0,
            heute_eur=0.0,
            limit_tag_usd=settings.cost_limit_usd_day,
            limit_tag_eur=settings.eur(settings.cost_limit_usd_day),
            limit_aufgabe_usd=settings.cost_limit_usd_task,
            kurs_usd_zu_eur=settings.usd_to_eur,
        ),
    )
