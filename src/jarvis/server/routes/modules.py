"""Modulbaum fuer die Seitenleiste - gelesen aus <Workspace>/bereiche/.

Nur Uebersetzung HTTP <-> Kern. Alle Pruefungen (Namen, Stufen, Waechter)
sitzen im Modul-Dienst, damit auch die CLI nicht an ihnen vorbeikommt.
Fehler des Dienstes (ModulFehler) werden in app.py zu 400 mit Klartext.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from ...config import Settings
from ...core.modules.baum import Knoten
from ...core.modules.dienst import Aenderung, ModulDienst
from ...core.modules.typen import TypRegister
from ...core.safety.datenschutz import Stufe
from ...workspace import Workspace
from ..schemas import (
    AenderungsAntwort,
    DatenschutzSetzen,
    GrundInfo,
    KnotenInfo,
    ModulAnlegen,
    OrdnerAnlegen,
    StufeName,
    TypInfo,
    Umbenennen,
    Verschieben,
)

router = APIRouter(prefix="/api/modules", tags=["module"])

_STUFE: dict[Stufe, StufeName] = {
    Stufe.OFFEN: "offen",
    Stufe.VERTRAULICH: "vertraulich",
    Stufe.LOKAL: "lokal",
}


def _dienst(request: Request) -> ModulDienst:
    settings: Settings = request.app.state.settings
    typen: TypRegister = request.app.state.typen
    return ModulDienst(Workspace.open(settings.workspace_path), typen)


def knoten_info(knoten: Knoten) -> KnotenInfo:
    """Kern-Knoten -> Antwort fuer die Oberflaeche."""
    datei = knoten.ordner_datei or knoten.modul_datei
    grund = knoten.grund
    eigen = knoten.eigene_stufe
    return KnotenInfo(
        id=knoten.id,
        art=knoten.art,
        name=knoten.name,
        pfad=knoten.pfad,
        beschreibung=datei.beschreibung if datei else "",
        symbol=knoten.symbol,
        farbe=knoten.farbe,
        datenschutz=_STUFE[knoten.datenschutz],
        # "is not None" statt Wahrheitswert: OFFEN ist die Zahl 0 und waere sonst "nichts".
        datenschutz_eigen=_STUFE[eigen] if eigen is not None else None,
        datenschutz_mindest=_STUFE[knoten.datenschutz_mindest],
        datenschutz_herkunft=knoten.datenschutz_herkunft,
        datenschutz_grund=GrundInfo(art=grund.art, text=grund.text, datum=grund.datum)
        if grund
        else None,
        typ=knoten.modul_datei.typ if knoten.modul_datei else None,
        typ_name=knoten.typ.name if knoten.typ else None,
        abteilung=bool(knoten.modul_datei and knoten.modul_datei.abteilung),
        fehler=knoten.fehler,
        warnungen=list(knoten.warnungen),
        kinder=[knoten_info(k) for k in knoten.kinder],
    )


def _antwort(dienst: ModulDienst, aenderung: Aenderung) -> AenderungsAntwort:
    return AenderungsAntwort(
        baum=knoten_info(dienst.baum().wurzel),
        knoten_id=aenderung.knoten_id,
        warnungen=aenderung.warnungen,
        hinweise=aenderung.hinweise,
        braucht_bestaetigung=aenderung.braucht_bestaetigung,
        betroffene=aenderung.betroffene,
    )


@router.get("", response_model=KnotenInfo)
def baum(request: Request) -> KnotenInfo:
    """Der ganze Baum, beginnend bei der Wurzel."""
    return knoten_info(_dienst(request).baum().wurzel)


@router.get("/typen", response_model=list[TypInfo])
def typen(request: Request) -> list[TypInfo]:
    register: TypRegister = request.app.state.typen
    return [
        TypInfo(
            id=t.id,
            name=t.name,
            beschreibung=t.beschreibung,
            symbol=t.symbol,
            mindest_datenschutz=_STUFE[t.mindest_datenschutz],
        )
        for t in register.alle()
    ]


@router.post("/ordner", response_model=AenderungsAntwort)
def ordner_anlegen(anfrage: OrdnerAnlegen, request: Request) -> AenderungsAntwort:
    dienst = _dienst(request)
    return _antwort(dienst, dienst.ordner_anlegen(anfrage.eltern_id, anfrage.name))


@router.post("/modul", response_model=AenderungsAntwort)
def modul_anlegen(anfrage: ModulAnlegen, request: Request) -> AenderungsAntwort:
    dienst = _dienst(request)
    return _antwort(dienst, dienst.modul_anlegen(anfrage.eltern_id, anfrage.name, anfrage.typ))


@router.post("/umbenennen", response_model=AenderungsAntwort)
def umbenennen(anfrage: Umbenennen, request: Request) -> AenderungsAntwort:
    dienst = _dienst(request)
    return _antwort(dienst, dienst.umbenennen(anfrage.id, anfrage.name))


@router.post("/verschieben", response_model=AenderungsAntwort)
def verschieben(anfrage: Verschieben, request: Request) -> AenderungsAntwort:
    dienst = _dienst(request)
    return _antwort(dienst, dienst.verschieben(anfrage.id, anfrage.ziel_id))


@router.post("/datenschutz", response_model=AenderungsAntwort)
def datenschutz(anfrage: DatenschutzSetzen, request: Request) -> AenderungsAntwort:
    dienst = _dienst(request)
    stufe = Stufe.aus_text(anfrage.stufe) if anfrage.stufe is not None else None
    return _antwort(
        dienst, dienst.datenschutz_setzen(anfrage.id, stufe, bestaetigt=anfrage.bestaetigt)
    )
