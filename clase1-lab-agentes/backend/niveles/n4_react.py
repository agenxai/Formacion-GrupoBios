"""N4 · Agente multipasos (ReAct) ★★★ — `while llm_should_continue(): execute_next_step()`

`create_react_agent` de LangGraph con las 7 tools. Ciclo Thought → Action →
Observation hasta responder o alcanzar el tope de iteraciones.

Tres momentos pedagógicos (spec 05):

1. **Encadenamiento autónomo.** Nadie le dijo que consultara dos tablas. Con la
   pregunta insignia hace `consultar_inventario` → `consultar_demanda` → compara →
   responde con un juicio, no con dos cifras sueltas.
2. **Cuánto abstrae el framework.** Se proyecta `n3_tool_caller.correr` (≈150
   líneas con eventos, ≈30 de lógica) al lado de `construir_agente` (3 líneas). La
   misma capacidad, más el loop.
3. **El costo.** ~5 llamadas al modelo contra 2 de N3, visible en la fila de
   métricas.

`max_iteraciones = 8`: al alcanzarlo emite `aviso` y responde con lo acumulado.
Nunca se cuelga en clase.
"""

from __future__ import annotations

from typing import AsyncIterator

from backend.eventos import Evento
from backend.niveles.base import Ejecucion, NivelBase
from backend.niveles.react import stream_react
from backend.tools.operaciones import TODAS

MAX_ITERACIONES = 8


class N4(NivelBase):
    ID = "n4"
    NOMBRE = "Agente multipasos"
    ESTRELLAS = "★★★"
    PATRON = "while llm_should_continue(): execute_next_step()"
    DESCRIPCION = (
        "ReAct sobre LangGraph: razona, llama una herramienta, observa el "
        "resultado y decide si sigue. Encadena consultas sin que nadie se lo pida."
    )
    TOOLS = TODAS

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        async for evento in stream_react(
            ej,
            tools=TODAS,
            system_prompt=self.system_prompt(),
            pregunta=pregunta,
            max_iteraciones=MAX_ITERACIONES,
        ):
            yield evento

        yield ej.ev("respuesta_final", texto=ej.respuesta_final)


nivel = N4()
