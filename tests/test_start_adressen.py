"""Tests fuer die Adressen, die Jarvis beim Start anzeigt.

Klingt nebensaechlich, ist es aber nicht: diese Adresse ist der einzige
Weg des Nutzers in die Anwendung. Ist sie falsch zusammengesetzt, steht er
vor einer weissen Seite - und sucht den Fehler an der falschen Stelle.
(Genau das war hier einmal der Fall: aus einem fehlenden Schraegstrich
wurde "...?token=abcapi/health".)
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from jarvis.config import Settings
from jarvis.server.start import pruefadresse, startadresse

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
