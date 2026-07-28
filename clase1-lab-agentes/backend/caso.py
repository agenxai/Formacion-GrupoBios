"""El agregado de la vista «El caso» — `GET /api/caso`. Spec 11.

Todo lo que muestra la vista previa a los niveles viene de este módulo, en una sola
respuesta: el escenario, las once tablas con sus relaciones, las siete herramientas
con sus ejemplos curados y las cinco preguntas sin sus respuestas.

La regla de construcción: **ningún dato se duplica escribiéndolo a mano en dos
sitios**. Conteos, columnas y llaves foráneas se leen de la base en vivo (`PRAGMA`);
las firmas y docstrings salen de `tools.operaciones.firmas`; las preguntas, del
catálogo; los identificadores, de `db/constantes`. Lo único redactado para esta
vista vive en `db/descripciones.py` y `tools/ejemplos.py` — y la prueba de humo
verifica que no se haya desincronizado de la base.

Lo que NO sale de acá, a propósito: `nivel_que_la_resuelve`. En las vistas de
ejecución ese dato es contenido (spec 07); en El caso sería responder antes de
tiempo la pregunta que la clase existe para formular (spec 11, bloque 4).
"""

from __future__ import annotations

from typing import Any

from backend.db import conectar, consulta_directa
from backend.db.constantes import AVISO_DATOS_SINTETICOS
from backend.db.descripciones import DOMINIOS, TABLAS
from backend.preguntas import PREGUNTAS
from backend.tools.ejemplos import ejemplos_de
from backend.tools.operaciones import firmas

# Dominio de cada tool. La agrupación es la de los cuatro proyectos de los
# Champions (spec 01): cada tarjeta queda al lado de las tablas que lee, que es lo
# que conecta el bloque 2 con el bloque 3 de la vista.
DOMINIO_DE_TOOL: dict[str, str] = {
    "consultar_inventario": "compras",
    "consultar_demanda": "demanda",
    "consultar_produccion": "demanda",
    "historial_fallas": "mantenimiento",
    "lecturas_sensor": "mantenimiento",
    "estado_pedido": "logistica",
    "turnos_muelle": "logistica",
}

ESCENARIO = {
    "titulo": "El caso: las operaciones de una planta de alimentos",
    "texto": (
        "Grupo Bios produce alimentos balanceados para animales en cinco plantas. "
        "Cada planta compra materias primas (maíz, soya, tortas…), las convierte en "
        "producto terminado y despacha pedidos a sus clientes. La operación genera "
        "datos todos los días: inventarios, ventas, producción, mantenimiento, "
        "camiones. El equipo de operaciones tiene preguntas que hoy nadie responde "
        "rápido —¿me alcanza el maíz?, ¿qué equipo está por fallar?, ¿dónde va mi "
        "pedido?— y los datos para responderlas existen, pero viven en once tablas "
        "repartidas en cuatro dominios. Ese es el terreno sobre el que trabajan los "
        "cinco niveles de esta clase."
    ),
}

LIMITE_CAMPO = 80  # caracteres por campo en las filas de ejemplo (spec 11)


def _recortar(valor: Any) -> Any:
    """Las filas de ejemplo no deben romper el panel con un texto largo."""
    if isinstance(valor, str) and len(valor) > LIMITE_CAMPO:
        return valor[:LIMITE_CAMPO] + "…"
    return valor


def _tablas() -> list[dict]:
    """Las once tablas, leídas de la base y anotadas con `descripciones.py`.

    Nombres, columnas y llaves foráneas salen del esquema real (`PRAGMA`): el mapa
    no puede desincronizarse de la base porque LEE la base.
    """
    with conectar() as con:
        nombres = [
            f["name"]
            for f in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        salida = []
        for nombre in nombres:
            desc = TABLAS.get(nombre)
            columnas = [
                {"nombre": c["name"], "tipo": c["type"]}
                for c in con.execute(f"PRAGMA table_info({nombre})")
            ]
            referencias = [
                {"desde": fk["from"], "hacia": fk["table"], "campo": fk["to"]}
                for fk in con.execute(f"PRAGMA foreign_key_list({nombre})")
            ]
            conteo = con.execute(f"SELECT COUNT(*) FROM {nombre}").fetchone()[0]
            muestra = [
                {k: _recortar(v) for k, v in dict(f).items()}
                for f in con.execute(f"SELECT * FROM {nombre} LIMIT 3")
            ]
            salida.append(
                {
                    "id": nombre,
                    "dominio": (desc or {}).get("dominio", "transversal"),
                    "que_aporta": (desc or {}).get("que_aporta", ""),
                    "conteo": conteo,
                    "columnas": columnas,
                    "muestra": muestra,
                    "referencias": referencias,
                    "descrita": desc is not None,
                }
            )
    return salida


def _herramientas() -> list[dict]:
    """Las siete tools con su docstring tal como la ve el modelo y sus ejemplos."""
    return [
        {
            **f,
            "dominio": DOMINIO_DE_TOOL.get(f["nombre"], "transversal"),
            "ejemplos": ejemplos_de(f["nombre"]),
        }
        for f in firmas()
    ]


def _preguntas() -> list[dict]:
    """Las cinco preguntas de negocio, SIN el nivel que las resuelve (spec 11)."""
    return [
        {
            "chip": p["chip"],
            "texto": p["texto"],
            "dominio": p["dominio"],
            "cruza": p["cruza"],
            "tablas": p["tablas"],
        }
        for p in PREGUNTAS
    ]


def agregado() -> dict:
    """La respuesta completa de `GET /api/caso`."""
    return {
        "aviso_datos": AVISO_DATOS_SINTETICOS,
        "escenario": {
            **ESCENARIO,
            "plantas": consulta_directa(
                "SELECT id, nombre, municipio, capacidad_ton_dia FROM plantas "
                "ORDER BY capacidad_ton_dia DESC"
            ),
        },
        "dominios": [
            {"id": d, **info} for d, info in DOMINIOS.items()
        ],
        "tablas": _tablas(),
        "herramientas": _herramientas(),
        "preguntas": _preguntas(),
    }
