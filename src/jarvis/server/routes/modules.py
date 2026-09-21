"""Modulbaum fuer die Seitenleiste.

Etappe 1 liefert einen Beispielbaum, damit die Oberflaeche etwas anzuzeigen
hat. Ab Etappe 2 wird er aus den echten Ordnern unter workspace/modules/
und deren module.json gelesen - die Form der Antwort bleibt dieselbe.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import ModulInfo

router = APIRouter(prefix="/api/modules", tags=["module"])

BEISPIEL_BAUM = [
    ModulInfo(
        id="privat",
        name="Privat",
        symbol="ordner",
        typ="ordner",
        kinder=[
            ModulInfo(
                id="privat/schule",
                name="Schule",
                symbol="ordner",
                typ="ordner",
                kinder=[
                    ModulInfo(id="privat/schule/mathe", name="Mathe", symbol="modul", typ="modul"),
                    ModulInfo(
                        id="privat/schule/referat", name="Referat", symbol="modul", typ="modul"
                    ),
                ],
            ),
            ModulInfo(id="privat/ideen", name="Ideen", symbol="modul", typ="modul"),
        ],
    ),
    ModulInfo(
        id="demo",
        name="Demo-Modul",
        symbol="stern",
        typ="modul",
        kinder=[],
    ),
]


@router.get("", response_model=list[ModulInfo])
def baum() -> list[ModulInfo]:
    return BEISPIEL_BAUM
