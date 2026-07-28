"""Ejemplos curados para el botón «Probar» de la vista El caso. Spec 11.

El frontend NO envía argumentos arbitrarios al endpoint de probar: pide «el ejemplo
0 de `consultar_inventario`» y los argumentos salen de acá. Es la misma filosofía
que la lista blanca de campos del contrato de eventos (spec 04): lo que no se
previó, no pasa. El endpoint no tiene autenticación y, aunque las tools son de solo
lectura, argumentos libres producirían salidas que nadie revisó, en pantalla,
delante del grupo.

Los identificadores salen de `db/constantes.py`, no se escriben a mano: si el
generador cambia, los ejemplos cambian con él — la misma regla que el catálogo de
preguntas.

Los `por_que` describen lo que la herramienta MUESTRA, nunca la conclusión de
negocio: la regla de la vista es «muestra datos, nunca conclusiones» (spec 11,
bloque 3). Decir «fíjate en los correctivos» sería hacer el trabajo de la clase.
"""

from __future__ import annotations

import time
from typing import Any

from backend.db.constantes import EQUIPO_EN_RIESGO, PEDIDO_ATASCADO, PLANTAS
from backend.tools.operaciones import POR_NOMBRE

_MUNICIPIO = {p[0]: p[2] for p in PLANTAS}
_ITAGUI = _MUNICIPIO["PL-ITG"]
_BUGA = _MUNICIPIO["PL-BUG"]

EJEMPLOS: dict[str, list[dict]] = {
    "consultar_inventario": [
        {
            "argumentos": {"planta": _ITAGUI, "materia_prima": "maíz"},
            "por_que": "El dato detrás de la pregunta de la clase, sin agente de por medio.",
        },
        {
            "argumentos": {"planta": _ITAGUI},
            "por_que": "Todas las materias primas de una planta al último corte.",
        },
    ],
    "consultar_demanda": [
        {
            "argumentos": {"planta": _ITAGUI, "dias": 7, "materia_prima": "maíz"},
            "por_que": (
                "La semana proyectada, ya convertida a toneladas de materia prima: "
                "la conversión la hace la tool, no el modelo."
            ),
        },
    ],
    "consultar_produccion": [
        {
            "argumentos": {"planta": _BUGA, "dias": 30},
            "por_que": "Un mes de producción de la planta más grande, con sus paradas.",
        },
    ],
    "estado_pedido": [
        {
            "argumentos": {"numero": PEDIDO_ATASCADO},
            "por_que": "Un pedido de la base: su estado y cuántos camiones van delante.",
        },
    ],
    "turnos_muelle": [
        {
            "argumentos": {"planta": _ITAGUI},
            "por_que": "La cola del muelle: turnos, placas y horas asignadas.",
        },
    ],
    "historial_fallas": [
        {
            "argumentos": {"equipo_id": EQUIPO_EN_RIESGO},
            "por_que": "Las órdenes de un equipo concreto: tipos, causas y horas de paro.",
        },
    ],
    "lecturas_sensor": [
        {
            "argumentos": {
                "equipo_id": EQUIPO_EN_RIESGO,
                "variable": "vibracion_mm_s",
                "horas": 720,
            },
            "por_que": "Un mes de vibración, con la tendencia calculada por la tool.",
        },
    ],
}


def ejemplos_de(nombre: str) -> list[dict]:
    """Los ejemplos curados de una tool, o lista vacía si no tiene."""
    return EJEMPLOS.get(nombre, [])


def ejecutar(nombre: str, indice: int) -> dict[str, Any]:
    """Ejecuta un ejemplo curado y devuelve la respuesta del endpoint de probar.

    Sin LLM y sin escritura: usa la tool directamente, que abre la base en solo
    lectura (spec 04). Es el invariante 1 y 2 del contrato de la spec 11: esto no
    toca `llm.py` ni el contador de gasto, y no puede escribir en la base.

    `KeyError` si la tool o el ejemplo no existen — el endpoint lo traduce a 404.
    """
    funcion = POR_NOMBRE.get(nombre)
    if funcion is None:
        raise KeyError(f"No existe la herramienta '{nombre}'.")
    ejemplos = EJEMPLOS.get(nombre, [])
    if not 0 <= indice < len(ejemplos):
        raise KeyError(
            f"La herramienta '{nombre}' no tiene el ejemplo {indice} "
            f"(tiene {len(ejemplos)})."
        )

    argumentos = dict(ejemplos[indice]["argumentos"])
    antes = time.monotonic()
    resultado = funcion(**argumentos)
    ms = int((time.monotonic() - antes) * 1000)

    filas = None
    if isinstance(resultado, dict):
        for clave in ("items", "serie", "cola", "ordenes", "filas"):
            if isinstance(resultado.get(clave), list):
                filas = len(resultado[clave])
                break

    return {
        "herramienta": nombre,
        "argumentos": argumentos,
        "resultado": resultado,
        "filas": filas,
        "ms": ms,
    }
