#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────
#  scripts/generar_corpus.py
#  Clase 3 · RAG — Generador del corpus sintético de Grupo Bios.
#
#  Produce `app/data/corpus.json` con ~15-20 documentos en español del agro
#  colombiano, agrupados en 4 familias por dominio Champion (Mantenimiento,
#  Compras, Logística, Producción/TD). Planta 3 anomalías documentales
#  (RAG-1, RAG-2, RAG-3) en pasajes específicos, para que el retrieval
#  las encuentre en las preguntas semilla de la clase.
#
#  Ver spec 03 § "El corpus sintético" y § "Las tres anomalías documentales".
#
#  Es determinista: con semilla fija (42), el corpus es byte-idéntico en
#  todas las máquinas. El texto es literal en este script — no usa LLM.
#
#  Uso:
#      python scripts/generar_corpus.py
#      python scripts/generar_corpus.py --salida app/data/corpus.json
#      python scripts/generar_corpus.py --verificar     # solo-thresholds, no
#                                                     # escribe archivo
# ──────────────────────────────────────────────────────────────────────────
"""Genera el corpus sintético de la Clase 3."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date
from pathlib import Path
from typing import Any

SEMILLA = 42

# Identificadores del negocio que también viven en bios_ops.db (S1, S2).
# No se inventan aquí: se referencian textualmente en el corpus para que
# las preguntas de la demo puedan mezclar corpus + tools de S2.
PLANTA_ITG = "Itagüí"           # PL-ITG
EQUIPO_MOLINO = "EQ-ITG-MOL-01" # molino de Itagüí, criticidad alta
PEDIDO_ATASCADO = "PD-24-00871" # estado en_muelle, cola 6


# ──────────────────────────────────────────────────────────────────────────
#  Documentos por familia.
#
#  Cada documento es un dict con:
#    id, titulo, parrafos (lista de strings), anomalias_plantadas
#
#  El campo `anomalias_plantadas` indica qué IDs RAG-N se insertaron en
#  este documento y en qué párrafo (índice 0-based). Lo usa el pre-bakeo
#  para verificar y lo usa el frontend para mostrar el chip "ANOMALÍA
#  PLANTADA" en la pantalla 6.
# ──────────────────────────────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════
#  FAMILIA · MANTENIMIENTO
# ═══════════════════════════════════════════════════════════════════════════
FAMILIA_MANT = {
    "id": "mant",
    "dominio": "Mantenimiento",
    "documentos": [
        {
            "id": "mant_manual_preventivo",
            "titulo": "Manual de mantenimiento preventivo de planta",
            "parrafos": [
                "El mantenimiento preventivo de la planta es responsabilidad de "
                "la Coordinación de Mantenimiento. Toda intervención programada "
                "se documenta en la orden de mantenimiento correspondiente y "
                "se archiva por planta y por equipo. La periodicidad se define "
                "según criticidad del equipo: alta (mensual), media (trimestral), "
                "baja (semestral).",

                "La planta de Itagüí concentra la mayor criticidad de la red. "
                "Allí el molino " + EQUIPO_MOLINO + " operación continua y "
                "demanda inspección semanal de rodamientos, alineación de ejes "
                "y hermeticidad del sistema de lubricación. El técnico de "
                "turno registra la inspección en la APP de mantenimiento; el "
                "registro digital es la fuente de verdad, no la libreta de "
                "papel del turno.",

                "El lubricante se reemplaza cada 500 horas de operación o "
                "cuando el sensor de degradación reporta índice de acidez "
                "fuera de rango. La reposición de rodamientos se programa solo "
                "cuando el análisis de vibración muestra componentes en "
                "frecuencia de falla dominante. No se cambia pieza por "
                "calendario, se cambia por condición."
            ]
        },
        {
            "id": "mant_politica_criticidad",
            "titulo": "Política de criticidad de equipos",
            "parrafos": [
                "Todo equipo de la red se clasifica en tres niveles de "
                "criticidad: alta, media y baja. La criticidad refleja el "
                "impacto operativo de una falla y la complejidad de su "
                "reemplazo. La clasificación la hace el Líder de "
                "Mantenimiento junto con el Director de Planta y se revisa "
                "anualmente.",

                "Los equipos de criticidad alta requieren inspección "
                "semanal, plan de contingencia documentado, repuesto crítico "
                "en bodega y monitoreo en línea de, al menos, dos variables "
                "de operación (vibración y temperatura, por ejemplo). El "
                "molino de la planta " + PLANTA_ITG + " es el caso típico de "
                "criticidad alta.",

                "La criticidad media admite inspección trimestral y "
                "reemplazo programado por ventana. La baja permite "
                "intervención correctiva: si falla, se repara, sin "
                "necesidad de plan de contingencia previo."
            ]
        },
        {
            "id": "mant_guia_sensor",
            "titulo": "Guía de interpretación de lecturas de sensor",
            "parrafos": [
                "Los sensores de vibración en molinos se configuran para "
                "reportar velocidad efectiva en milímetros por segundo "
                "(mm/s) en el eje radial. El umbral normal está en 0.0–3.5 "
                "mm/s. La alerta amarilla dispara entre 3.5 y 5.5 mm/s; la "
                "alerta roja dispara por encima de 5.5 mm/s.",

                # ▣ ANOMALÍA RAG-1: procedimiento cuando el molino supera
                #    5.5 mm/s por más de 2 turnos.
                "Cuando el molino supera el umbral de vibración de 5.5 mm/s "
                "durante más de 2 turnos consecutivos, el turno de "
                "mantenimiento debe detener el lote en curso, aislar el "
                "equipo de la línea, notificar al Coordinador de "
                "Mantenimiento con copia al Director de Planta, y abrir "
                "una orden de mantenimiento de tipo 'urgente'. El lote "
                "detenido se reagendariza en el siguiente turno disponible "
                "con prioridad alta.",

                "La lectura de temperatura del rodamiento se interpreta en "
                "combinación con la vibración. Temperatura sobre 78 °C con "
                "vibración en rango amarillo sugiere lubricación degradada. "
                "Temperatura sobre 78 °C con vibración en rango rojo sugiere "
                "daño de rodamiento y exige parada inmediata, no solo "
                "inspección."
            ],
            "anomalias_plantadas": [{"id": "RAG-1", "parrafo_idx": 1}]
        }
    ]
}


# ═══════════════════════════════════════════════════════════════════════════
#  FAMILIA · COMPRAS
# ═══════════════════════════════════════════════════════════════════════════
FAMILIA_COMP = {
    "id": "comp",
    "dominio": "Compras",
    "documentos": [
        {
            "id": "comp_politica_abastecimiento",
            "titulo": "Política de abastecimiento de materias primas",
            "parrafos": [
                "El abastecimiento de materias primas a las plantas se "
                "rige por dos principios: cobertura mínima por planta y "
                "priorización por criticidad operativa. La cobertura mínima "
                "se calcula como el stock suficiente para 7 días de "
                "operación a demanda proyectada.",

                "El reorden se dispara automáticamente cuando el inventario "
                "de una materia prima cae por debajo de su mínimo. El "
                "mínimo lo define el área de Compras con el área de "
                "Producción y se revisa trimestralmente. El sistema emite "
                "una alerta al coordinador de planta y al analista de "
                "Compras.",

                # ▣ ANOMALÍA RAG-2: procedimiento cuando una planta de
                #    criticidad alta declara stock crítico.
                "Todo stock crítico declarado en una planta de criticidad "
                "alta activa una orden de abastecimiento de prioridad 1. "
                "La asignación de proveedor se hace en zona norte con ETA "
                "comprometida de 48 horas. El analista de Compras envía la "
                "orden directamente, sin pasar por la cola de aprobación "
                "general, y deja trazabilidad de la excepción en la "
                "bitácora del Comité de Abastecimiento."
            ],
            "anomalias_plantadas": [{"id": "RAG-2", "parrafo_idx": 2}]
        },
        {
            "id": "comp_manual_volumenes",
            "titulo": "Manual de planeación de volúmenes a plantas",
            "parrafos": [
                "La planeación de volúmenes de materia prima por planta se "
                "actualiza mensualmente. El insumo principal es la "
                "proyección de demanda entregada por el área de "
                "Producción/TD. Cada planta recibe su volumen asignado "
                "según su capacidad de molienda y su consumo histórico.",

                "El buffer de seguridad por materia prima se calcula como "
                "el percentil 90 del consumo histórico de los últimos 12 "
                "meses, multiplicado por el factor de criticidad del "
                "proveedor. Cuando el proveedor es único en zona, el "
                "factor sube a 1.4; cuando hay al menos dos proveedores "
                "activos, el factor baja a 1.1.",

                "El reporte mensual de volúmenes se entrega al cierre del "
                "mes anterior y se revisita en el comité de abastecimiento del "
                "primer miércoles de cada mes. Cualquier ajuste intermedio "
                "se documenta como excepción y se firma por el Director de "
                "Planta receptora."
            ]
        },
        {
            "id": "comp_reglas_inventario_minimo",
            "titulo": "Reglas de inventario mínimo",
            "parrafos": [
                "El inventario mínimo de una materia prima en una planta "
                "es la cantidad por debajo de la cual se considera stock "
                "crítico. El sistema emite alerta al cruzar este umbral "
                "y el coordinador de planta debe accionar el procedimiento "
                "de reabastecimiento.",

                "Las reglas de inventario mínimo se ajustan por estación y "
                "por criticidad de la materia prima. Maíz amarillo y "
                "soya son materias de criticidad alta: el mínimo sube en "
                "temporada de peak de demanda. Harina y aceite son "
                "criticidad media y admiten menor cobertura.",

                "La conciliación entre inventario físico e inventario "
                "sistémico se hace semanalmente. Diferencias mayores al "
                "2% se reportan como discrepancia y se abre investigación "
                "operativa. Las diferencias menores se ajustan con "
                "justificación documentada, sin investigación formal."
            ]
        }
    ]
}


# ═══════════════════════════════════════════════════════════════════════════
#  FAMILIA · LOGÍSTICA
# ═══════════════════════════════════════════════════════════════════════════
FAMILIA_LOGI = {
    "id": "logi",
    "dominio": "Logística",
    "documentos": [
        {
            "id": "logi_manual_despachos",
            "titulo": "Manual de despachos a clientes",
            "parrafos": [
                "Un pedido pasa por cuatro estados en el flujo de "
                "despacho: en_cola, en_muelle, en_ruta y entregado. El "
                "cambio de estado lo hace el operario del muelle en la "
                "APP de Logística. Cada transición queda timestamp; el "
                "SLA por estado se mide desde el último cambio.",

                "El turno de muelle es la unidad de planificación de "
                "despachos. Hay 12 turnos diarios (turnos de 2 horas). "
                "Cuando un pedido queda en estado en_muelle, el sistema "
                "asigna el siguiente turno disponible. Si no hay turno "
                "libre en las próximas 6 horas, el pedido queda en cola "
                "de espera visible para el cliente.",

                # ▣ ANOMALÍA RAG-3: notificación automática cuando un
                #    pedido lleva más de 5 (más de 5 turnos) en estado
                #    en_muelle.
                "Cuando un pedido lleva más de 5 turnos en estado "
                "en_muelle, Logística dispara una notificación automática "
                "al cliente con la razón documentada del retraso y el "
                "nuevo slot estimado de despacho. La notificación es por "
                "canal preferido del cliente (email o SMS) y queda "
                "registrada en el historial del pedido. El servidor que "
                "envía la notificación es el mismo que procesa los "
                "cambios de estado; no hay fila externa."
            ],
            "anomalias_plantadas": [{"id": "RAG-3", "parrafo_idx": 2}]
        },
        {
            "id": "logi_reglas_turnos_muelle",
            "titulo": "Reglas de asignación de turnos de muelle",
            "parrafos": [
                "Los turnos de muelle se asignan por prioridad del pedido. "
                "La prioridad pedidos con cliente clasificado como VIP, "
                "luego pedidos con productos perecederos y finalmente "
                "pedidos estándar. Dentro de la misma prioridad, el "
                "criterio de desempate es hora de ingreso al muelle.",

                "Cuando un turno queda libre por cancelación, el sistema "
                "lo reasigna al primer pedido de la cola de espera con "
                "misma prioridad que el pedido cancelado. Si no existen "
                "pedidos de esa prioridad, se reasigna a la siguiente "
                "prioridad disponible.",

                "Los turnos no usados por error operativo se documentan "
                "como 'turno vacío' y se reportan al cierre del día. La "
                "tasa de turnos vacíos es indicador clave de Logística "
                "y se monitorea diariamente."
            ]
        },
        {
            "id": "logi_politica_notificacion_clientes",
            "titulo": "Política de notificación a clientes",
            "parrafos": [
                "La notificación al cliente se hace en tres momentos "
                "obligatorios: confirmación de pedido, inicio de despacho "
                "y entrega. Adicionalmente, cualquier evento que modifique "
                "el SLA en más de 2 horas con respecto a la promesa "
                "original dispara una notificación de excepción.",

                "Las notificaciones se hacen por canal preferido del "
                "cliente. La bitácora de envíos la mantiene Logística y "
                "es fuente de verdad en caso de reclamo. El cliente puede "
                "consultar el estado de su pedido en el portal de "
                "autoservicio, que consume el mismo sistema de estado.",

                "El tono de las notificaciones es estándar para "
                "todas las plantas y no varía por cliente. Las plantas "
                "tipifican mensajes por evento y los aprueba el área de "
                "Servicio al Cliente antes de publicación."
            ]
        }
    ]
}


# ═══════════════════════════════════════════════════════════════════════════
#  FAMILIA · PRODUCCIÓN / TRANSFORMACIÓN DIGITAL
# ═══════════════════════════════════════════════════════════════════════════
FAMILIA_PROD = {
    "id": "prod",
    "dominio": "Producción / TD",
    "documentos": [
        {
            "id": "prod_procedimiento_planeacion_demanda",
            "titulo": "Procedimiento de planeación de demanda",
            "parrafos": [
                "La planeación de demanda se actualiza mensualmente. El "
                "insumo principal es la proyección estadística generada "
                "por el área de Producción/TD sobre los últimos 24 meses "
                "de ventas. La proyección se ajusta por estacionalidad "
                "conocida del agro colombiano (peak en julio-agosto por "
                "siembra tardía, valle en diciembre por cierre de año).",

                "El Comité de Demanda se reúne el último jueves de cada "
                "mes. En la sesión se aprueba el plan de demanda que rige "
                "el mes siguiente y se documenta cualquier desviación del "
                "plan anterior. Las desviaciones mayores al 10% se "
                "documentan como excepción, con causa raíz y plan "
                "correctivo.",

                "El plan aprobado alimenta el sistema de Producción y "
                "define el calendario de molienda por planta. La "
                "diferencia entre lo planeado y lo producido se reporta "
                "diariamente; acumulada mensual,entra como insumo al "
                "ciclo siguiente."
            ]
        },
        {
            "id": "prod_glosario_indicadores",
            "titulo": "Glosario de indicadores operativos",
            "parrafos": [
                "Eficiencia OEE (Overall Equipment Effectiveness) es el "
                "indicador agregado de desempeño de una línea. Combina "
                "disponibilidad, performance y calidad. Para Grupo Bios, "
                "el OEE objetivo de molienda es 78%, y se reporta por "
                "turno y por planta.",

                "Cumplimiento de plan es la relación entre toneladas "
                "producidas y toneladas planeadas para el período. Se "
                "calcula por día, acumulado por mes. El objetivo mínimo "
                "es 95%; por debajo se considera falla de planeación.",
                
                "Tasa de turnos vacíos (Logística) es el indicador que "
                "mide la subutilización de muelles. Es lo que Logística "
                "reporta al cierre diario.胱si lasplanta tiene promedio "
                "menor al 5% en el mes, no se reporta al siguiente nivel.",

                "Tiempo de ciclo de pedido es el indicador de "
                "satisfacción al cliente. Se mide desde el ingreso del "
                "pedido hasta la entrega. El objetivo es menor a 48 "
                "horas en el promedio mensual por planta."
            ]
        },
        {
            "id": "prod_instructivo_conexion_demanda_produccion",
            "titulo": "Instructivo de conexión demanda ↔ producción",
            "parrafos": [
                "La conexión entre el plan de demanda y el calendario de "
                "producción se hace mediante el tablero de planeación "
                "operativa. El tablero consume el plan aprobado por "
                "Comité de Demanda y lo traduce en órdenes de molienda "
                "por planta.",

                "Cuando el plan cambia en sesión intermedia, se abre "
                "una excepción con causa documentada. La excepción "
                "permite ajustar el calendario hasta el siguiente "
                "Comité. Toda excepción queda registrada en el tablero "
                "y es visible para el área deProducción/TD.",

                "El monitoreo diario de avance comparalogro del plan "
                "al cierre del día vs planeado. Cuando el desvío "
                "acumulado de un pedido en muelle supera las 12 horas "
                "del compromiso original, se dispara el procedimiento "
                "de notificación al cliente, sin pasar por vía manual "
                "de Logística. El automatismo vive en el mismo tablero."
            ]
        }
    ]
}


TODAS_LAS_FAMILIAS = [FAMILIA_MANT, FAMILIA_COMP, FAMILIA_LOGI, FAMILIA_PROD]


# ──────────────────────────────────────────────────────────────────────────
#  Texto de las preguntas semilla (RAG-1, RAG-2, RAG-3).
#  Estas preguntas son las que el facilitador usa en las pantallas 6 y 7.
#  El pre-bakeo les calcula el embedding y las coloca en
#  app/data/similitudes.json para que la validación (CA-6.1) verifique que
#  el chunk correcto está en el top-3.
# ──────────────────────────────────────────────────────────────────────────
PREGUNTAS_SEMILLA = [
    {
        "id": "RAG-1",
        "dominio_esperado": "Mantenimiento",
        "texto": (
            f"Si el molino {EQUIPO_MOLINO} entra en alerta por vibración, "
            "¿qué dice el manual que debe hacer el turno de mantenimiento?"
        )
    },
    {
        "id": "RAG-2",
        "dominio_esperado": "Compras",
        "texto": (
            f"Si la planta de {PLANTA_ITG} declara stock crítico de maíz "
            "amarillo, ¿qué procedimiento sigue el área de Compras para "
            "reabastecer?"
        )
    },
    {
        "id": "RAG-3",
        "dominio_esperado": "Logística",
        "texto": (
            f"Si el pedido {PEDIDO_ATASCADO} lleva más de 6 turnos en "
            "muelle en estado en_muelle, ¿qué notificación hace Logística "
            "al cliente?"
        )
    }
]


# ──────────────────────────────────────────────────────────────────────────
#  Generación + validación.
# ──────────────────────────────────────────────────────────────────────────
def construir_corpus() -> dict[str, Any]:
    """Componer el corpus completo con la semilla fija."""
    random.seed(SEMILLA)
    familias_out: list[dict[str, Any]] = []
    total_docs = 0
    total_parrafos = 0
    total_palabras = 0
    anomalias_out: list[dict[str, Any]] = []

    for fam in TODAS_LAS_FAMILIAS:
        fam_out: list = []
        for doc in fam["documentos"]:
            # cuerpo en este orden: no hay orden alatorio en este script;
            # todo es literal. La semilla fija se reusa arriba por comunidad.
            doc_out = {
                "id": doc["id"],
                "titulo": doc["titulo"],
                "parrafos": list(doc["parrafos"]),
                "dominio": fam["id"],
                "dominio_label": fam["dominio"],
                "anomalias_plantadas": doc.get("anomalias_plantadas", []),
            }
            fam_out.append(doc_out)
            total_docs += 1
            total_parrafos += len(doc_out["parrafos"])
            for p in doc_out["parrafos"]:
                total_palabras += len(p.split())
            for an in doc.get("anomalias_plantadas", []):
                anomalias_out.append({
                    "id": an["id"],
                    "doc": doc["id"],
                    "parrafo_idx": an["parrafo_idx"],
                    "dominio": fam["id"]
                })
        familias_out.append({
            "id": fam["id"],
            "dominio": fam["dominio"],
            "documentos": fam_out
        })

    return {
        "semilla": SEMILLA,
        "fecha_generacion": date.today().isoformat(),
        "familias": familias_out,
        "preguntas_semilla": PREGUNTAS_SEMILLA,
        "anomalias_plantadas": anomalias_out,
        "_stats": {
            "familias": len(familias_out),
            "documentos": total_docs,
            "paragrafos": total_parrafos,
            "palabras_aprox": total_palabras,
            "anomalias": len(anomalias_out)
        }
    }


def validar(corpus: dict[str, Any]) -> list[str]:
    """Thresholds de validación. Devuelve lista de errores; vacía = OK."""
    errores: list[str] = []

    familias = [f["id"] for f in corpus["familias"]]
    if familias != ["mant", "comp", "logi", "prod"]:
        errores.append(f"Familias esperadas [mant, comp, logi, prod], "
                       f"obtenidas {familias}")

    if len(corpus["anomalias_plantadas"]) != 3:
        errores.append(f"Se esperaban 3 anomalías plantadas, hay "
                       f"{len(corpus['anomalias_plantadas'])}")

    ids_esperados = {"RAG-1", "RAG-2", "RAG-3"}
    ids_presentes = {an["id"] for an in corpus["anomalias_plantadas"]}
    if ids_presentes != ids_esperados:
        errores.append(f"IDs de anomalías distintos: {ids_presentes} vs "
                       f"{ids_esperados}")

    # Cada anomalía debe estar en el dominio esperado:
    # RAG-1 → mant, RAG-2 → comp, RAG-3 → logi.
    mapa = {an["id"]: an["dominio"]
            for an in corpus["anomalias_plantadas"]}
    esperados = {"RAG-1": "mant", "RAG-2": "comp", "RAG-3": "logi"}
    for an_id, dom in esperados.items():
        if mapa.get(an_id) != dom:
            errores.append(f"Anomalía {an_id} debería estar en familia {dom}, "
                           f"está en {mapa.get(an_id)}")

    # Cada familia debe tener entre 3 y 5 documentos.
    for fam in corpus["familias"]:
        n = len(fam["documentos"])
        if not 3 <= n <= 5:
            errores.append(f"Familia {fam['id']} tiene {n} documentos; "
                           f"se esperaban entre 3 y 5")

    # Cada documento debe tener al menos 2 párrafos y títulos no vacíos.
    for fam in corpus["familias"]:
        for doc in fam["documentos"]:
            if len(doc["parrafos"]) < 2:
                errores.append(f"Documento {doc['id']} tiene "
                               f"{len(doc['parrafos'])} párrafos (< 2)")
            if not doc["titulo"].strip():
                errores.append(f"Documento {doc['id']} tiene título vacío")

    # Las preguntas semilla deben tener 3 entradas y referencia de dominio.
    if len(corpus["preguntas_semilla"]) != 3:
        errores.append(f"Se esperaban 3 preguntas semilla, hay "
                       f"{len(corpus['preguntas_semilla'])}")
    ids_p = [p["id"] for p in corpus["preguntas_semilla"]]
    if ids_p != ["RAG-1", "RAG-2", "RAG-3"]:
        errores.append(f"IDs de preguntas semilla distintos: {ids_p}")

    return errores


def escribir(corpus: dict[str, Any], salida: Path) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera el corpus sintético Bios para la clase 3 (RAG).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Determinístico (semilla 42). El texto es literal, no usa "
            "LLM. Validado por thresholds (familias 4, anomalías 3, "
            "documentos por familia 3-5, preguntas semilla 3)."
        )
    )
    parser.add_argument(
        "--salida", type=Path,
        default=Path("app/data/corpus.json"),
        help="Archivo JSON de salida (default: app/data/corpus.json)"
    )
    parser.add_argument(
        "--verificar", action="store_true",
        help="Solo validar; no escribe archivo"
    )
    args = parser.parse_args()

    corpus = construir_corpus()
    errores = validar(corpus)

    print(f"✓ Semilla: {corpus['semilla']}")
    print(f"✓ Fecha de generación: {corpus['fecha_generacion']}")
    print(f"✓ Familias: {corpus['_stats']['familias']}")
    print(f"✓ Documentos: {corpus['_stats']['documentos']}")
    print(f"✓ Párrafos: {corpus['_stats']['paragrafos']}")
    print(f"✓ Palabras (aprox): {corpus['_stats']['palabras_aprox']}")
    print(f"✓ Anomalías plantadas: {corpus['_stats']['anomalias']}")
    for an in corpus["anomalias_plantadas"]:
        print(f"    └ {an['id']}: {an['doc']} · párrafo {an['parrafo_idx']}")
    print(f"✓ Preguntas semilla: {len(corpus['preguntas_semilla'])}")

    if errores:
        print("\n✗ Validación FALLÓ:")
        for e in errores:
            print(f"    └ {e}")
        return 1

    print("\n✓ Validación OK")

    if args.verificar:
        print("(modo --verificar: no se escribe archivo)")
        return 0

    escribir(corpus, args.salida)
    print(f"✓ Escrito en {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())