"""Los brazos del agente: 4 funciones + schemas JSON sobre bios_ops.db.

Spec 03 · 04. Las 4 herramientas seleccionadas para la clase 2 — una por dominio
(Mantenimiento, Compras, Logística, Producción/TD). Autocontenidas: cada una abre
un sqlite3.connect de solo lectura, consulta y devuelve un dict. No dependen del
paquete `backend/` de la clase 1.

Reglas (heredadas del contrato de la clase 1, spec 04):
· Función síncrona, anotaciones de tipo completas.
· **La docstring es el prompt que ve el modelo.** Se escribe para el modelo, no
  para el desarrollador. Es la lección práctica del nivel 3 de la clase 1.
· Devuelve un dict serializable a JSON. Nunca un DataFrame, nunca un objeto.
· El caso "sin resultados" devuelve estructura con `mensaje`, NUNCA una excepción.
· Máximo LIMITE_FILAS filas por respuesta, con `truncado: bool`.
· La conexión es de solo lectura — un agente no escribe en la base en esta sesión.
"""

from __future__ import annotations

import os
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

# Ruta a bios_ops.db. Por defecto es el archivo que se copia desde la clase 1.
# Se puede sobreescribir con la variable de entorno BIOS_DB_PATH.
_RUTA_DB = Path(
    os.getenv("BIOS_DB_PATH", Path(__file__).resolve().parent / "bios_ops.db")
)
LIMITE_FILAS = 50


# ---------------------------------------------------------------------------
#  Plomería mínima de acceso a datos — solo lectura, tolerante con los nombres
# ---------------------------------------------------------------------------


def _con() -> sqlite3.Connection:
    """Conexión de SOLO LECTURA. Cualquier escritura falla en el driver sqlite."""
    if not _RUTA_DB.exists():
        raise SystemExit(
            f"No encuentro bios_ops.db en {_RUTA_DB}. "
            "Cópiala desde la clase 1 o regenérala con "
            "`python -m backend.db.seed --recrear`."
        )
    con = sqlite3.connect(f"file:{_RUTA_DB}?mode=ro", uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    return con


def _q(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _con() as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def _uno(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    filas = _q(sql, params)
    return filas[0] if filas else None


def _norm(texto: str) -> str:
    """Minúsculas sin tildes, para comparar 'Itagüí' con 'itagui' o 'Itagui'."""
    sin = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin.lower().split())


_VACIAS = {
    "la", "el", "los", "las", "de", "del", "en", "para",
    "planta", "plantas", "sede", "municipio", "ciudad",
    "materia", "prima", "primas", "inventario", "que", "una", "un",
}


def _tokens(texto: str) -> list[str]:
    return [
        t for t in _norm(texto).replace("-", " ").split()
        if len(t) >= 3 and t not in _VACIAS
    ]


def _resolver_planta(texto: str) -> dict | None:
    """Encuentra una planta por id, nombre o municipio. Tolerante, no adivina."""
    if not texto:
        return None
    obj = _norm(texto)
    plantas = _q("SELECT * FROM plantas")
    for p in plantas:
        if obj in (_norm(p["id"]), _norm(p["nombre"]), _norm(p["municipio"])):
            return p
    pedidas = _tokens(texto)
    if not pedidas:
        return None
    for p in plantas:
        propias = set(_tokens(p["nombre"]) + _tokens(p["municipio"]) + [_norm(p["id"])])
        propias.update(_norm(p["id"]).split("-"))
        for pedida in pedidas:
            if pedida in propias:
                return p
            if len(pedida) >= 4 and any(pr.startswith(pedida) for pr in propias):
                return p
    return None


def _resolver_materia(texto: str) -> dict | None:
    """Encuentra una materia prima por id o nombre parcial ('maíz', 'maiz')."""
    if not texto:
        return None
    obj = _norm(texto)
    materias = _q("SELECT * FROM materias_primas")
    for m in materias:
        if obj in (_norm(m["id"]), _norm(m["nombre"])):
            return m
    pedidas = _tokens(texto)
    for m in materias:
        propias = set(_tokens(m["nombre"]) + [_norm(m["id"])])
        propias.update(_norm(m["id"]).split("-"))
        for pedida in pedidas:
            if pedida in propias or (
                len(pedida) >= 4 and any(pr.startswith(pedida) for pr in propias)
            ):
                return m
    return None


def _truncar(filas: list[Any]) -> tuple[list[Any], bool]:
    return filas[:LIMITE_FILAS], len(filas) > LIMITE_FILAS


def _sin_planta(texto: str) -> dict:
    return {
        "encontrado": False,
        "mensaje": f"No encontré la planta '{texto}'. Plantas: Itagüí, Buga, "
        "Mosquera, Barranquilla, Palmira.",
    }


# ---------------------------------------------------------------------------
#  1 · Inventario — dominio Compras — reto: planeación de volúmenes a plantas
# ---------------------------------------------------------------------------


def consultar_inventario(planta: str, materia_prima: str | None = None) -> dict:
    """Consulta el inventario de materias primas de una planta al último corte.

    Devuelve, por cada materia prima, la cantidad disponible en toneladas, el
    stock mínimo definido para esa planta y si está por debajo de ese mínimo.

    Usa esta herramienta para saber CUÁNTO HAY de una materia prima. Para saber
    cuánto se NECESITA en un período, usa `consultar_demanda` indicando la misma
    materia prima.

    Args:
        planta: Nombre, municipio o código de la planta. Acepta 'Itagüí',
            'Planta Itagüí' o 'PL-ITG'.
        materia_prima: Opcional. Nombre o código de una materia prima concreta,
            por ejemplo 'maíz' o 'MP-MAIZ'. Si se omite, devuelve todas.
    """
    p = _resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    corte = _uno(
        "SELECT MAX(fecha_corte) AS f FROM inventario_planta WHERE planta_id = ?",
        (p["id"],),
    )
    fecha_corte = corte["f"] if corte else None
    if not fecha_corte:
        return {
            "planta": p["nombre"], "fecha_corte": None, "items": [],
            "truncado": False,
            "mensaje": f"No hay cortes de inventario registrados para {p['nombre']}.",
        }

    sql = """SELECT m.id, m.nombre, m.unidad, m.dias_lead_time,
                    i.cantidad_ton, i.stock_minimo_ton
               FROM inventario_planta i
               JOIN materias_primas m ON m.id = i.materia_prima_id
              WHERE i.planta_id = ? AND i.fecha_corte = ?"""
    params: list[Any] = [p["id"], fecha_corte]
    if materia_prima:
        m = _resolver_materia(materia_prima)
        if not m:
            return {
                "planta": p["nombre"], "fecha_corte": fecha_corte, "items": [],
                "truncado": False,
                "mensaje": f"No encontré la materia prima '{materia_prima}'.",
            }
        sql += " AND m.id = ?"
        params.append(m["id"])

    filas = _q(sql + " ORDER BY m.nombre", tuple(params))
    items = [
        {
            "materia_prima": f["nombre"], "codigo": f["id"],
            "cantidad_ton": round(f["cantidad_ton"], 1),
            "stock_minimo_ton": round(f["stock_minimo_ton"], 1),
            "bajo_minimo": f["cantidad_ton"] < f["stock_minimo_ton"],
            "dias_lead_time": f["dias_lead_time"],
        }
        for f in filas
    ]
    items, truncado = _truncar(items)
    salida = {"planta": p["nombre"], "fecha_corte": fecha_corte,
              "items": items, "truncado": truncado}
    if not items:
        salida["mensaje"] = "No hay inventario registrado para ese criterio."
    return salida


# ---------------------------------------------------------------------------
#  2 · Demanda — dominio Producción/TD — reto: planeación de la demanda
# ---------------------------------------------------------------------------


def consultar_demanda(
    planta: str, materia_prima: str | None = None, dias: int = 7
) -> dict:
    """Consulta la demanda de producto de una planta en los últimos días.

    Devuelve el total en toneladas del período y la serie por día. La demanda es
    HISTÓRICA (los últimos `dias` días registrados) y se usa como referencia de
    lo que se espera para un período equivalente; no es un pronóstico calculado.

    IMPORTANTE — unidades: el total viene en toneladas de PRODUCTO TERMINADO. Si
    necesitas compararlo contra el inventario de una materia prima, pasa el
    parámetro `materia_prima`: la herramienta convierte la demanda a toneladas de
    esa materia prima usando su participación en la fórmula de cada producto, y
    devuelve el resultado en `requerimiento_materia_prima`. No hagas esa
    conversión por tu cuenta.

    Args:
        planta: Nombre, municipio o código de la planta.
        materia_prima: Opcional. Si se indica, añade cuántas toneladas de esa
            materia prima requiere la demanda del período, según fórmula.
        dias: Cuántos días hacia atrás incluir. Por defecto 7 (una semana).
    """
    p = _resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    dias = max(1, min(int(dias), 365))
    corte = _uno(
        "SELECT MAX(fecha) AS f FROM demanda_historica WHERE planta_id = ?",
        (p["id"],),
    )
    ultima = corte["f"] if corte else None
    if not ultima:
        return {
            "planta": p["nombre"], "periodo": None, "total_ton": 0.0,
            "serie": [], "truncado": False,
            "mensaje": f"No hay demanda registrada para {p['nombre']}.",
        }

    filas = _q(
        """SELECT fecha, producto, toneladas FROM demanda_historica
            WHERE planta_id = ? AND fecha > date(?, ?)
            ORDER BY fecha""",
        (p["id"], ultima, f"-{dias} day"),
    )
    if not filas:
        return {
            "planta": p["nombre"], "periodo": None, "total_ton": 0.0,
            "serie": [], "truncado": False,
            "mensaje": f"No hay demanda registrada para ese criterio en {p['nombre']}.",
        }

    por_dia: dict[str, float] = {}
    por_producto: dict[str, float] = {}
    for f in filas:
        por_dia[f["fecha"]] = por_dia.get(f["fecha"], 0.0) + f["toneladas"]
        por_producto[f["producto"]] = (
            por_producto.get(f["producto"], 0.0) + f["toneladas"]
        )
    total = round(sum(por_dia.values()), 1)
    serie = [
        {"fecha": k, "toneladas": round(v, 1)} for k, v in sorted(por_dia.items())
    ]
    serie_t, truncado = _truncar(serie)

    salida: dict[str, Any] = {
        "planta": p["nombre"],
        "periodo": {
            "desde": serie[0]["fecha"], "hasta": serie[-1]["fecha"],
            "dias": len(serie),
        },
        "total_ton": total,
        "promedio_dia_ton": round(total / len(serie), 1),
        "serie": serie_t,
        "truncado": truncado,
    }

    if materia_prima:
        m = _resolver_materia(materia_prima)
        if not m:
            salida["requerimiento_materia_prima"] = {
                "encontrado": False,
                "mensaje": f"No encontré la materia prima '{materia_prima}'.",
            }
        else:
            formula = {
                f["producto"]: f["inclusion_pct"]
                for f in _q(
                    "SELECT producto, inclusion_pct FROM formulas WHERE materia_prima_id = ?",
                    (m["id"],),
                )
            }
            req = 0.0
            detalle = []
            for prod, ton in sorted(por_producto.items()):
                pct = formula.get(prod, 0.0)
                aporte = ton * pct / 100.0
                req += aporte
                detalle.append({
                    "producto": prod, "demanda_ton": round(ton, 1),
                    "inclusion_pct": pct, "requiere_ton": round(aporte, 1),
                })
            salida["requerimiento_materia_prima"] = {
                "materia_prima": m["nombre"], "codigo": m["id"],
                "toneladas_requeridas": round(req, 1),
                "dias_lead_time": m["dias_lead_time"],
                "detalle_por_producto": detalle,
            }
    return salida


# ---------------------------------------------------------------------------
#  3 · Pedido — dominio Logística — reto: interfaz "tipo aeropuerto"
# ---------------------------------------------------------------------------

# Máquina de estados de pedidos (de la clase 1, db/constantes.py).
_FLUJO_PEDIDO = [
    "registrado", "programado", "en_produccion", "listo_despacho",
    "en_muelle", "cargado", "en_transito", "entregado", "novedad",
]


def estado_pedido(pedido_id: str) -> dict:
    """Consulta el estado y avance de un pedido por su número.

    Devuelve el estado actual, cuántos pasos le faltan hasta 'entregado' y, si
    está en muelle, qué turno de cargue tiene asignado. Es la base de la interfaz
    tipo aeropuerto: el cliente pregunta y obtiene dónde está su pedido.

    Args:
        pedido_id: Número del pedido. Formato 'PD-24-XXXXX'.
    """
    numero = (pedido_id or "").strip().upper()
    if not numero:
        return {"encontrado": False, "mensaje": "Indicá el número del pedido."}

    ped = _uno("SELECT * FROM pedidos WHERE numero = ?", (numero,))
    if not ped:
        return {"encontrado": False, "numero": numero,
                "mensaje": f"No encontré el pedido '{numero}'."}

    estado = ped["estado"]
    if estado == "novedad":
        pasos = None
    else:
        idx = _FLUJO_PEDIDO.index(estado) if estado in _FLUJO_PEDIDO else -1
        pasos = max(0, len(_FLUJO_PEDIDO) - 2 - idx)  # 'entregado' es el último válido

    desp = _uno(
        """SELECT turno_muelle, placa, hora_asignada, estado
             FROM despachos WHERE pedido_numero = ?""",
        (numero,),
    )
    turno = desp["turno_muelle"] if desp else None

    salida = {
        "numero": numero, "cliente": ped["cliente"],
        "producto": ped["producto"], "toneladas": round(ped["toneladas"], 1),
        "estado": estado, "pasos_faltantes": pasos,
        "fecha_pedido": ped["fecha_pedido"], "fecha_promesa": ped["fecha_promesa"],
    }
    if turno is not None:
        salida["turno_muelle"] = turno
        salida["mensaje"] = f"El pedido está en muelle, en cola turno {turno}."
    elif estado == "novedad":
        salida["mensaje"] = "El pedido tiene una novedad registrada."
    else:
        salida["mensaje"] = f"El pedido está en estado '{estado}'."
    return salida


# ---------------------------------------------------------------------------
#  4 · Fallas — dominio Mantenimiento — reto: predicción de fallas de equipos
# ---------------------------------------------------------------------------


def historial_fallas(planta: str, dias: int = 30) -> dict:
    """Consulta el historial de fallas y el estado de los equipos de una planta.

    Devuelve las órdenes de mantenimiento del período, con tipo (correctivo,
    preventivo, predictivo), causa, horas de paro y costo. Incluye el MTBF
    (tiempo medio entre fallas) y el equipo con más correctivos del período.

    Para detectar un equipo en riesgo, mira la REPETICIÓN de correctivos con la
    misma causa en poco tiempo. Combínala con el equipo de mayor criticidad
    ('alta') y con la tendencia de lecturas del sensor si la quieres confirmar.

    Args:
        planta: Nombre, municipio o código de la planta.
        dias: Ventana hacia atrás en días. Por defecto 30.
    """
    p = _resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    dias = max(1, min(int(dias), 730))

    filas = _q(
        """SELECT o.id, o.equipo_id, e.tipo AS tipo_equipo, e.criticidad,
                  o.fecha_apertura, o.fecha_cierre, o.tipo, o.causa,
                  o.horas_paro, o.costo_cop
             FROM ordenes_mantenimiento o
             JOIN equipos e ON e.id = o.equipo_id
            WHERE e.planta_id = ? AND o.fecha_apertura > date(?, ?)
            ORDER BY o.fecha_apertura DESC""",
        (p["id"], _fecha_base(), f"-{dias} day"),
    )
    if not filas:
        return {
            "planta": p["nombre"], "periodo_dias": dias, "ordenes": [],
            "total": 0, "correctivos": 0, "mtbf_dias": None,
            "truncado": False,
            "mensaje": f"No hay órdenes en {p['nombre']} en los últimos {dias} días.",
        }

    correctivos = [f for f in filas if f["tipo"] == "correctivo"]
    mtbf = None
    if len(correctivos) >= 2:
        fechas = sorted(f["fecha_apertura"] for f in correctivos)
        intervalos = [
            _diff_dias(b, a) for a, b in zip(fechas, fechas[1:])
        ]
        intervalos = [i for i in intervalos if i >= 0]
        if intervalos:
            mtbf = round(sum(intervalos) / len(intervalos), 1)

    causas: dict[str, int] = {}
    for f in correctivos:
        if f["causa"]:
            causas[f["causa"]] = causas.get(f["causa"], 0) + 1
    causa_top = max(causas.items(), key=lambda kv: kv[1]) if causas else None

    # Equipo con más correctivos — señal de patrón.
    eq_count: dict[str, int] = {}
    for f in correctivos:
        eq_count[f["equipo_id"]] = eq_count.get(f["equipo_id"], 0) + 1
    equipo_riesgo = max(eq_count.items(), key=lambda kv: kv[1]) if eq_count else None

    ordenes, truncado = _truncar([
        {
            "id": f["id"], "equipo_id": f["equipo_id"],
            "tipo_equipo": f["tipo_equipo"], "criticidad": f["criticidad"],
            "fecha_apertura": f["fecha_apertura"], "fecha_cierre": f["fecha_cierre"],
            "tipo": f["tipo"], "causa": f["causa"],
            "horas_paro": round(f["horas_paro"], 1), "costo_cop": int(f["costo_cop"]),
        }
        for f in filas
    ])

    salida = {
        "planta": p["nombre"], "periodo_dias": dias,
        "ordenes": ordenes, "total": len(filas),
        "correctivos": len(correctivos),
        "horas_paro_total": round(sum(f["horas_paro"] for f in filas), 1),
        "costo_total_cop": int(sum(f["costo_cop"] for f in filas)),
        "mtbf_dias": mtbf,
        "truncado": truncado,
    }
    if causa_top:
        salida["causa_mas_repetida"] = {"causa": causa_top[0], "veces": causa_top[1]}
    if equipo_riesgo:
        salida["equipo_con_mas_correctivos"] = {
            "equipo_id": equipo_riesgo[0], "correctivos": equipo_riesgo[1],
        }
    return salida


# ---------------------------------------------------------------------------
#  Utilidades de fechas — simples, sin numpy/pandas (librería extra innecesaria)
# ---------------------------------------------------------------------------


def _fecha_base() -> str:
    """Fecha más reciente presente en la base. Toma la máxima de demanda."""
    r = _uno("SELECT MAX(fecha) AS f FROM demanda_historica")
    return r["f"] if r and r["f"] else "2026-07-31"


def _diff_dias(a: str, b: str) -> int:
    """Días transcurridos entre dos fechas ISO 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM'."""
    from datetime import datetime
    da = datetime.fromisoformat(a[:10])
    db = datetime.fromisoformat(b[:10])
    return (db - da).days


# ---------------------------------------------------------------------------
#  Exposición para el agente
# ---------------------------------------------------------------------------


def dispatch(name: str, args: dict[str, Any]) -> dict:
    """Ejecuta la tool por nombre. Es lo que el loop ReAct llama tras la tool_call.

    En la Parte 1a (transparente) este despacho es visible y se proyecta. En la
    Parte 1b (framework) `create_react_agent` lo hace internamente — ahí se ve
    qué abstrae el framework.
    """
    if name == "consultar_inventario":
        return consultar_inventario(**args)
    if name == "consultar_demanda":
        return consultar_demanda(**args)
    if name == "estado_pedido":
        return estado_pedido(**args)
    if name == "historial_fallas":
        return historial_fallas(**args)
    return {"error": f"Tool desconocida: {name}"}


# Lista de funciones — la que `agente.py` exportará al loop.
TOOLS_FUNC = {
    "consultar_inventario": consultar_inventario,
    "consultar_demanda": consultar_demanda,
    "estado_pedido": estado_pedido,
    "historial_fallas": historial_fallas,
}

# Schemas JSON que el modelo ve — el "contrato de tools". Se escriben a mano para
# que se vean en clase: cada schema es una pieza legible, no una introspección.
SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_inventario",
            "description": consultar_inventario.__doc__.split("\n\n")[0].strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "planta": {
                        "type": "string",
                        "description": "Nombre, municipio o código de la planta.",
                    },
                    "materia_prima": {
                        "type": "string",
                        "description": "Opcional. Nombre o código de la materia prima.",
                    },
                },
                "required": ["planta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_demanda",
            "description": consultar_demanda.__doc__.split("\n\n")[0].strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "planta": {
                        "type": "string",
                        "description": "Nombre, municipio o código de la planta.",
                    },
                    "materia_prima": {
                        "type": "string",
                        "description": "Opcional. Filtra y convierte a toneladas de esa materia.",
                    },
                    "dias": {"type": "integer", "description": "Días hacia atrás. Default 7."},
                },
                "required": ["planta"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estado_pedido",
            "description": estado_pedido.__doc__.split("\n\n")[0].strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "pedido_id": {
                        "type": "string",
                        "description": "Número del pedido. Formato 'PD-24-XXXXX'.",
                    },
                },
                "required": ["pedido_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historial_fallas",
            "description": historial_fallas.__doc__.split("\n\n")[0].strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "planta": {
                        "type": "string",
                        "description": "Nombre, municipio o código de la planta.",
                    },
                    "dias": {"type": "integer", "description": "Días hacia atrás. Default 30."},
                },
                "required": ["planta"],
            },
        },
    },
]


__all__ = [
    "consultar_inventario", "consultar_demanda", "estado_pedido", "historial_fallas",
    "dispatch", "TOOLS_FUNC", "SCHEMAS",
]