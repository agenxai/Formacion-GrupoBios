"""Las 7 tools de dominio del laboratorio.

Spec 04, contrato de tools. Reglas que aplican a todas:

· Función Python síncrona, con anotaciones de tipo completas.
· **La docstring es el prompt que ve el modelo.** Se escribe para el modelo, no
  para el desarrollador. Es una de las lecciones prácticas del nivel 3: si el
  agente ignora una tool, la docstring es la sospechosa.
· Devuelve un `dict` serializable a JSON. Nunca un DataFrame, nunca un objeto.
· El caso "sin resultados" devuelve estructura vacía con un campo `mensaje`,
  NUNCA una excepción. Un agente sabe recuperarse de "no encontré datos"; no sabe
  recuperarse de un stack trace.
· Máximo `LIMITE_FILAS` filas por respuesta, con `truncado: bool`. Volcar 2.000
  filas al contexto es el error clásico.
· Ninguna escribe en la base: la conexión es de solo lectura.
"""

from __future__ import annotations

import statistics
from datetime import datetime, time, timedelta
from typing import Any

from backend.config import config
from backend.db import (
    consulta_directa,
    plantas_conocidas,
    resolver_materia,
    resolver_planta,
    una,
)
from backend.db.constantes import ESTADO_EXCEPCION, FLUJO_PEDIDO

LIMITE_FILAS = 50

# Hora en que abre el muelle. Es el momento de referencia de `eta_estimada`: usar
# la hora real del reloj haría que la misma pregunta diera una respuesta distinta
# cada minuto, rompiendo el caché y el determinismo de la demo.
HORA_APERTURA_MUELLE = 6


def _truncar(filas: list[Any]) -> tuple[list[Any], bool]:
    return filas[:LIMITE_FILAS], len(filas) > LIMITE_FILAS


def _sin_planta(texto: str) -> dict:
    return {
        "encontrado": False,
        "mensaje": (
            f"No encontré ninguna planta que coincida con '{texto}'. "
            f"Las plantas disponibles son: {plantas_conocidas()}."
        ),
    }


def _pendiente(puntos: list[tuple[float, float]]) -> float:
    """Pendiente de una regresión lineal simple. 0.0 si no se puede calcular."""
    n = len(puntos)
    if n < 2:
        return 0.0
    media_x = sum(p[0] for p in puntos) / n
    media_y = sum(p[1] for p in puntos) / n
    num = sum((x - media_x) * (y - media_y) for x, y in puntos)
    den = sum((x - media_x) ** 2 for x, _ in puntos)
    return num / den if den else 0.0


# ---------------------------------------------------------------------------
#  1 · Inventario
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
    p = resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    corte = una(
        "SELECT MAX(fecha_corte) AS f FROM inventario_planta WHERE planta_id = ?",
        (p["id"],),
    )
    fecha_corte = corte["f"] if corte else None
    if not fecha_corte:
        return {
            "planta": p["nombre"],
            "fecha_corte": None,
            "items": [],
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
        m = resolver_materia(materia_prima)
        if not m:
            disponibles = ", ".join(
                f["nombre"] for f in consulta_directa("SELECT nombre FROM materias_primas")
            )
            return {
                "planta": p["nombre"],
                "fecha_corte": fecha_corte,
                "items": [],
                "truncado": False,
                "mensaje": (
                    f"No encontré la materia prima '{materia_prima}'. "
                    f"Las disponibles son: {disponibles}."
                ),
            }
        sql += " AND m.id = ?"
        params.append(m["id"])

    filas = consulta_directa(sql + " ORDER BY m.nombre", tuple(params))
    items = [
        {
            "materia_prima": f["nombre"],
            "codigo": f["id"],
            "cantidad_ton": round(f["cantidad_ton"], 1),
            "stock_minimo_ton": round(f["stock_minimo_ton"], 1),
            "bajo_minimo": f["cantidad_ton"] < f["stock_minimo_ton"],
            "dias_lead_time": f["dias_lead_time"],
        }
        for f in filas
    ]
    items, truncado = _truncar(items)
    salida = {
        "planta": p["nombre"],
        "fecha_corte": fecha_corte,
        "items": items,
        "truncado": truncado,
    }
    if not items:
        salida["mensaje"] = "No hay inventario registrado para ese criterio."
    return salida


# ---------------------------------------------------------------------------
#  2 · Demanda
# ---------------------------------------------------------------------------


def consultar_demanda(
    planta: str,
    dias: int = 7,
    producto: str | None = None,
    materia_prima: str | None = None,
) -> dict:
    """Consulta la demanda de producto terminado de una planta en los últimos días.

    Devuelve el total en toneladas del período, el promedio diario y la serie por
    día. La demanda es HISTÓRICA (los últimos `dias` días registrados) y se usa
    como referencia de lo que se espera para un período equivalente; no es un
    pronóstico calculado.

    IMPORTANTE — unidades: el total viene en toneladas de PRODUCTO TERMINADO. Si
    necesitas compararlo contra el inventario de una materia prima, pasa el
    parámetro `materia_prima`: la herramienta convierte la demanda a toneladas de
    esa materia prima usando su participación en la fórmula de cada producto, y
    devuelve el resultado en `requerimiento_materia_prima`. No hagas esa
    conversión por tu cuenta.

    Args:
        planta: Nombre, municipio o código de la planta.
        dias: Cuántos días hacia atrás incluir. Por defecto 7 (una semana).
        producto: Opcional. Un producto concreto. Si se omite, suma todos.
        materia_prima: Opcional. Si se indica, añade cuántas toneladas de esa
            materia prima requiere la demanda del período, según fórmula.
    """
    p = resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    dias = max(1, min(int(dias), 365))
    corte = una("SELECT MAX(fecha) AS f FROM demanda_historica WHERE planta_id = ?", (p["id"],))
    ultima = corte["f"] if corte else None
    if not ultima:
        return {
            "planta": p["nombre"],
            "periodo": None,
            "total_ton": 0.0,
            "serie": [],
            "truncado": False,
            "mensaje": f"No hay demanda registrada para {p['nombre']}.",
        }

    sql = """SELECT fecha, producto, toneladas FROM demanda_historica
              WHERE planta_id = ? AND fecha > date(?, ?)"""
    params: list[Any] = [p["id"], ultima, f"-{dias} day"]
    if producto:
        sql += " AND producto LIKE ?"
        params.append(f"%{producto}%")
    filas = consulta_directa(sql + " ORDER BY fecha", tuple(params))

    if not filas:
        return {
            "planta": p["nombre"],
            "periodo": None,
            "total_ton": 0.0,
            "serie": [],
            "truncado": False,
            "mensaje": (
                f"No hay demanda registrada para ese criterio en {p['nombre']}. "
                f"El último registro disponible es del {ultima}."
            ),
        }

    por_dia: dict[str, float] = {}
    for f in filas:
        por_dia[f["fecha"]] = por_dia.get(f["fecha"], 0.0) + f["toneladas"]
    total = round(sum(por_dia.values()), 1)
    serie_completa = [
        {"fecha": k, "toneladas": round(v, 1)} for k, v in sorted(por_dia.items())
    ]
    serie, truncado = _truncar(serie_completa)

    salida: dict[str, Any] = {
        "planta": p["nombre"],
        "periodo": {
            "desde": serie_completa[0]["fecha"],
            "hasta": serie_completa[-1]["fecha"],
            "dias": len(serie_completa),
        },
        "producto": producto or "todos",
        "total_ton": total,
        "promedio_dia_ton": round(total / len(serie_completa), 1),
        "serie": serie,
        "truncado": truncado,
    }

    if materia_prima:
        m = resolver_materia(materia_prima)
        if not m:
            salida["requerimiento_materia_prima"] = {
                "encontrado": False,
                "mensaje": f"No encontré la materia prima '{materia_prima}'.",
            }
        else:
            # La conversión la hace la tool, no el modelo: la fórmula está en la
            # base y así el número queda auditable (spec 04, `tendencia`).
            req = 0.0
            detalle = []
            formula = {
                f["producto"]: f["inclusion_pct"]
                for f in consulta_directa(
                    "SELECT producto, inclusion_pct FROM formulas WHERE materia_prima_id = ?",
                    (m["id"],),
                )
            }
            por_producto: dict[str, float] = {}
            for f in filas:
                por_producto[f["producto"]] = (
                    por_producto.get(f["producto"], 0.0) + f["toneladas"]
                )
            for prod, ton in sorted(por_producto.items()):
                pct = formula.get(prod, 0.0)
                aporte = ton * pct / 100.0
                req += aporte
                detalle.append(
                    {
                        "producto": prod,
                        "demanda_ton": round(ton, 1),
                        "inclusion_pct": pct,
                        "requiere_ton": round(aporte, 1),
                    }
                )
            salida["requerimiento_materia_prima"] = {
                "materia_prima": m["nombre"],
                "codigo": m["id"],
                "toneladas_requeridas": round(req, 1),
                "dias_lead_time": m["dias_lead_time"],
                "detalle_por_producto": detalle,
            }
    return salida


# ---------------------------------------------------------------------------
#  3 · Producción
# ---------------------------------------------------------------------------


def consultar_produccion(planta: str, dias: int = 7) -> dict:
    """Consulta la producción real de una planta en los últimos días.

    Devuelve el total producido en toneladas, los minutos de parada acumulados, el
    porcentaje de utilización de la capacidad instalada y la serie por día.

    Úsala para comparar lo que la planta PRODUJO contra lo que se le DEMANDÓ
    (`consultar_demanda`) y detectar días en que la producción no alcanzó.

    Args:
        planta: Nombre, municipio o código de la planta.
        dias: Cuántos días hacia atrás incluir. Por defecto 7.
    """
    p = resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    dias = max(1, min(int(dias), 365))
    corte = una("SELECT MAX(fecha) AS f FROM produccion_diaria WHERE planta_id = ?", (p["id"],))
    ultima = corte["f"] if corte else None
    if not ultima:
        return {
            "planta": p["nombre"],
            "periodo": None,
            "total_ton": 0.0,
            "serie": [],
            "truncado": False,
            "mensaje": f"No hay producción registrada para {p['nombre']}.",
        }

    filas = consulta_directa(
        """SELECT pr.fecha, pr.toneladas, pr.paradas_min,
                  (SELECT SUM(d.toneladas) FROM demanda_historica d
                    WHERE d.planta_id = pr.planta_id AND d.fecha = pr.fecha) AS demanda_ton
             FROM produccion_diaria pr
            WHERE pr.planta_id = ? AND pr.fecha > date(?, ?)
            ORDER BY pr.fecha""",
        (p["id"], ultima, f"-{dias} day"),
    )
    total = round(sum(f["toneladas"] for f in filas), 1)
    paradas = sum(f["paradas_min"] for f in filas)
    capacidad_periodo = p["capacidad_ton_dia"] * len(filas)
    serie_completa = [
        {
            "fecha": f["fecha"],
            "toneladas": round(f["toneladas"], 1),
            "paradas_min": f["paradas_min"],
            "demanda_ton": round(f["demanda_ton"] or 0.0, 1),
            "cubrio_demanda": f["toneladas"] >= (f["demanda_ton"] or 0.0),
        }
        for f in filas
    ]
    serie, truncado = _truncar(serie_completa)
    dias_cortos = [s["fecha"] for s in serie_completa if not s["cubrio_demanda"]]
    return {
        "planta": p["nombre"],
        "periodo": {
            "desde": serie_completa[0]["fecha"] if serie_completa else None,
            "hasta": serie_completa[-1]["fecha"] if serie_completa else None,
            "dias": len(serie_completa),
        },
        "total_ton": total,
        "paradas_min": paradas,
        "capacidad_ton_dia": p["capacidad_ton_dia"],
        "utilizacion_pct": round(100 * total / capacidad_periodo, 1)
        if capacidad_periodo
        else None,
        "dias_sin_cubrir_demanda": dias_cortos,
        "serie": serie,
        "truncado": truncado,
    }


# ---------------------------------------------------------------------------
#  4 · Estado de un pedido
# ---------------------------------------------------------------------------


def _tiempo_medio_cargue(planta_id: str) -> tuple[float | None, int]:
    """Mediana de (hora_cargue_real − hora_asignada) en minutos, y cuántos casos.

    Spec 04: con menos de 5 despachos cerrados no hay base para la mediana y
    `eta_estimada` devuelve null. Devolver null es correcto; devolver una cifra
    sin sustento no.
    """
    filas = consulta_directa(
        """SELECT d.hora_asignada, d.hora_cargue_real
             FROM despachos d
             JOIN pedidos p ON p.numero = d.pedido_numero
            WHERE p.planta_id = ?
              AND d.hora_cargue_real IS NOT NULL
              AND d.hora_asignada IS NOT NULL""",
        (planta_id,),
    )
    minutos = []
    for f in filas:
        try:
            a = datetime.fromisoformat(f["hora_asignada"])
            r = datetime.fromisoformat(f["hora_cargue_real"])
        except (TypeError, ValueError):
            continue
        delta = (r - a).total_seconds() / 60
        if delta >= 0:
            minutos.append(delta)
    if len(minutos) < 5:
        return None, len(minutos)
    return round(statistics.median(minutos), 1), len(minutos)


def estado_pedido(numero: str) -> dict:
    """Consulta en qué punto del proceso logístico está un pedido.

    Devuelve el estado actual, cuántos pasos le faltan para ser entregado, su
    turno de muelle, cuántos camiones tiene delante en la cola y una fecha
    estimada de cargue.

    Sobre `eta_estimada`: se calcula como
        max(fecha_promesa, momento_referencia + posicion_en_cola × tiempo_medio_cargue)
    donde `tiempo_medio_cargue` es la mediana de lo que tardaron los cargues ya
    cerrados de esa planta. El campo `base_calculo` trae los insumos para que
    puedas explicar de dónde sale. Si no hay al menos 5 cargues cerrados,
    `eta_estimada` es null: en ese caso di que no hay base para estimarla, NO
    inventes una fecha.

    Args:
        numero: Número del pedido, por ejemplo 'PD-24-00871'.
    """
    numero = (numero or "").strip().upper()
    ped = una(
        """SELECT p.*, pl.nombre AS planta_nombre, pl.municipio
             FROM pedidos p JOIN plantas pl ON pl.id = p.planta_id
            WHERE UPPER(p.numero) = ?""",
        (numero,),
    )
    if not ped:
        ejemplo = una("SELECT numero FROM pedidos ORDER BY numero LIMIT 1")
        return {
            "encontrado": False,
            "mensaje": (
                f"No encontré el pedido '{numero}'. Los números tienen la forma "
                f"PD-24-00XXX (por ejemplo {ejemplo['numero'] if ejemplo else 'PD-24-00801'})."
            ),
        }

    estado = ped["estado"]
    if estado == ESTADO_EXCEPCION:
        pasos_restantes = None
    elif estado in FLUJO_PEDIDO:
        pasos_restantes = len(FLUJO_PEDIDO) - 1 - FLUJO_PEDIDO.index(estado)
    else:
        pasos_restantes = None

    desp = una(
        """SELECT * FROM despachos WHERE pedido_numero = ?
            ORDER BY (hora_cargue_real IS NULL) DESC, hora_asignada DESC LIMIT 1""",
        (ped["numero"],),
    )
    turno = desp["turno_muelle"] if desp else None
    posicion = None
    if desp and desp["estado"] == "en_espera" and turno is not None:
        delante = consulta_directa(
            """SELECT COUNT(*) AS n FROM despachos d
                 JOIN pedidos p ON p.numero = d.pedido_numero
                WHERE p.planta_id = ? AND d.estado = 'en_espera'
                  AND d.turno_muelle < ?""",
            (ped["planta_id"], turno),
        )[0]["n"]
        posicion = delante + 1

    medio, n_cierres = _tiempo_medio_cargue(ped["planta_id"])
    momento = datetime.combine(config.fecha_base, time(HORA_APERTURA_MUELLE, 0))
    eta = None
    base: dict[str, Any] = {
        "posicion_en_cola": posicion,
        "tiempo_medio_cargue_min": medio,
        "despachos_cerrados_considerados": n_cierres,
        "momento_referencia": momento.isoformat(sep=" ", timespec="minutes"),
    }
    if medio is None:
        base["motivo"] = (
            f"Solo hay {n_cierres} despachos cerrados en esta planta; se necesitan "
            "al menos 5 para calcular la mediana de tiempo de cargue. Sin esa base "
            "no se estima una fecha."
        )
    elif posicion is None:
        base["motivo"] = (
            "El pedido no está en la cola de muelle, así que no aplica una "
            "estimación por turnos."
        )
    else:
        promesa = datetime.fromisoformat(ped["fecha_promesa"] + " 23:59")
        estimado = momento + timedelta(minutes=posicion * medio)
        eta = max(promesa, estimado).isoformat(sep=" ", timespec="minutes")
        base["formula"] = (
            "max(fecha_promesa, momento_referencia + "
            f"{posicion} × {medio} min)"
        )

    return {
        "numero": ped["numero"],
        "cliente": ped["cliente"],
        "planta": ped["planta_nombre"],
        "municipio": ped["municipio"],
        "producto": ped["producto"],
        "toneladas": round(ped["toneladas"], 1),
        "estado": estado,
        "flujo_completo": FLUJO_PEDIDO,
        "pasos_restantes": pasos_restantes,
        "turno_muelle": turno,
        "posicion_en_cola": posicion,
        "placa": desp["placa"] if desp else None,
        "hora_asignada": desp["hora_asignada"] if desp else None,
        "fecha_pedido": ped["fecha_pedido"],
        "fecha_promesa": ped["fecha_promesa"],
        "eta_estimada": eta,
        "base_calculo": base,
    }


# ---------------------------------------------------------------------------
#  5 · Turnos de muelle
# ---------------------------------------------------------------------------


def turnos_muelle(planta: str, fecha: str | None = None) -> dict:
    """Consulta la cola de camiones en el muelle de una planta.

    Devuelve los turnos en orden, con el pedido, la placa, la hora asignada y si
    ya cargó o sigue esperando. Úsala para explicar por qué un pedido no avanza:
    un pedido en muelle con varios camiones delante está esperando turno, no
    detenido por un problema de producción.

    Args:
        planta: Nombre, municipio o código de la planta.
        fecha: Opcional, formato YYYY-MM-DD. Si se omite, usa la cola vigente
            (los turnos que aún están en espera).
    """
    p = resolver_planta(planta)
    if not p:
        return _sin_planta(planta)

    sql = """SELECT d.turno_muelle, d.pedido_numero, d.placa, d.hora_asignada,
                    d.hora_cargue_real, d.estado, pe.cliente, pe.toneladas
               FROM despachos d
               JOIN pedidos pe ON pe.numero = d.pedido_numero
              WHERE pe.planta_id = ?"""
    params: list[Any] = [p["id"]]
    if fecha:
        sql += " AND date(d.hora_asignada) = ?"
        params.append(fecha)
    else:
        sql += " AND d.estado = 'en_espera'"
    filas = consulta_directa(sql + " ORDER BY d.turno_muelle", tuple(params))

    cola = [
        {
            "turno": f["turno_muelle"],
            "pedido": f["pedido_numero"],
            "cliente": f["cliente"],
            "toneladas": round(f["toneladas"], 1),
            "placa": f["placa"],
            "hora_asignada": f["hora_asignada"],
            "estado": f["estado"],
            "ya_cargo": f["hora_cargue_real"] is not None,
        }
        for f in filas
    ]
    cola, truncado = _truncar(cola)
    salida = {
        "planta": p["nombre"],
        "fecha": fecha or "cola vigente",
        "cola": cola,
        "en_cola": len([c for c in cola if not c["ya_cargo"]]),
        "truncado": truncado,
    }
    if not cola:
        salida["mensaje"] = (
            f"No hay camiones en cola en {p['nombre']}"
            + (f" para el {fecha}." if fecha else ".")
        )
    return salida


# ---------------------------------------------------------------------------
#  6 · Historial de fallas
# ---------------------------------------------------------------------------


def historial_fallas(
    equipo_id: str | None = None, planta: str | None = None, dias: int = 90
) -> dict:
    """Consulta las órdenes de mantenimiento de un equipo o de una planta.

    Devuelve las órdenes del período con su tipo (correctivo, preventivo,
    predictivo), la causa, las horas de paro y el costo. Incluye el MTBF (tiempo
    medio entre fallas, en días) calculado sobre los correctivos.

    Para detectar un equipo en riesgo, mira la repetición de CORRECTIVOS con la
    misma causa en poco tiempo. Combínala con `lecturas_sensor` para confirmar si
    hay una variable en ascenso.

    Args:
        equipo_id: Opcional. Código del equipo, por ejemplo 'EQ-ITG-MOL-01'.
        planta: Opcional. Nombre, municipio o código de la planta; devuelve todos
            sus equipos. Si se indican los dos, manda `equipo_id`.
        dias: Ventana hacia atrás en días. Por defecto 90.
    """
    dias = max(1, min(int(dias), 730))
    sql = """SELECT o.id, o.equipo_id, e.tipo AS tipo_equipo, e.criticidad,
                    pl.nombre AS planta, o.fecha_apertura, o.fecha_cierre,
                    o.tipo, o.causa, o.horas_paro, o.costo_cop
               FROM ordenes_mantenimiento o
               JOIN equipos e ON e.id = o.equipo_id
               JOIN plantas pl ON pl.id = e.planta_id
              WHERE o.fecha_apertura > date(?, ?)"""
    params: list[Any] = [config.fecha_base.isoformat(), f"-{dias} day"]

    if equipo_id:
        codigo = equipo_id.strip().upper()
        if not una("SELECT 1 FROM equipos WHERE UPPER(id) = ?", (codigo,)):
            equipos = ", ".join(
                f["id"] for f in consulta_directa("SELECT id FROM equipos ORDER BY id LIMIT 20")
            )
            return {
                "alcance": codigo,
                "ordenes": [],
                "total": 0,
                "truncado": False,
                "mensaje": f"No existe el equipo '{codigo}'. Algunos equipos: {equipos}.",
            }
        sql += " AND UPPER(o.equipo_id) = ?"
        params.append(codigo)
        alcance = f"equipo {codigo}"
    elif planta:
        p = resolver_planta(planta)
        if not p:
            return _sin_planta(planta)
        sql += " AND e.planta_id = ?"
        params.append(p["id"])
        alcance = f"planta {p['nombre']}"
    else:
        alcance = "todas las plantas"

    filas = consulta_directa(sql + " ORDER BY o.fecha_apertura DESC", tuple(params))
    if not filas:
        return {
            "alcance": alcance,
            "periodo_dias": dias,
            "ordenes": [],
            "total": 0,
            "horas_paro_total": 0.0,
            "mtbf_dias": None,
            "truncado": False,
            "mensaje": f"No hay órdenes de mantenimiento en {alcance} en los últimos {dias} días.",
        }

    correctivos = sorted(
        [f["fecha_apertura"] for f in filas if f["tipo"] == "correctivo"]
    )
    mtbf = None
    if len(correctivos) >= 2:
        fechas = [datetime.fromisoformat(c) for c in correctivos]
        intervalos = [
            (b - a).days for a, b in zip(fechas, fechas[1:]) if (b - a).days >= 0
        ]
        if intervalos:
            mtbf = round(sum(intervalos) / len(intervalos), 1)

    # Causa que más se repite entre los correctivos: es la señal del patrón.
    causas: dict[str, int] = {}
    for f in filas:
        if f["tipo"] == "correctivo" and f["causa"]:
            causas[f["causa"]] = causas.get(f["causa"], 0) + 1
    causa_repetida = max(causas.items(), key=lambda kv: kv[1]) if causas else None

    ordenes_completas = [
        {
            "id": f["id"],
            "equipo_id": f["equipo_id"],
            "tipo_equipo": f["tipo_equipo"],
            "criticidad": f["criticidad"],
            "planta": f["planta"],
            "fecha_apertura": f["fecha_apertura"],
            "fecha_cierre": f["fecha_cierre"],
            "tipo": f["tipo"],
            "causa": f["causa"],
            "horas_paro": round(f["horas_paro"], 1),
            "costo_cop": int(f["costo_cop"]),
        }
        for f in filas
    ]
    ordenes, truncado = _truncar(ordenes_completas)
    return {
        "alcance": alcance,
        "periodo_dias": dias,
        "ordenes": ordenes,
        "total": len(ordenes_completas),
        "correctivos": len(correctivos),
        "horas_paro_total": round(sum(f["horas_paro"] for f in filas), 1),
        "costo_total_cop": int(sum(f["costo_cop"] for f in filas)),
        "mtbf_dias": mtbf,
        "causa_mas_repetida": (
            {"causa": causa_repetida[0], "veces": causa_repetida[1]}
            if causa_repetida
            else None
        ),
        "truncado": truncado,
    }


# ---------------------------------------------------------------------------
#  7 · Lecturas de sensor
# ---------------------------------------------------------------------------


def lecturas_sensor(equipo_id: str, variable: str, horas: int = 168) -> dict:
    """Consulta las lecturas de un sensor de un equipo y su tendencia.

    Variables disponibles: 'vibracion_mm_s', 'temperatura_c', 'amperaje_a'.

    Devuelve mínimo, máximo, promedio y `tendencia`, que trae la pendiente de una
    regresión lineal por día y su dirección (creciente, estable o decreciente).

    La tendencia se calcula sobre TODAS las lecturas del período, no solo sobre
    las que se devuelven en `serie` — `n_puntos` te dice cuántas entraron al
    cálculo. Confía en `tendencia` y no la recalcules a mano sobre `serie`.

    Una vibración creciente y sostenida en un equipo con correctivos repetidos es
    la señal clásica de una falla en desarrollo.

    Args:
        equipo_id: Código del equipo, por ejemplo 'EQ-ITG-MOL-01'.
        variable: Nombre de la variable a consultar.
        horas: Ventana hacia atrás en horas. Por defecto 168 (7 días).
    """
    codigo = (equipo_id or "").strip().upper()
    eq = una("SELECT * FROM equipos WHERE UPPER(id) = ?", (codigo,))
    if not eq:
        equipos = ", ".join(
            f["id"] for f in consulta_directa("SELECT id FROM equipos ORDER BY id LIMIT 20")
        )
        return {
            "equipo_id": codigo,
            "serie": [],
            "n_lecturas": 0,
            "truncado": False,
            "mensaje": f"No existe el equipo '{codigo}'. Algunos equipos: {equipos}.",
        }

    disponibles = [
        f["variable"]
        for f in consulta_directa(
            "SELECT DISTINCT variable FROM lecturas_sensor WHERE equipo_id = ?", (codigo,)
        )
    ]
    if variable not in disponibles:
        return {
            "equipo_id": codigo,
            "variable": variable,
            "serie": [],
            "n_lecturas": 0,
            "truncado": False,
            "mensaje": (
                f"El equipo {codigo} no tiene lecturas de '{variable}'. "
                f"Variables disponibles: {', '.join(disponibles)}."
            ),
        }

    horas = max(1, min(int(horas), 24 * 400))
    ultima = una(
        "SELECT MAX(ts) AS t FROM lecturas_sensor WHERE equipo_id = ? AND variable = ?",
        (codigo, variable),
    )["t"]
    filas = consulta_directa(
        """SELECT ts, valor FROM lecturas_sensor
            WHERE equipo_id = ? AND variable = ?
              AND ts > datetime(?, ?)
            ORDER BY ts""",
        (codigo, variable, ultima, f"-{horas} hour"),
    )
    if not filas:
        return {
            "equipo_id": codigo,
            "variable": variable,
            "serie": [],
            "n_lecturas": 0,
            "truncado": False,
            "mensaje": f"No hay lecturas de '{variable}' en las últimas {horas} horas.",
        }

    valores = [f["valor"] for f in filas]
    t0 = datetime.fromisoformat(filas[0]["ts"])
    puntos = [
        ((datetime.fromisoformat(f["ts"]) - t0).total_seconds() / 86400.0, f["valor"])
        for f in filas
    ]
    pendiente = _pendiente(puntos)
    promedio = sum(valores) / len(valores)
    dias_periodo = max(puntos[-1][0], 1e-9)
    cambio_total = abs(pendiente * dias_periodo)
    # Estable si el cambio acumulado del período no llega al 5% del promedio.
    # Es un umbral explícito y explicable, no un juicio del modelo.
    if promedio and cambio_total < 0.05 * abs(promedio):
        direccion = "estable"
    elif pendiente > 0:
        direccion = "creciente"
    elif pendiente < 0:
        direccion = "decreciente"
    else:
        direccion = "estable"

    unidades = {"vibracion_mm_s": "mm/s", "temperatura_c": "°C", "amperaje_a": "A"}
    serie_completa = [{"ts": f["ts"], "valor": f["valor"]} for f in filas]
    serie, truncado = _truncar(serie_completa)

    return {
        "equipo_id": codigo,
        "equipo_tipo": eq["tipo"],
        "criticidad": eq["criticidad"],
        "variable": variable,
        "periodo_horas": horas,
        "n_lecturas": len(filas),
        "minimo": round(min(valores), 2),
        "maximo": round(max(valores), 2),
        "promedio": round(promedio, 2),
        "tendencia": {
            "pendiente": round(pendiente, 4),
            "unidad": f"{unidades.get(variable, '')} por día".strip(),
            "direccion": direccion,
            "n_puntos": len(puntos),
        },
        "serie": serie,
        "truncado": truncado,
    }


# ---------------------------------------------------------------------------
#  Registro
# ---------------------------------------------------------------------------

TODAS = [
    consultar_inventario,
    consultar_demanda,
    consultar_produccion,
    estado_pedido,
    turnos_muelle,
    historial_fallas,
    lecturas_sensor,
]

POR_NOMBRE = {f.__name__: f for f in TODAS}

# Subconjuntos de los dos sub-agentes de N5 (spec 05). La separación no es
# decorativa: es la que justifica el multiagente. Si los dos vieran las siete
# tools, no habría especialización que mostrar.
TOOLS_ABASTECIMIENTO = [consultar_inventario, consultar_demanda, consultar_produccion]
TOOLS_OPERACIONES = [historial_fallas, lecturas_sensor, estado_pedido, turnos_muelle]


def firmas() -> list[dict]:
    """Nombre, parámetros y docstring de cada tool, tal como la ve el modelo.

    Lo consume `GET /api/niveles` y el panel de tools del tablero, que refuerza la
    lección: la docstring es el prompt.
    """
    import inspect

    salida = []
    for f in TODAS:
        sig = inspect.signature(f)
        salida.append(
            {
                "nombre": f.__name__,
                "firma": f"{f.__name__}{sig}",
                "docstring": inspect.getdoc(f) or "",
            }
        )
    return salida
