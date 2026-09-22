"""Tests fuer die Konfiguration."""

from __future__ import annotations

import pytest

from jarvis.config import PROJECT_ROOT, Settings, default_workspace_dir
from jarvis.errors import ConfigError


def test_standardwerte() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.model == "claude-opus-5"
    assert settings.max_steps == 12
    # None heisst: Standardort benutzen (Dokumente\Jarvis-Workspace).
    assert settings.workspace_dir is None


def test_werte_kommen_aus_der_umgebung(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("JARVIS_MAX_STEPS", "3")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.model == "claude-haiku-4-5"
    assert settings.max_steps == 3  # aus Text wird eine Zahl


def test_fehlender_schluessel_erklaert_sich(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        settings.require_api_key()


def test_schluessel_wird_nicht_versehentlich_gedruckt(monkeypatch: pytest.MonkeyPatch) -> None:
    """SecretStr verhindert, dass der Key in Logs oder Tracebacks landet."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-geheim")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert "geheim" not in str(settings)
    assert settings.require_api_key() == "sk-ant-geheim"


def test_workspace_pfad_wird_absolut(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_WORKSPACE_DIR", "workspace")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.workspace_path.is_absolute()


# ---------------------------------------------------------------------------
# Neu in Etappe 1: Workspace-Ort, Server-Werte, Kostenumrechnung
# ---------------------------------------------------------------------------


def test_standard_workspace_liegt_ausserhalb_des_projekts() -> None:
    """Echte Daten gehoeren nicht ins Quelltext-Verzeichnis.

    Sonst landen sie frueher oder spaeter in einem Commit.
    """
    standard = default_workspace_dir()
    assert standard.is_absolute()
    assert standard.name == "Jarvis-Workspace"
    assert PROJECT_ROOT not in standard.parents
    assert standard != PROJECT_ROOT


def test_eigener_workspace_schlaegt_den_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_WORKSPACE_DIR", "test-workspace")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.workspace_path == PROJECT_ROOT / "test-workspace"


def test_server_darf_nur_lokal_lauschen(monkeypatch: pytest.MonkeyPatch) -> None:
    """0.0.0.0 wuerde Jarvis fuer das ganze Netzwerk oeffnen."""
    monkeypatch.setenv("JARVIS_HOST", "0.0.0.0")  # noqa: S104 - genau das wird abgelehnt
    with pytest.raises(ValueError, match="nicht erlaubt"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_erlaubte_origins_enthalten_nur_lokale_adressen() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert f"http://127.0.0.1:{settings.port}" in settings.allowed_origins
    assert f"http://localhost:{settings.ui_dev_port}" in settings.allowed_origins
    for origin in settings.allowed_origins:
        assert origin.startswith(("http://127.0.0.1:", "http://localhost:"))


def test_kosten_werden_in_usd_gezaehlt_und_in_eur_angezeigt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JARVIS_USD_TO_EUR", "0.90")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.usd_to_eur == 0.90
    assert settings.eur(1.00) == 0.90
    assert settings.eur(0.1234) == 0.1111


def test_leerer_schluessel_in_der_env_zaehlt_als_fehlend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Die .env.example enthaelt leere Eintraege - die duerfen nicht zaehlen.

    Sonst meldet die Oberflaeche "Schluessel vorhanden", und der erste
    Modellaufruf scheitert mit einer Fehlermeldung der API, die dem Nutzer
    nichts sagt.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.anthropic_api_key is None
    assert settings.gemini_api_key is None
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        settings.require_api_key()


def test_echter_schluessel_bleibt_erhalten(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-echt")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.anthropic_api_key is not None
    assert settings.require_api_key() == "sk-ant-echt"
