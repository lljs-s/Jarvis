"""Einstellungen - kommen ausschliesslich aus der Umgebung bzw. der .env.

Warum pydantic-settings? Es liest die .env, prueft die Typen (aus "12" wird
ein echtes int) und meckert frueh, wenn etwas fehlt. Der API-Key liegt in
einem SecretStr, damit er beim Ausdrucken von Objekten nicht versehentlich
im Log landet.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError

# Projektwurzel = zwei Ebenen ueber dieser Datei (src/jarvis/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Alle einstellbaren Werte an einem Ort."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    workspace_dir: Path = Field(default=Path("workspace"), alias="JARVIS_WORKSPACE_DIR")
    model: str = Field(default="claude-opus-5", alias="JARVIS_MODEL")
    max_tokens: int = Field(default=16000, ge=256, alias="JARVIS_MAX_TOKENS")
    max_steps: int = Field(default=12, ge=1, le=100, alias="JARVIS_MAX_STEPS")
    max_read_bytes: int = Field(default=200_000, ge=1024, alias="JARVIS_MAX_READ_BYTES")

    @property
    def workspace_path(self) -> Path:
        """Absoluter Workspace-Pfad (relative Angaben gelten ab Projektwurzel)."""
        path = self.workspace_dir.expanduser()
        return path if path.is_absolute() else (PROJECT_ROOT / path)

    def require_api_key(self) -> str:
        """Gibt den API-Key zurueck oder erklaert verstaendlich, was fehlt."""
        if self.anthropic_api_key is None or not self.anthropic_api_key.get_secret_value().strip():
            raise ConfigError(
                "Kein ANTHROPIC_API_KEY gefunden.\n"
                "  1. Kopiere .env.example nach .env\n"
                "  2. Trage deinen Schluessel von https://console.anthropic.com ein\n"
                "  3. Starte den Befehl erneut."
            )
        return self.anthropic_api_key.get_secret_value()


def load_settings() -> Settings:
    """Laedt die Einstellungen (eigene Funktion, damit Tests sie ersetzen koennen)."""
    return Settings()
