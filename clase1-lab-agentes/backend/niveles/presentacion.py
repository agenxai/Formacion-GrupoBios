"""Diagramas de arquitectura y textos explicativos de cada nivel.

Sostiene el **modo paso a paso** del tablero: un nivel a la vez, con su diagrama
dibujado en SVG y la petición viajando por él conforme corre. El objetivo es que se
entienda de primerazo: no un dibujo estático al lado de una traza, sino la traza
ocurriendo *sobre* el dibujo.

Por qué vive en el backend y no en el frontend: la spec 02 dice que toda diferencia
entre niveles vive del lado del nivel y ninguna en el frontend. Un diagrama ES
conocimiento del nivel — la forma de su arquitectura. Al estar acá, `GET /api/niveles`
lo entrega y el frontend lo dibuja de forma genérica: agregar un sexto nivel no obliga
a tocar una línea de JavaScript.

════════════════════════════════════════════════════════════════════════════════
 EL MODELO DE DATOS
════════════════════════════════════════════════════════════════════════════════

**`columnas`** — nodos agrupados de izquierda a derecha. El frontend calcula las
coordenadas; acá solo se declara el orden y qué va en paralelo.

**`aristas`** — las flechas, con `desde` y `hasta` (ids de nodo). `curva` las manda
por debajo (`abajo`) o por encima (`arriba`) cuando vuelven hacia atrás; es lo que
dibuja el bucle de N4. `tenue: True` para las que existen como posibilidad pero no se
recorrieron —los caminos que N2 no eligió—.

**`flujo`** — lo que se ANIMA. Mapea *evento* → *qué viaja y por dónde*:

    "tool_call": {"arista": "a2", "etiqueta": "{nombre}", "clase": "tool"}

Cuando llega un `tool_call`, un paquete etiquetado con el nombre de la herramienta
recorre la arista `a2`. Las llaves toman campos del propio evento, así que
`"a_del_{agente}"` manda el paquete a la arista del sub-agente al que se delegó, sin
una línea de lógica por nivel en el frontend.

Para los eventos anidados de N5 la clave lleva el tipo interior:
`"sub_evento.tool_call"`. Y `insignia` en lugar de `arista` hace destellar una
etiqueta *sobre* un nodo — así se ve que un sub-agente usó una herramienta por dentro
sin dibujarle las siete herramientas alrededor.
"""

from __future__ import annotations

# tipo de nodo: entrada | modelo | decision | tool | agente | salida
# Determina la FORMA además del color: los proyectores desaturan y en cualquier
# grupo de quince personas hay daltonismo.


def _n(id: str, etiqueta: str, tipo: str, nota: str = "") -> dict:
    return {"id": id, "etiqueta": etiqueta, "tipo": tipo, "nota": nota}


def _a(id: str, desde: str, hasta: str, etiqueta: str = "", **extra) -> dict:
    return {"id": id, "desde": desde, "hasta": hasta, "etiqueta": etiqueta, **extra}


DOMINIOS = ("mantenimiento", "compras", "logistica", "demanda")
AGENTES = ("agente_abastecimiento", "agente_operaciones")


DIAGRAMAS: dict[str, dict] = {
    # ══════════════════════════════════════════════════════════════════ N1
    "n1": {
        "columnas": [
            [_n("pregunta", "Pregunta", "entrada")],
            [_n("llm", "LLM", "modelo", "0 herramientas")],
            [_n("respuesta", "Respuesta", "salida", "sin ninguna fuente")],
        ],
        "aristas": [
            _a("a_in", "pregunta", "llm"),
            _a("a_out", "llm", "respuesta"),
        ],
        "activacion": {
            "inicio": "pregunta",
            "llm_request": "llm",
            "respuesta_final": "respuesta",
        },
        "flujo": {
            "inicio": {"arista": "a_in", "etiqueta": "la pregunta", "clase": "peticion"},
            "respuesta_final": {
                "arista": "a_out",
                "etiqueta": "texto generado",
                "clase": "respuesta",
            },
        },
        "leyenda": (
            "Dos flechas y nada en el medio. No hay a dónde ir a buscar un dato: "
            "lo que sale es lo que el modelo trae de su entrenamiento."
        ),
    },
    # ══════════════════════════════════════════════════════════════════ N2
    "n2": {
        "columnas": [
            [_n("pregunta", "Pregunta", "entrada")],
            [_n("llm", "LLM decide", "decision", "salida estructurada")],
            [_n(d, d, "salida") for d in DOMINIOS],
            [_n("alto", "Se detiene", "salida", "no ejecuta la ruta")],
        ],
        "aristas": [
            _a("a_in", "pregunta", "llm"),
            # Los cuatro caminos posibles. Se dibujan tenues y solo se enciende el
            # que el modelo eligió: se ve de un golpe que descartó tres.
            *[_a(f"a_dom_{d}", "llm", d, tenue=True) for d in DOMINIOS],
            *[_a(f"a_fin_{d}", d, "alto", tenue=True) for d in DOMINIOS],
        ],
        "activacion": {
            "inicio": "pregunta",
            "llm_request": "llm",
            "ruta": "{dominio}",
            "respuesta_final": "alto",
        },
        "flujo": {
            "inicio": {"arista": "a_in", "etiqueta": "la pregunta", "clase": "peticion"},
            "ruta": {
                "arista": "a_dom_{dominio}",
                "etiqueta": "ruta: {dominio}",
                "clase": "decision",
            },
            "respuesta_final": {
                "insignia": "alto",
                "etiqueta": "y aquí para",
                "clase": "respuesta",
            },
        },
        "leyenda": (
            "Cuatro caminos dibujados, uno recorrido. Mira los tres que quedan "
            "apagados: eso es la información que el enrutador tuvo que tirar."
        ),
    },
    # ══════════════════════════════════════════════════════════════════ N3
    "n3": {
        "columnas": [
            [_n("pregunta", "Pregunta", "entrada")],
            [_n("llm1", "LLM · 1", "modelo", "7 herramientas declaradas")],
            [_n("tool", "Herramienta", "tool", "consulta la base")],
            [_n("llm2", "LLM · 2", "modelo", "ya sin herramientas")],
            [_n("respuesta", "Respuesta", "salida", "correcta e incompleta")],
        ],
        "aristas": [
            _a("a_in", "pregunta", "llm1"),
            _a("a_call", "llm1", "tool", "tool_call"),
            _a("a_result", "tool", "llm2", "resultado"),
            _a("a_out", "llm2", "respuesta"),
        ],
        "activacion": {
            "inicio": "pregunta",
            "llm_request": "llm{n_llamada}",
            "tool_call": "tool",
            "respuesta_final": "respuesta",
        },
        "flujo": {
            "inicio": {"arista": "a_in", "etiqueta": "la pregunta", "clase": "peticion"},
            "tool_call": {
                "arista": "a_call",
                "etiqueta": "{nombre}",
                "clase": "tool",
            },
            "tool_result": {
                "arista": "a_result",
                "etiqueta": "datos reales",
                "clase": "resultado",
            },
            "respuesta_final": {
                "arista": "a_out",
                "etiqueta": "la respuesta",
                "clase": "respuesta",
            },
        },
        "leyenda": (
            "Sigue el paquete: la pregunta entra, el modelo NO ejecuta nada — solo "
            "emite el JSON que pide la herramienta—, tú la ejecutas, el dato vuelve "
            "y recién entonces responde. Y el camino es una sola línea recta: no "
            "hay forma de volver a consultar."
        ),
    },
    # ══════════════════════════════════════════════════════════════════ N4
    "n4": {
        "columnas": [
            [_n("pregunta", "Pregunta", "entrada")],
            [_n("llm", "LLM", "modelo", "razona y decide")],
            [_n("tool", "Herramientas", "tool", "7 disponibles")],
            [_n("respuesta", "Respuesta", "salida", "con conclusión")],
        ],
        "aristas": [
            _a("a_in", "pregunta", "llm"),
            _a("a_call", "llm", "tool", "tool_call"),
            # LA ARISTA DEL NIVEL. Es la única diferencia con N3, y se ve porque el
            # paquete de resultado la recorre hacia atrás una vez por iteración.
            _a("a_loop", "tool", "llm", "observación", curva="abajo", bucle=True),
            _a("a_out", "llm", "respuesta"),
        ],
        "activacion": {
            "inicio": "pregunta",
            "llm_request": "llm",
            "tool_call": "tool",
            "respuesta_final": "respuesta",
        },
        "flujo": {
            "inicio": {"arista": "a_in", "etiqueta": "la pregunta", "clase": "peticion"},
            "tool_call": {"arista": "a_call", "etiqueta": "{nombre}", "clase": "tool"},
            "tool_result": {
                "arista": "a_loop",
                "etiqueta": "observación",
                "clase": "resultado",
            },
            "respuesta_final": {
                "arista": "a_out",
                "etiqueta": "la respuesta",
                "clase": "respuesta",
            },
        },
        "leyenda": (
            "El mismo dibujo de N3 más UNA flecha: la de abajo, que vuelve. "
            "Cuéntala cada vez que el paquete la recorre — cada vuelta es una "
            "iteración, y cada iteración es contexto que se reenvía y se paga."
        ),
    },
    # ══════════════════════════════════════════════════════════════════ N5
    "n5": {
        "columnas": [
            [_n("pregunta", "Pregunta", "entrada")],
            [_n("supervisor", "Supervisor", "decision", "no toca la base")],
            [
                _n(
                    "agente_abastecimiento",
                    "agente_abastecimiento",
                    "agente",
                    "inventario · demanda · producción",
                ),
                _n(
                    "agente_operaciones",
                    "agente_operaciones",
                    "agente",
                    "fallas · sensores · pedidos · muelle",
                ),
            ],
            [_n("sintesis", "Síntesis", "salida", "un diagnóstico único")],
        ],
        "aristas": [
            _a("a_in", "pregunta", "supervisor"),
            *[_a(f"a_del_{ag}", "supervisor", ag, "instrucción") for ag in AGENTES],
            *[_a(f"a_ret_{ag}", ag, "sintesis", "diagnóstico") for ag in AGENTES],
        ],
        "activacion": {
            "inicio": "pregunta",
            "llm_request": "supervisor",
            "delegacion": "{agente}",
            "sub_evento": "{agente}",
            "respuesta_final": "sintesis",
        },
        "flujo": {
            "inicio": {"arista": "a_in", "etiqueta": "la pregunta", "clase": "peticion"},
            "delegacion": {
                "arista": "a_del_{agente}",
                "etiqueta": "instrucción",
                "clase": "decision",
            },
            # La actividad interna del sub-agente se muestra como una insignia que
            # destella SOBRE su nodo, en lugar de dibujarle sus herramientas
            # alrededor. Dice lo que hay que decir —«por dentro es un ReAct
            # completo»— sin convertir el diagrama en una maraña.
            "sub_evento.tool_call": {
                "insignia": "{agente}",
                "etiqueta": "🔧 {nombre}",
                "clase": "tool",
            },
            "sub_evento.respuesta_final": {
                "arista": "a_ret_{agente}",
                "etiqueta": "diagnóstico",
                "clase": "resultado",
            },
            "respuesta_final": {
                "insignia": "sintesis",
                "etiqueta": "un solo diagnóstico",
                "clase": "respuesta",
            },
        },
        "leyenda": (
            "El supervisor nunca toca la base: reparte instrucciones y espera "
            "diagnósticos. Cada destello 🔧 sobre un agente es una herramienta que "
            "usó por dentro — cada uno es un N4 completo. Cuenta los destellos y "
            "entenderás por qué cuesta lo que cuesta."
        ),
    },
}


# --- Textos del modo paso a paso ---------------------------------------------
# Resumidos de la spec 05. Se muestran junto al diagrama mientras se explica.

TEXTOS: dict[str, dict[str, str]] = {
    "n1": {
        "que_hace": (
            "Una única llamada al modelo. El system prompt lo presenta como "
            "asistente de operaciones, así que se siente autorizado a responder."
        ),
        "que_no_hace": "No consulta la base. No tiene forma de saber nada real.",
        "observa": (
            "Si dio una cifra, no salió de ninguna fuente. Si se negó, se portó "
            "bien — y sigue siendo inútil para la operación. Los dos resultados "
            "enseñan lo mismo."
        ),
        "cuando_usarlo": "Clasificar o redactar texto. Nada que dependa de un dato.",
    },
    "n2": {
        "que_hace": (
            "El modelo clasifica la pregunta en uno de cuatro dominios y explica "
            "por qué, con salida estructurada sobre un modelo Pydantic."
        ),
        "que_no_hace": "No consulta datos. No responde la pregunta. Elige y para.",
        "observa": (
            "Enrutó bien… y no sirvió de nada. La pregunta que sigue —«¿y ahora "
            "quién ejecuta?»— es la puerta de entrada a N3. Prueba también una "
            "pregunta ambigua: tiene que elegir uno y pierde la otra mitad."
        ),
        "cuando_usarlo": "Triage y enrutamiento. Mesas de ayuda, bandejas de entrada.",
    },
    "n3": {
        "que_hace": (
            "El modelo elige qué herramienta usar y con qué argumentos; el código "
            "la ejecuta y le devuelve el resultado para que responda."
        ),
        "que_no_hace": (
            "No itera. Si le falta un segundo dato, no vuelve a consultar: "
            "responde con lo que tiene."
        ),
        "observa": (
            "Mira el JSON crudo: el modelo NO ejecuta nada, solo dice qué "
            "ejecutarías. Y fíjate en la respuesta: está correcta y está "
            "incompleta. ¿Qué le falta? Una palabra."
        ),
        "cuando_usarlo": (
            "Consulta puntual. Una pregunta, una fuente, una respuesta — como la "
            "interfaz tipo aeropuerto de Logística."
        ),
    },
    "n4": {
        "que_hace": (
            "Ciclo ReAct: razona, llama una herramienta, observa el resultado y "
            "decide si necesita otra. Encadena sin que nadie se lo pida."
        ),
        "que_no_hace": (
            "No delega ni separa contextos: un solo agente con las siete "
            "herramientas y un solo hilo de razonamiento."
        ),
        "observa": (
            "Nadie le dijo que consultara dos tablas. Y compara los tokens con "
            "N3: la factura no está en el número de llamadas, está en el contexto "
            "que se reenvía en cada vuelta."
        ),
        "cuando_usarlo": "Análisis multi-fuente dentro de un mismo dominio.",
    },
    "n5": {
        "que_hace": (
            "Un supervisor que ve a dos agentes especializados como si fueran "
            "herramientas: decide a quién preguntar, y sintetiza lo que le "
            "devuelven."
        ),
        "que_no_hace": (
            "Los sub-agentes no se hablan entre sí y no delegan: la anidación es "
            "de un solo nivel."
        ),
        "observa": (
            "Un agente delegando en otro agente, y el supervisor sin tocar la "
            "base. Ahora mira el costo: se justifica cuando hay separación real "
            "de dominios, no por sofisticación."
        ),
        "cuando_usarlo": (
            "Dominios separados con contextos que conviene no mezclar. Con una "
            "sola pregunta de un solo dominio, un supervisor es un N4 caro."
        ),
    },
}


def de(nivel_id: str) -> dict:
    """Diagrama + textos de un nivel, para `GET /api/niveles`."""
    return {
        "diagrama": DIAGRAMAS.get(nivel_id),
        "textos": TEXTOS.get(nivel_id, {}),
    }
