"""Einstellungen - kommen ausschliesslich aus der Umgebung bzw. der .env.

Warum pydantic-settings? Es liest die .env, prueft die Typen (aus "12" wird
ein echtes int) und meckert frueh, wenn etwas fehlt. API-Keys liegen in
SecretStr, damit sie beim Ausdrucken von Objekten nicht versehentlich im Log
landen.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ConfigError

# Projektwurzel = zwei Ebenen ueber dieser Datei (src/jarvis/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Nur diese Adressen darf der Server bedienen. Jarvis ist eine lokale
# Anwendung: waere der Server von aussen erreichbar, koennte jeder im
# Netzwerk deine Dateien lesen.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def documents_dir() -> Path:
    """Der Dokumente-Ordner des Nutzers.

    Unter Windows fragen wir Windows selbst (SHGetKnownFolderPath). Das ist
    wichtig, weil "Dokumente" umgeleitet sein kann - etwa nach OneDrive.
    Ein festes "%USERPROFILE%\\Documents" laege dann daneben.
    """
    if os.name == "nt":
        try:
            import ctypes
            import ctypes.wintypes

            # FOLDERID_Documents als GUID {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            class GUID(ctypes.Structure):
                _fields_ = [
                    ("Data1", ctypes.c_uint32),
                    ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16),
                    ("Data4", ctypes.c_ubyte * 8),
                ]

            folderid = GUID(
                0xFDD39AD0,
                0x238F,
                0x46AF,
                (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7),
            )
            zeiger = ctypes.c_wchar_p()
            ergebnis = ctypes.windll.shell32.SHGetKnownFolderPath(  # type: ignore[attr-defined]
                ctypes.byref(folderid), 0, None, ctypes.byref(zeiger)
            )
            if ergebnis == 0 and zeiger.value:
                pfad = Path(zeiger.value)
                ctypes.windll.ole32.CoTaskMemFree(zeiger)  # type: ignore[attr-defined]
                return pfad
        except Exception:  # noqa: BLE001, S110 - hier zaehlt nur die Rueckfallebene
            # Egal warum Windows nicht antwortet: unten steht ein
            # funktionierender Ersatzweg. Ein Absturz waere hier das
            # schlechtere Verhalten.
            pass

    heim = Path.home()
    for name in ("Documents", "Dokumente"):
        if (heim / name).is_dir():
            return heim / name
    return heim


def default_workspace_dir() -> Path:
    """Standard-Workspace: Dokumente\\Jarvis-Workspace.

    Bewusst AUSSERHALB des Projektordners. Deine echten Daten haben im
    Quelltext-Repository nichts zu suchen - sonst landen sie eines Tages
    aus Versehen in einem Commit.
    """
    return documents_dir() / "Jarvis-Workspace"


class Settings(BaseSettings):
    """Alle einstellbaren Werte an einem Ort."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Modelle ----------------------------------------------------------
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    model: str = Field(default="claude-opus-5", alias="JARVIS_MODEL")
    max_tokens: int = Field(default=16000, ge=256, alias="JARVIS_MAX_TOKENS")

    # -- Workspace --------------------------------------------------------
    # None bedeutet: Standardort benutzen (Dokumente\Jarvis-Workspace).
    workspace_dir: Path | None = Field(default=None, alias="JARVIS_WORKSPACE_DIR")

    # -- Sicherheitsbremsen ------------------------------------------------
    max_steps: int = Field(default=12, ge=1, le=100, alias="JARVIS_MAX_STEPS")
    max_read_bytes: int = Field(default=200_000, ge=1024, alias="JARVIS_MAX_READ_BYTES")

    # -- Server ------------------------------------------------------------
    host: str = Field(default="127.0.0.1", alias="JARVIS_HOST")
    port: int = Field(default=8765, ge=1024, le=65535, alias="JARVIS_PORT")
    ui_dev_port: int = Field(default=5173, ge=1024, le=65535, alias="JARVIS_UI_DEV_PORT")
    # Wird beim Start erzeugt, wenn nichts gesetzt ist (siehe server/security.py).
    session_token: SecretStr | None = Field(default=None, alias="JARVIS_SESSION_TOKEN")

    # -- Kosten ------------------------------------------------------------
    # Intern rechnen wir immer in USD - so stehen es die Preislisten der
    # Anbieter. Der Kurs dient nur der Anzeige.
    usd_to_eur: float = Field(default=0.92, gt=0, lt=100, alias="JARVIS_USD_TO_EUR")
    cost_limit_usd_task: float = Field(default=0.50, gt=0, alias="JARVIS_COST_LIMIT_USD_TASK")
    cost_limit_usd_day: float = Field(default=2.00, gt=0, alias="JARVIS_COST_LIMIT_USD_DAY")

    @field_validator("anthropic_api_key", "gemini_api_key", mode="before")
    @classmethod
    def _leer_ist_kein_schluessel(cls, wert: object) -> object:
        """Ein leerer Eintrag in der .env ist KEIN Schluessel.

        Die .env.example enthaelt "GEMINI_API_KEY=" ohne Wert. Ohne diese
        Pruefung wuerde daraus SecretStr("") - also ein Objekt, das "es gibt
        einen Schluessel" bedeutet. Die Oberflaeche haette dann gemeldet,
        der Schluessel sei vorhanden, und der erste Modellaufruf waere mit
        einer unverstaendlichen Fehlermeldung der API gescheitert.
        """
        if isinstance(wert, str) and not wert.strip():
            return None
        return wert

    @field_validator("host")
    @classmethod
    def _nur_lokal(cls, wert: str) -> str:
        """Jarvis darf nur auf dem eigenen Rechner lauschen."""
        if wert not in LOOPBACK_HOSTS:
            raise ValueError(
                f"JARVIS_HOST={wert!r} ist nicht erlaubt. Jarvis lauscht nur lokal "
                f"({', '.join(sorted(LOOPBACK_HOSTS))}), damit niemand im Netzwerk "
                "an deine Dateien kommt."
            )
        return wert

    # -- Abgeleitete Werte -------------------------------------------------

    @property
    def workspace_path(self) -> Path:
        """Absoluter Workspace-Pfad (relative Angaben gelten ab Projektwurzel)."""
        if self.workspace_dir is None:
            return default_workspace_dir()
        pfad = Path(os.path.expandvars(str(self.workspace_dir))).expanduser()
        return pfad if pfad.is_absolute() else (PROJECT_ROOT / pfad)

    @property
    def allowed_origins(self) -> tuple[str, ...]:
        """Seiten, von denen der Server Anfragen annimmt.

        Nur die eigene Oberflaeche: der Server selbst (fertige App) und der
        Vite-Entwicklungsserver. Alles andere wird abgewiesen - das ist der
        Schutz gegen fremde Webseiten, die im Hintergrund deinen lokalen
        Server ansprechen wollen.
        """
        eintraege: list[str] = []
        for host in ("127.0.0.1", "localhost"):
            eintraege.append(f"http://{host}:{self.port}")
            eintraege.append(f"http://{host}:{self.ui_dev_port}")
        return tuple(eintraege)

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        """Erlaubte Werte im Host-Header (Schutz gegen DNS-Rebinding).

        Beide Ports sind dabei: im Entwicklungsbetrieb spricht der Browser
        mit dem Vite-Server (5173), der die Anfrage an uns weiterreicht -
        im Host-Header steht dann seine Adresse. Alle Eintraege bleiben
        Loopback-Adressen, ein umgebogener Name wie "boese.de" faellt
        weiterhin durch.
        """
        eintraege: list[str] = []
        for host in ("127.0.0.1", "localhost", "[::1]"):
            eintraege.append(f"{host}:{self.port}")
            eintraege.append(f"{host}:{self.ui_dev_port}")
            eintraege.append(host)
        return tuple(eintraege)

    def eur(self, usd: float) -> float:
        """Rechnet USD in EUR um - ausschliesslich fuer die Anzeige."""
        return round(usd * self.usd_to_eur, 4)

    def require_api_key(self) -> str:
        """Gibt den Anthropic-Key zurueck oder erklaert verstaendlich, was fehlt."""
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
