"""Tests fuer die Konfiguration."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.config import Settings
from jarvis.errors import ConfigError


def test_standardwerte() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.model == "claude-opus-5"
    assert settings.max_steps == 12
    assert settings.workspace_dir == Path("workspace")


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
