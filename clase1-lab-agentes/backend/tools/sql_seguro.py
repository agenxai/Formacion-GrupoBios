"""`ejecutar_sql` — alcance ampliado, reto [NÚCLEO]. Spec 04.

Las seis restricciones de la spec, todas obligatorias:

  1. Solo sentencias que empiecen por SELECT o WITH, tras normalizar espacios.
  2. Rechazo por lista negra de tokens de escritura y de `;` múltiple.
  3. Conexión abierta en modo URI de solo lectura (`file:...?mode=ro`).
  4. `LIMIT 50` forzado si la consulta no trae uno.
  5. Timeout de 5 segundos.
  6. La consulta ejecutada queda registrada en el evento `tool_result`.

Las capas 1–3 son redundantes A PROPÓSITO, y eso es el contenido de clase: la
validación por texto de SQL generado por un LLM es frágil —hay decenas de formas
de escribir algo que pase un filtro de tokens— y la garantía real es la conexión de
solo lectura. Las capas de texto solo sirven para dar un mensaje de error útil
antes de llegar al driver.

Esta tool NO está en `TODAS`. Se agrega explícitamente cuando se quiere abrir la
conversación de "la tool es la superficie de ataque del agente", que la Sesión 7
desarrolla.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from backend.config import config
from backend.tools.operaciones import LIMITE_FILAS

TIMEOUT_SEGUNDOS = 5.0

# Capa 2. No es una defensa suficiente y no se presenta como tal.
TOKENS_PROHIBIDOS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "attach",
    "detach",
    "pragma",
    "create",
    "replace",
    "vacuum",
    "reindex",
    "trigger",
)


def _normalizar(sql: str) -> str:
    return " ".join(sql.strip().split())


def ejecutar_sql(consulta: str) -> dict:
    """Ejecuta una consulta SQL de SOLO LECTURA sobre la base de operaciones.

    Solo se permiten sentencias SELECT o WITH. Cualquier intento de escritura se
    rechaza. Si la consulta no trae LIMIT, se le agrega LIMIT 50.

    Tablas disponibles: plantas, materias_primas, formulas, inventario_planta,
    demanda_historica, produccion_diaria, equipos, ordenes_mantenimiento,
    lecturas_sensor, pedidos, despachos.

    Úsala solo cuando ninguna de las otras herramientas responde la pregunta. Las
    otras devuelven los datos ya agregados y son preferibles.

    Args:
        consulta: La sentencia SQL a ejecutar.
    """
    normalizada = _normalizar(consulta or "")
    if not normalizada:
        return {"ok": False, "consulta": "", "mensaje": "La consulta viene vacía."}

    sin_punto = normalizada.rstrip(";")
    minuscula = sin_punto.lower()

    # Capa 1
    if not (minuscula.startswith("select") or minuscula.startswith("with")):
        return {
            "ok": False,
            "consulta": normalizada,
            "mensaje": "Solo se permiten consultas que empiecen por SELECT o WITH.",
        }

    # Capa 2 — incluye `;` múltiple (más de una sentencia)
    if ";" in sin_punto:
        return {
            "ok": False,
            "consulta": normalizada,
            "mensaje": "No se permite ejecutar más de una sentencia.",
        }
    for token in TOKENS_PROHIBIDOS:
        if re.search(rf"\b{token}\b", minuscula):
            return {
                "ok": False,
                "consulta": normalizada,
                "mensaje": f"La consulta contiene '{token}', que no está permitido.",
            }

    # Capa 4
    final = sin_punto
    if not re.search(r"\blimit\b", minuscula):
        final = f"{sin_punto} LIMIT {LIMITE_FILAS}"

    # Capas 3 y 5 — la garantía real
    try:
        con = sqlite3.connect(
            f"file:{config.ruta_db}?mode=ro", uri=True, timeout=TIMEOUT_SEGUNDOS
        )
        con.row_factory = sqlite3.Row
        try:
            con.execute(f"PRAGMA query_only = ON")
            filas = [dict(f) for f in con.execute(final).fetchall()]
        finally:
            con.close()
    except sqlite3.Error as exc:
        # Se devuelve como dato, no como excepción: un agente sabe recuperarse de
        # un mensaje de error, no de un stack trace.
        return {
            "ok": False,
            "consulta": final,
            "mensaje": f"SQLite rechazó la consulta: {exc}",
        }

    return {
        "ok": True,
        # Capa 6: la consulta efectivamente ejecutada viaja en el resultado y por
        # lo tanto queda en el evento `tool_result` y en la traza.
        "consulta": final,
        "filas": filas[:LIMITE_FILAS],
        "n_filas": len(filas),
        "truncado": len(filas) > LIMITE_FILAS,
    }


def _demo_por_que_es_fragil() -> list[dict[str, Any]]:
    """Casos para la discusión de clase sobre por qué la capa de texto no basta.

    No se ejecuta en la demo; está acá para que el facilitador tenga los ejemplos
    a mano si alguien pregunta.
    """
    return [
        {
            "consulta": "SELECT * FROM pedidos; DROP TABLE pedidos",
            "la_frena": "capa 2 (una sola sentencia)",
        },
        {
            "consulta": "SELECT * FROM sqlite_master",
            "la_frena": "nada — es lectura legítima, y expone el esquema completo",
        },
        {
            "consulta": "WITH x AS (SELECT 1) DELETE FROM pedidos",
            "la_frena": "capa 2 por el token, pero pasó la capa 1 empezando por WITH",
        },
        {
            "consulta": "SELECT * FROM pedidos WHERE cliente = 'DELETE'",
            "la_frena": "capa 2 — falso positivo: rechaza una consulta válida",
        },
    ]
