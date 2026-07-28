"""Catálogo de preguntas precargadas. Spec 07.

Los identificadores literales salen de `db/constantes.py`, no se escriben a mano:
si el generador cambia, cambian acá también y no se rompe la demo en silencio.

Los chips NO son decorativos. Con API key compartida maximizan aciertos de caché —
quince personas haciendo clic en el mismo chip cuestan una sola llamada al modelo
(spec 09, 1a).

La columna `nivel_que_la_resuelve` es contenido, no metadata: mostrarla enseña que
**no toda pregunta necesita el nivel más alto**. El chip de logística se resuelve en
N3, y eso es exactamente lo que el Champion de logística necesita oír.
"""

from __future__ import annotations

from backend.db.constantes import (
    AVISO_DATOS_SINTETICOS,
    PEDIDO_ATASCADO,
    PLANTAS,
)

_MUNICIPIO = {p[0]: p[2] for p in PLANTAS}
_ITAGUI = _MUNICIPIO["PL-ITG"]
_BUGA = _MUNICIPIO["PL-BUG"]

PREGUNTAS: list[dict] = [
    {
        "id": "inventario_vs_demanda",
        "chip": "Inventario vs demanda",
        "dominio": "compras",
        "texto": (
            f"¿Cuánto maíz le queda a la planta de {_ITAGUI} y me alcanza para la "
            "demanda proyectada de esta semana?"
        ),
        "nivel_que_la_resuelve": "n4",
        "por_que": (
            "Requiere dos consultas distintas y una comparación. Es la pregunta "
            "insignia: N1 la inventa, N2 solo la clasifica, N3 la responde a "
            "medias, N4 la responde bien."
        ),
        # `cruza` es lo que la vista El caso muestra (spec 11): qué hay que
        # combinar para responderla. El nivel que la resuelve NO aparece ahí —
        # esa es la pregunta que la clase entera existe para formular.
        "cruza": "Inventario contra demanda, convirtiendo unidades de producto a materia prima.",
        "tablas": ["inventario_planta", "demanda_historica", "formulas"],
    },
    {
        "id": "equipo_en_riesgo",
        "chip": "Equipo con fallas",
        "dominio": "mantenimiento",
        "texto": f"¿Cuál equipo de {_ITAGUI} está en riesgo de falla y por qué?",
        "nivel_que_la_resuelve": "n4",
        "por_que": (
            "Hay que cruzar la repetición de correctivos con la tendencia del "
            "sensor. Una sola consulta no alcanza para justificar el 'por qué'."
        ),
        "cruza": "Correctivos repetidos contra la tendencia del sensor de vibración.",
        "tablas": ["ordenes_mantenimiento", "lecturas_sensor"],
    },
    {
        "id": "donde_esta_mi_pedido",
        "chip": "¿Dónde está mi pedido?",
        "dominio": "logistica",
        "texto": (
            f"¿Dónde está el pedido {PEDIDO_ATASCADO} y cuántos turnos le faltan?"
        ),
        "nivel_que_la_resuelve": "n3",
        "por_que": (
            "Una sola herramienta la responde completa. Es el ejemplo de que no "
            "toda pregunta necesita un agente que itere: la interfaz tipo "
            "aeropuerto es un N3 bien hecho."
        ),
        "cruza": "El pedido contra la cola de camiones del muelle.",
        "tablas": ["pedidos", "despachos"],
    },
    {
        "id": "pico_de_demanda",
        "chip": "Pico de demanda",
        "dominio": "demanda",
        "texto": (
            f"En la planta de {_BUGA}, ¿hubo algún día en que la demanda superó "
            "la producción y en cuánto?"
        ),
        "nivel_que_la_resuelve": "n4",
        "por_que": (
            "Comparar dos series del mismo período. El agente tiene que decidir "
            "qué ventana pedir y luego concluir sobre el día concreto."
        ),
        "cruza": "La demanda contra la producción del mismo período.",
        "tablas": ["demanda_historica", "produccion_diaria"],
    },
    {
        "id": "cruzada",
        "chip": "Cruzada (dos dominios)",
        "dominio": "dos dominios",
        "texto": (
            f"El pedido {PEDIDO_ATASCADO} va retrasado. ¿Es por falta de materia "
            "prima o por un problema de equipos?"
        ),
        "nivel_que_la_resuelve": "n5",
        "por_que": (
            "Abastecimiento y operaciones sobre un mismo sitio. Es la única de "
            "las cinco que justifica un supervisor: hay separación real de "
            "dominios y dos contextos que conviene no mezclar."
        ),
        "cruza": "Abastecimiento y operaciones sobre una misma planta.",
        "tablas": ["inventario_planta", "equipos", "ordenes_mantenimiento", "pedidos"],
    },
]

PREGUNTA_INSIGNIA = PREGUNTAS[0]["texto"]

# Pregunta de la demo de cierre de N4 (spec 05): una planta que no existe. El
# agente DEBE decir que no encontró datos. Cierra el arco que abrió N1.
PREGUNTA_SIN_DATOS = "¿Cuánto maíz le queda a la planta de Cali?"

# Pregunta ambigua para mostrar en vivo que un router pierde información al tener
# que elegir un solo dominio (spec 05, N2). Siembra la arquitectura de N5.
PREGUNTA_AMBIGUA = (
    "El pedido de la avícola no llegó y creo que el molino está parado."
)


def catalogo() -> dict:
    return {
        "aviso_datos": AVISO_DATOS_SINTETICOS,
        "preguntas": PREGUNTAS,
        "extras": {
            "sin_datos": PREGUNTA_SIN_DATOS,
            "ambigua": PREGUNTA_AMBIGUA,
        },
    }
