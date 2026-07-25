"""Supervisor con agentes como tools — la mecánica compartida de N5.

Ebook 8.1, variante "supervisor (llamada a herramientas)": los agentes se
representan como herramientas y el supervisor usa un LLM con tool calling para
decidir a qué agente-herramienta llamar y con qué argumentos.

Este módulo existe para que el tablero y el notebook compartan UNA sola
implementación. Si el notebook funciona, el tablero funciona (spec 02); si cada
uno tuviera la suya, se desincronizarían y el participante vería en el tablero algo
distinto de lo que construyó.

Lo que aporta: la envoltura de un agente como tool y la cola que saca a la
superficie la actividad interna del sub-agente. Sin la cola, esa actividad
ocurriría dentro de una función que ya no puede hacer `yield` hacia afuera, y el
tablero se quedaría sin ver la anidación — que es justamente lo que hay que
mostrar en pantalla.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable, NamedTuple

from backend.config import config
from backend.eventos import Evento
from backend.niveles.base import Ejecucion, esta_cancelado
from backend.niveles.react import stream_react

MAX_LLAMADAS_LLM = 20
MAX_ITERACIONES_SUB = 5
MAX_ITERACIONES_SUPERVISOR = 6

CENTINELA = object()


class SubAgente(NamedTuple):
    """Un especialista al que el supervisor puede preguntar.

    `descripcion` es lo que ve el supervisor para decidir a quién llamar: es un
    prompt, no documentación. Vale lo mismo que la docstring de una tool.
    """

    nombre: str
    system_prompt: str
    tools: list[Callable]
    descripcion: str


class Delegador:
    """Convierte una lista de `SubAgente` en tools que el supervisor puede llamar.

    Uso:

        delegador = Delegador(ej, SUBAGENTES)
        supervisor = create_react_agent(cliente(), delegador.tools, prompt=PROMPT)
        async for evento in delegador.correr(supervisor, pregunta, PROMPT):
            yield evento
    """

    def __init__(
        self,
        ej: Ejecucion,
        subagentes: list[SubAgente],
        max_iteraciones_sub: int = MAX_ITERACIONES_SUB,
        max_llamadas: int = MAX_LLAMADAS_LLM,
    ) -> None:
        self.ej = ej
        self.subagentes = subagentes
        self.max_iteraciones_sub = max_iteraciones_sub
        self.max_llamadas = max_llamadas
        self.cola: asyncio.Queue = asyncio.Queue()
        self.tools = [self._envolver(s) for s in subagentes]
        self.nombres = [s.nombre for s in subagentes]

    # --- Un agente expuesto como tool -------------------------------------

    def _envolver(self, sub: SubAgente):
        """Un agente expuesto como tool es solo una función que llama a un agente.

        Esta es la línea que revela que la arquitectura de la sección 8.1 no es
        nueva: es la misma de N4, aplicada un nivel más arriba.
        """
        from langchain_core.tools import StructuredTool

        async def invocar(instruccion: str) -> str:
            return await self._delegar(sub, instruccion)

        return StructuredTool.from_function(
            coroutine=invocar,
            name=sub.nombre,
            description=sub.descripcion,
        )

    async def _delegar(self, sub: SubAgente, instruccion: str) -> str:
        ej = self.ej
        if ej.llamadas_llm >= self.max_llamadas:
            return (
                "No consulté: el run alcanzó el tope de llamadas al modelo. "
                "Responde con lo que ya tengas."
            )

        await self.cola.put(
            ej.ev("delegacion", agente=sub.nombre, instruccion=instruccion)
        )

        # Sub-run con su PROPIO contador de `seq`, independiente del padre
        # (invariante 8). Comparte `t0` para que los tiempos sean comparables.
        subej = Ejecucion(ej.nivel_id, ej.run_id, emisor=ej.emisor.sub_emisor())

        async def anidar(evento: Any) -> None:
            # Invariante 10: anidación de un solo nivel. Un sub-agente no delega,
            # así que ningún `sub_evento` contiene otro.
            await self.cola.put(
                ej.ev("sub_evento", agente=sub.nombre, evento=evento)
            )

        # El sub-run cumple el contrato completo por separado (invariante 9): su
        # propio `inicio`, sus propias `metricas`, su propio `fin`.
        await anidar(
            subej.ev(
                "inicio",
                pregunta=instruccion,
                modelo=config.openai_model,
                desde_cache=False,
            )
        )
        estado = "ok"
        try:
            async for evento in stream_react(
                subej,
                tools=sub.tools,
                system_prompt=sub.system_prompt,
                pregunta=instruccion,
                max_iteraciones=self.max_iteraciones_sub,
            ):
                await anidar(evento)
        except Exception as exc:  # noqa: BLE001
            estado = "error"
            await anidar(
                subej.ev(
                    "error",
                    mensaje=f"{type(exc).__name__}: {exc}",
                    recuperable=False,
                )
            )
            subej.respuesta_final = (
                f"El agente falló: {type(exc).__name__}. No tengo el dato; no lo "
                "inventes."
            )

        await anidar(subej.ev("respuesta_final", texto=subej.respuesta_final))
        await anidar(subej.metricas())
        await anidar(subej.ev("fin", estado=estado))
        ej.sumar_subrun(subej)
        return subej.respuesta_final or "El agente no devolvió respuesta."

    # --- Ejecución del supervisor ----------------------------------------

    async def correr(
        self,
        pregunta: str,
        system_prompt: str,
        agente: Any = None,
        modelo: str | None = None,
        max_iteraciones: int = MAX_ITERACIONES_SUPERVISOR,
    ) -> AsyncIterator[Evento]:
        """Emite los eventos del supervisor y de sus sub-agentes, intercalados."""
        ej = self.ej

        async def bombear() -> None:
            try:
                async for evento in stream_react(
                    ej,
                    tools=self.tools,
                    system_prompt=system_prompt,
                    pregunta=pregunta,
                    modelo=modelo or config.modelo_del_supervisor,
                    max_iteraciones=max_iteraciones,
                    nombres_tools=self.nombres,
                    agente=agente,
                ):
                    await self.cola.put(evento)
            except Exception as exc:  # noqa: BLE001
                await self.cola.put(
                    ej.ev(
                        "error",
                        mensaje=f"{type(exc).__name__}: {exc}",
                        recuperable=False,
                    )
                )
            finally:
                await self.cola.put(CENTINELA)

        tarea = asyncio.create_task(bombear())
        try:
            while True:
                item = await self.cola.get()
                if item is CENTINELA:
                    break
                yield item
                if esta_cancelado(ej.run_id):
                    break
                if ej.llamadas_llm > self.max_llamadas:
                    yield ej.ev(
                        "aviso",
                        gravedad="alerta",
                        mensaje=(
                            f"Tope de {self.max_llamadas} llamadas al modelo "
                            "alcanzado. El supervisor corta y responde."
                        ),
                    )
                    break
        finally:
            if not tarea.done():
                tarea.cancel()
                try:
                    await tarea
                except BaseException:  # noqa: BLE001 — incluye CancelledError
                    pass
