"""Acceso a `bios_ops.db`. Siempre de solo lectura.

Spec 09, Riesgo 5: la conexión desde las tools se abre en modo URI `mode=ro`. Es la
garantía real de que un agente no escribe en la base — no la validación de texto del
SQL, que es frágil (spec 04, `ejecutar_sql`).
"""

from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from backend.config import config


class BaseNoGenerada(RuntimeError):
    """La base no existe. El mensaje dice qué ejecutar, no solo qué pasó."""


def _ruta() -> Path:
    ruta = config.ruta_db
    if not ruta.exists():
        raise BaseNoGenerada(
            f"No encuentro la base de datos en {ruta}.\n"
            "Genérala con:\n"
            "    python -m backend.db.seed --recrear\n"
            "Si estás en Docker, la imagen la trae generada: reconstruye con "
            "`docker compose build`."
        )
    return ruta


def conectar() -> sqlite3.Connection:
    """Conexión de SOLO LECTURA. Cualquier escritura falla en el driver."""
    con = sqlite3.connect(f"file:{_ruta()}?mode=ro", uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    return con


def consulta_directa(sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
    """Consulta la base sin pasar por un agente.

    Es lo que usa el notebook para contrastar la respuesta del modelo con el dato
    real —la demostración de N1— y lo que usan las celdas de verificación.
    """
    with conectar() as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def una(sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
    filas = consulta_directa(sql, params)
    return filas[0] if filas else None


def escalar(sql: str, params: tuple | dict = ()) -> Any:
    fila = una(sql, params)
    return next(iter(fila.values())) if fila else None


# --- Resolución tolerante de nombres ------------------------------------------


def _normalizar(texto: str) -> str:
    """Minúsculas sin tildes, para comparar 'Itagüí' con 'itagui'."""
    sin_tildes = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


# Palabras que no identifican nada por sí solas. Sin esta lista, "la planta de
# Cali" resolvía a la primera planta del catálogo —porque "planta" coincide con
# todas— y la tool respondía con datos de otro sitio sin avisar.
#
# Ese fallo importa más de lo que parece: la demo de cierre de N4 consiste
# precisamente en preguntar por una planta que no existe y mostrar que el agente
# dice que no encontró nada (spec 05). Con este defecto, el agente habría
# respondido con cifras de Itagüí y la lección de la clase se habría dado vuelta.
PALABRAS_VACIAS = {
    "la", "el", "los", "las", "de", "del", "en", "para", "planta", "plantas",
    "sede", "municipio", "ciudad", "materia", "prima", "primas", "inventario",
    "que", "una", "un", "nuestra", "nuestro",
}


def _tokens(texto: str) -> list[str]:
    """Palabras significativas: sin tildes, sin genéricos, de 3 letras o más."""
    return [
        t
        for t in _normalizar(texto).replace("-", " ").split()
        if len(t) >= 3 and t not in PALABRAS_VACIAS
    ]


def resolver_planta(texto: str) -> dict[str, Any] | None:
    """Encuentra una planta por id, nombre o municipio.

    Spec 04: `planta` DEBE aceptar tanto el id (`PL-ITG`) como el nombre o el
    municipio (`Itagüí`). Un agente escribe "Itagüí" porque así lo dijo el
    usuario; una tool que exige el id exacto produce un ciclo de error inútil que
    gasta tokens y confunde en la demo.

    Tolerante, pero NO adivina: si ninguna palabra significativa coincide,
    devuelve None y la tool responde "no encontré esa planta". Inventar una
    coincidencia es peor que no encontrarla.
    """
    if not texto:
        return None
    objetivo = _normalizar(texto)
    plantas = consulta_directa("SELECT * FROM plantas")

    # 1. Coincidencia exacta con id, nombre o municipio.
    for p in plantas:
        if objetivo in (
            _normalizar(p["id"]),
            _normalizar(p["nombre"]),
            _normalizar(p["municipio"]),
        ):
            return p

    # 2. Coincidencia por palabra significativa contra las palabras de la planta.
    pedidas = _tokens(texto)
    if not pedidas:
        return None
    for p in plantas:
        propias = set(
            _tokens(p["nombre"]) + _tokens(p["municipio"]) + [_normalizar(p["id"])]
        )
        propias.update(_normalizar(p["id"]).split("-"))
        for pedida in pedidas:
            if pedida in propias:
                return p
            # Prefijo largo: 'barranq' encuentra 'barranquilla'. Cuatro caracteres
            # es el mínimo para que no empiece a coincidir con cualquier cosa.
            if len(pedida) >= 4 and any(pr.startswith(pedida) for pr in propias):
                return p
    return None


def resolver_materia(texto: str) -> dict[str, Any] | None:
    """Encuentra una materia prima por id o por nombre parcial ('maíz', 'maiz').

    Misma regla que `resolver_planta`: tolerante con la forma, estricta con la
    identidad. 'maiz' encuentra 'Maíz amarillo'; 'trigo' no encuentra nada aunque
    exista 'Salvado de trigo' como palabra suelta… salvo que sea la única
    candidata, que es el caso de uso real.
    """
    if not texto:
        return None
    objetivo = _normalizar(texto)
    materias = consulta_directa("SELECT * FROM materias_primas")

    for m in materias:
        if objetivo in (_normalizar(m["id"]), _normalizar(m["nombre"])):
            return m

    pedidas = _tokens(texto)
    if not pedidas:
        return None
    candidatas = []
    for m in materias:
        propias = set(_tokens(m["nombre"]) + [_normalizar(m["id"])])
        propias.update(_normalizar(m["id"]).split("-"))
        for pedida in pedidas:
            if pedida in propias or (
                len(pedida) >= 4 and any(pr.startswith(pedida) for pr in propias)
            ):
                candidatas.append(m)
                break
    # Con una sola candidata no hay ambigüedad. Con varias, se prefiere la que
    # coincide en la primera palabra del nombre ('Maíz amarillo' para 'maiz').
    if len(candidatas) == 1:
        return candidatas[0]
    for m in candidatas:
        primera = _tokens(m["nombre"])[:1]
        if primera and primera[0] in pedidas:
            return m
    return candidatas[0] if candidatas else None


def plantas_conocidas() -> str:
    """Lista legible de plantas, para los mensajes de 'no encontré esa planta'."""
    filas = consulta_directa("SELECT nombre, municipio FROM plantas ORDER BY nombre")
    return ", ".join(f"{f['nombre']} ({f['municipio']})" for f in filas)


def conteo_por_tabla() -> dict[str, int]:
    """Filas por tabla. Lo usa `GET /api/esquema` y `verificar_entorno()`."""
    with conectar() as con:
        tablas = [
            f["name"]
            for f in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tablas}
