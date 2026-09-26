"""Die Datenschutzstufen und die feste Regel "nie von hoeher nach niedriger"."""

from __future__ import annotations

import pytest

from jarvis.core.safety.datenschutz import Stufe, darf_fliessen, strengste


def test_reihenfolge_der_stufen() -> None:
    assert Stufe.OFFEN < Stufe.VERTRAULICH < Stufe.LOKAL


@pytest.mark.parametrize("text", ["offen", "vertraulich", "lokal"])
def test_stufe_aus_text(text: str) -> None:
    assert Stufe.aus_text(text).wert == text


@pytest.mark.parametrize("text", ["Offen", "LOKAL", "geheim", "", None, 0, 2, ["lokal"]])
def test_unbekannte_stufe_wird_abgelehnt(text: object) -> None:
    """Bei Tippfehlern wird nicht geraten - auch nicht bei Gross/Klein."""
    with pytest.raises(ValueError):
        Stufe.aus_text(text)


def test_strengste_gewinnt() -> None:
    assert strengste(Stufe.OFFEN, Stufe.LOKAL, Stufe.VERTRAULICH) is Stufe.LOKAL
    assert strengste(None, Stufe.VERTRAULICH) is Stufe.VERTRAULICH
    assert strengste() is Stufe.OFFEN


@pytest.mark.parametrize("daten", list(Stufe))
@pytest.mark.parametrize("empfaenger", list(Stufe))
def test_daten_fliessen_nie_nach_unten(daten: Stufe, empfaenger: Stufe) -> None:
    assert darf_fliessen(daten, empfaenger) == (empfaenger >= daten)


def test_vertrauliches_darf_nicht_ins_offene() -> None:
    assert not darf_fliessen(Stufe.VERTRAULICH, Stufe.OFFEN)
    assert not darf_fliessen(Stufe.LOKAL, Stufe.VERTRAULICH)
    assert darf_fliessen(Stufe.OFFEN, Stufe.LOKAL)
