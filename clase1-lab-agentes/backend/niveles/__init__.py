"""Registro de los cinco niveles.

Spec 02: un nivel nuevo se agrega creando un módulo; el tablero lo descubre. Toda
diferencia entre niveles vive dentro de `ejecutar`. Ninguna vive en el frontend.
"""

from backend.niveles import (
    n1_procesador,
    n2_router,
    n3_tool_caller,
    n4_react,
    n5_supervisor,
)
from backend.niveles.base import Ejecucion, Nivel, NivelBase, cancelar, esta_cancelado

_MODULOS = (n1_procesador, n2_router, n3_tool_caller, n4_react, n5_supervisor)

NIVELES: dict[str, NivelBase] = {m.nivel.ID: m.nivel for m in _MODULOS}
ORDEN: list[str] = [m.nivel.ID for m in _MODULOS]


def obtener(nivel_id: str) -> NivelBase | None:
    return NIVELES.get(nivel_id)


def metadatos() -> list[dict]:
    return [NIVELES[i].metadatos() for i in ORDEN]


__all__ = [
    "NIVELES",
    "ORDEN",
    "Ejecucion",
    "Nivel",
    "NivelBase",
    "cancelar",
    "esta_cancelado",
    "metadatos",
    "obtener",
]
