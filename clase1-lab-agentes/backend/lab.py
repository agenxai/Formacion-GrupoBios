"""Fachada del laboratorio para el notebook.

El notebook construye agentes; no reimplementa plomería (spec 08). Este módulo le
da lo mínimo para ejecutar un nivel y mirar su traza:

    traza = await correr(MiN3(), PREGUNTA)
    traza.imprimir()
    assert traza.llamadas_llm == 2

`ultima_traza()` devuelve la última ejecutada, que es lo que usan las celdas de
verificación.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.eventos import Traza, resumir
from backend.niveles.base import NivelBase

# Pregunta insignia de la spec 05. Requiere dos consultas distintas y una
# comparación: N1 la inventa, N2 solo la clasifica, N3 la responde a medias, N4 la
# responde bien. La progresión se ve con una sola pregunta.
PREGUNTA = (
    "¿Cuánto maíz le queda a la planta de Itagüí y me alcanza para la demanda "
    "proyectada de esta semana?"
)

# Pregunta de N5: cruza los dos dominios, que es lo único que justifica un
# supervisor multiagente.
PREGUNTA_CRUZADA = (
    "El pedido PD-24-00871 va retrasado. ¿Es por falta de materia prima o por un "
    "problema de equipos?"
)

_ultima: Traza | None = None


async def correr(nivel: NivelBase, pregunta: str = PREGUNTA, imprimir: bool = True) -> Traza:
    """Ejecuta un nivel de principio a fin y devuelve su traza."""
    run_id = str(uuid.uuid4())
    eventos: list[Any] = []
    async for evento in nivel.ejecutar(pregunta, run_id):
        eventos.append(evento)
    traza = resumir(eventos)
    global _ultima
    _ultima = traza
    if imprimir:
        traza.imprimir()
    return traza


def ultima_traza() -> Traza:
    """La traza de la última ejecución. La usan las celdas de verificación."""
    if _ultima is None:
        raise RuntimeError(
            "Todavía no has ejecutado ningún nivel. Corre la celda anterior "
            "(la que llama a `await correr(...)`) antes de verificar."
        )
    return _ultima


def valor_real_inventario(planta: str = "Itagüí", materia: str = "maíz") -> dict:
    """El dato de verdad, consultado sin pasar por ningún modelo.

    Es lo que se proyecta al lado de la respuesta de N1 en el minuto 2 de la clase.
    """
    from backend.tools.operaciones import consultar_inventario

    r = consultar_inventario(planta, materia)
    item = (r.get("items") or [{}])[0]
    return {
        "planta": r.get("planta"),
        "fecha_corte": r.get("fecha_corte"),
        "materia_prima": item.get("materia_prima"),
        "cantidad_ton": item.get("cantidad_ton"),
        "stock_minimo_ton": item.get("stock_minimo_ton"),
        "bajo_minimo": item.get("bajo_minimo"),
    }
