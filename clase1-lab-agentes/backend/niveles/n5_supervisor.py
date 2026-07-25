"""N5 · Sistema multiagente ★★★★ — `if llm_trigger(): execute_agent()`

Arquitectura **supervisor con agentes como tools**: la variante de la sección 8.1
del ebook. Un supervisor con dos sub-agentes especializados, cada uno con su propio
system prompt y su propio subconjunto de tools.

Por qué cabe en doce minutos de clase: **N5 se construye reutilizando N4**, y eso es
precisamente lo que enseña la arquitectura.

    1. Se instancia el ReAct dos veces, cada una con su prompt y sus tools.
    2. Se envuelve cada instancia en una función con docstring — un agente expuesto
       como tool es solo una función que por dentro llama a un agente.
    3. Se le pasan esas dos funciones como tools a un tercer ReAct.

La revelación es que "supervisor con llamada a herramientas" no es una arquitectura
nueva sino la misma de N4 aplicada un nivel más arriba. Este archivo tiene 40 líneas
por eso: toda la mecánica está en `multiagente.py`, compartida con el notebook.

Y —esto es lo que hay que decir en voz alta— cuesta ~11 llamadas al modelo lo que
N4 hacía en 5. El multiagente se justifica cuando hay separación real de dominios,
no por sofisticación. Es la advertencia de la sección 8 del ebook, ahora con la
factura al lado.
"""

from __future__ import annotations

from typing import AsyncIterator

from backend import prompts
from backend.eventos import Evento
from backend.niveles.base import Ejecucion, NivelBase
from backend.niveles.multiagente import Delegador, SubAgente
from backend.tools.operaciones import TOOLS_ABASTECIMIENTO, TOOLS_OPERACIONES


def subagentes() -> list[SubAgente]:
    """Los dos especialistas.

    La separación de tools no es decorativa: es la que justifica el multiagente.
    Si los dos vieran las siete herramientas, no habría especialización que
    mostrar y el nivel sería un N4 caro.
    """
    return [
        SubAgente(
            nombre="agente_abastecimiento",
            system_prompt=prompts.obtener("n5_abastecimiento"),
            tools=TOOLS_ABASTECIMIENTO,
            descripcion=(
                "Especialista en abastecimiento y planeación. Consulta inventarios "
                "de materias primas, demanda de producto y producción de las "
                "plantas. Pásale una pregunta completa y autocontenida; devuelve un "
                "diagnóstico con cifras."
            ),
        ),
        SubAgente(
            nombre="agente_operaciones",
            system_prompt=prompts.obtener("n5_operaciones"),
            tools=TOOLS_OPERACIONES,
            descripcion=(
                "Especialista en mantenimiento y logística. Consulta órdenes de "
                "mantenimiento, sensores de equipos, estado de pedidos y turnos de "
                "muelle. Pásale una pregunta completa y autocontenida; devuelve un "
                "diagnóstico con cifras."
            ),
        ),
    ]


class N5(NivelBase):
    ID = "n5"
    NOMBRE = "Supervisor multiagente"
    ESTRELLAS = "★★★★"
    PATRON = "if llm_trigger(): execute_agent()"
    DESCRIPCION = (
        "Un supervisor que ve a dos agentes especializados como si fueran "
        "herramientas: decide a quién preguntar y sintetiza. Cada sub-agente es "
        "un ReAct de N4 con su propio subconjunto de tools."
    )
    TOOLS = TOOLS_ABASTECIMIENTO + TOOLS_OPERACIONES

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        delegador = Delegador(ej, subagentes())
        async for evento in delegador.correr(pregunta, self.system_prompt()):
            yield evento
        yield ej.ev("respuesta_final", texto=ej.respuesta_final)


nivel = N5()
