"""Tests fuer den Start: angezeigte Adressen und sauberes Aufraeumen.

Klingt nebensaechlich, ist es aber nicht: diese Adresse ist der einzige
Weg des Nutzers in die Anwendung. Ist sie falsch zusammengesetzt, steht er
vor einer weissen Seite - und sucht den Fehler an der falschen Stelle.
(Genau das war hier einmal der Fall: aus einem fehlenden Schraegstrich
wurde "...?token=abcapi/health".)
"""

from __future__ import annotations

import socket
import subprocess
from urllib.parse import parse_qs, urlparse

import pytest

from jarvis.config import Settings
from jarvis.errors import ConfigError
from jarvis.server.start import beende_vite, pruefadresse, pruefe_port_frei, startadresse

TOKEN = "abc123"  # noqa: S105


@pytest.fixture()
def settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_startadresse_im_entwicklungsbetrieb_zeigt_auf_die_oberflaeche(
    settings: Settings,
) -> None:
    teile = urlparse(startadresse(settings, TOKEN, dev=True))
    assert teile.scheme == "http"
    assert teile.hostname == "127.0.0.1"
    assert teile.port == settings.ui_dev_port
    assert parse_qs(teile.query)["token"] == [TOKEN]


def test_startadresse_im_normalbetrieb_zeigt_auf_den_server(settings: Settings) -> None:
    teile = urlparse(startadresse(settings, TOKEN, dev=False))
    assert teile.port == settings.port
    assert parse_qs(teile.query)["token"] == [TOKEN]


def test_pruefadresse_zeigt_auf_den_health_endpunkt(settings: Settings) -> None:
    teile = urlparse(pruefadresse(settings, TOKEN))
    assert teile.path == "/api/health"
    assert teile.port == settings.port
    assert parse_qs(teile.query)["token"] == [TOKEN]


def test_adressen_haben_keine_doppelten_schraegstriche(settings: Settings) -> None:
    for adresse in (
        startadresse(settings, TOKEN, dev=True),
        startadresse(settings, TOKEN, dev=False),
        pruefadresse(settings, TOKEN),
    ):
        assert "//" not in adresse.removeprefix("http://")


# ---------------------------------------------------------------------------
# Aufraeumen beim Beenden
# ---------------------------------------------------------------------------


class FakeProzess:
    """Ein Vite-Prozess-Doppelgaenger fuer die Tests."""

    def __init__(self, *, laeuft: bool = True, reagiert_auf_terminate: bool = True) -> None:
        self._laeuft = laeuft
        self._reagiert = reagiert_auf_terminate
        self.terminate_gerufen = False
        self.kill_gerufen = False

    def poll(self) -> int | None:
        return None if self._laeuft else 0

    def terminate(self) -> None:
        self.terminate_gerufen = True

    def wait(self, timeout: float | None = None) -> int:
        if self._reagiert:
            self._laeuft = False
            return 0
        raise subprocess.TimeoutExpired(cmd="vite", timeout=timeout or 0)

    def kill(self) -> None:
        self.kill_gerufen = True
        self._laeuft = False


def test_vite_wird_beim_beenden_gestoppt() -> None:
    """Sonst belegt Vite weiter Port 5173 und der naechste Start scheitert."""
    vite = FakeProzess()
    beende_vite(vite)  # type: ignore[arg-type]
    assert vite.terminate_gerufen
    assert not vite.kill_gerufen


def test_haengender_vite_wird_hart_beendet() -> None:
    """Wenn Vite nicht reagiert, hilft nur noch kill - sonst bleibt der Port belegt."""
    vite = FakeProzess(reagiert_auf_terminate=False)
    beende_vite(vite, frist=0.01)  # type: ignore[arg-type]
    assert vite.terminate_gerufen
    assert vite.kill_gerufen


def test_bereits_beendeter_vite_wird_in_ruhe_gelassen() -> None:
    vite = FakeProzess(laeuft=False)
    beende_vite(vite)  # type: ignore[arg-type]
    assert not vite.terminate_gerufen
    assert not vite.kill_gerufen


# ---------------------------------------------------------------------------
# Belegter Port
# ---------------------------------------------------------------------------


def test_freier_port_stoert_nicht() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        freier_port = sock.getsockname()[1]
    # Socket ist wieder zu -> Port frei
    pruefe_port_frei("127.0.0.1", freier_port)


def test_belegter_port_erklaert_sich_verstaendlich() -> None:
    """Statt "[Errno 98] bind" soll dastehen, was der Nutzer tun kann."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as belegt:
        belegt.bind(("127.0.0.1", 0))
        belegt.listen(1)
        port = belegt.getsockname()[1]

        with pytest.raises(ConfigError) as fehler:
            pruefe_port_frei("127.0.0.1", port)

    text = str(fehler.value)
    assert str(port) in text
    assert "Strg+C" in text  # was der Nutzer als Erstes versuchen soll
    assert "JARVIS_PORT" in text  # und wie er es dauerhaft loest
