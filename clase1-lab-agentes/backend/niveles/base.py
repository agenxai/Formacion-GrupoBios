"""Contrato interno de los niveles. Spec 02.

Los cinco módulos de nivel exponen la misma firma. Es lo que permite que el tablero
los ejecute en paralelo y que la comparación entre ellos sea honesta: se mide con
la misma regla en las cinco columnas.

`NivelBase.ejecutar` es una plantilla que se encarga de todo lo que es igual en los
cinco niveles —caché, replay, métricas, cancelación, `inicio` y `fin`— y delega en
`correr()` lo único que los distingue: la arquitectura del agente.

Esto no es solo comodidad. Los invariantes 1 y 4 del contrato de eventos ("todo run
empieza con `inicio` y termina con `fin`, sin excepción, incluso al fallar" y
"`metricas` se emite siempre justo antes de `fin`") se cumplen acá una vez, en
lugar de depender de que quien escriba cada nivel se acuerde.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Protocol, runtime_checkable

from backend import prompts
from backend.config import config
from backend.eventos import Emisor, Evento
from backend.llm import (
    clave_cache,
    estado_lab,
    guardar_cache,
    leer_cache,
    reproducir,
    traza_pregrabada,
)

# Cancelación cooperativa. `POST /api/cancelar/{run_id}` agrega acá; los niveles
# consultan entre pasos. Se prefiere a cancelar la tarea de asyncio porque así el
# run alcanza a emitir sus `metricas` y su `fin`, y la traza queda completa.
CANCELADOS: set[str] = set()


def cancelar(run_id: str) -> None:
    CANCELADOS.add(run_id)


def esta_cancelado(run_id: str) -> bool:
    return run_id in CANCELADOS


@runtime_checkable
class Nivel(Protocol):
    ID: str  # "n1" .. "n5"
    NOMBRE: str  # "Procesador simple"
    ESTRELLAS: str  # "☆☆☆"
    PATRON: str  # "process_llm_output(llm_response)"

    async def ejecutar(self, pregunta: str, run_id: str) -> AsyncIterator[Evento]:
        """Emite eventos del contrato (spec 04) hasta 'fin'."""
        ...


class Ejecucion:
    """Estado de UN run. Uno por ejecución, nunca compartido entre runs.

    Existe porque el tablero corre los cinco niveles a la vez y el mismo nivel
    puede estar corriendo dos veces si dos personas preguntan al mismo tiempo:
    guardar los contadores en el objeto del nivel los mezclaría.
    """

    def __init__(
        self, nivel_id: str, run_id: str, emisor: Emisor | None = None
    ) -> None:
        self.nivel_id = nivel_id
        self.run_id = run_id
        # Los sub-runs de N5 reciben un emisor con su propio contador de `seq`
        # (invariante 8): hay un contador por run y uno por sub-run, y no se
        # mezclan.
        self.emisor = emisor if emisor is not None else Emisor(nivel_id, run_id)
        self.llamadas_llm = 0
        self.llamadas_tools = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.costo_usd = 0.0
        self.respuesta_final = ""

    def ev(self, tipo: str, **campos: Any) -> Any:
        return self.emisor.emitir(tipo, **campos)

    def proxima_llamada(self) -> int:
        """Número de llamada al modelo, 1-indexado dentro del run."""
        self.llamadas_llm += 1
        return self.llamadas_llm

    def contar_tokens(self, tokens_in: int, tokens_out: int) -> None:
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.costo_usd += estado_lab.registrar_uso(
            self.nivel_id, tokens_in, tokens_out
        )

    def sumar_subrun(self, otra: "Ejecucion") -> None:
        """Absorbe las métricas de un sub-run.

        Invariante 9: las métricas del run padre son la suma de las suyas más las
        de todos sus sub-runs. El costo ya quedó contabilizado en `estado_lab` por
        el sub-run, así que acá solo se agrega al total del padre.
        """
        self.llamadas_llm += otra.llamadas_llm
        self.llamadas_tools += otra.llamadas_tools
        self.tokens_in += otra.tokens_in
        self.tokens_out += otra.tokens_out
        self.costo_usd += otra.costo_usd

    def metricas(self, desde_cache: bool = False) -> Any:
        return self.ev(
            "metricas",
            llamadas_llm=self.llamadas_llm,
            llamadas_tools=self.llamadas_tools,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            costo_usd=round(self.costo_usd, 6),
            ms_total=self.emisor.ms_transcurridos,
            desde_cache=desde_cache,
            costo_configurado=config.costo_configurado,
        )


class NivelBase:
    """Plantilla común. Los niveles concretos implementan `correr`."""

    ID: str = "?"
    NOMBRE: str = "?"
    ESTRELLAS: str = "☆☆☆"
    PATRON: str = ""
    DESCRIPCION: str = ""
    TOOLS: list = []

    # --- lo que implementa cada nivel -------------------------------------

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        raise NotImplementedError
        yield  # pragma: no cover — marca la función como generadora

    # --- lo que es igual en los cinco -------------------------------------

    def system_prompt(self) -> str:
        return prompts.obtener(self.ID)

    def variante(self) -> str:
        """Huella del código de `correr`, para que el caché no mienta.

        Entra en la clave de caché. Dos participantes que escriban el mismo N3
        comparten el resultado —lo que protege la key compartida—, pero uno que
        lo tenga a medias NO recibe la traza del que lo tiene bien: hace su propia
        llamada, ve su propio fallo y sus `assert` dicen la verdad.

        Si no se puede leer la fuente (código compilado, algún entorno raro), se
        cae al nombre completo de la clase: menos preciso, nunca engañoso.
        """
        import hashlib
        import inspect

        try:
            fuente = inspect.getsource(type(self).correr)
        except (OSError, TypeError):
            return f"{type(self).__module__}.{type(self).__qualname__}"
        return hashlib.sha256(fuente.encode("utf-8")).hexdigest()[:12]

    def metadatos(self) -> dict:
        from backend.niveles import presentacion
        from backend.tools.operaciones import firmas

        nombres = {getattr(t, "__name__", str(t)) for t in self.TOOLS}
        return {
            "id": self.ID,
            "nombre": self.NOMBRE,
            "estrellas": self.ESTRELLAS,
            "patron": self.PATRON,
            "descripcion": self.DESCRIPCION,
            "tools": [f for f in firmas() if f["nombre"] in nombres],
            # Diagrama y textos del modo paso a paso. Van acá y no en el frontend
            # porque son conocimiento del nivel: un nivel nuevo trae su diagrama y
            # el tablero lo dibuja sin cambios en JavaScript (spec 02).
            **presentacion.de(self.ID),
        }

    async def ejecutar(self, pregunta: str, run_id: str) -> AsyncIterator[Evento]:
        ej = Ejecucion(self.ID, run_id)
        prompt = self.system_prompt()
        modelo = (
            config.modelo_del_supervisor if self.ID == "n5" else config.openai_model
        )

        # 1 · Modo replay: trazas pregrabadas, con sus tiempos originales.
        if not estado_lab.vivo:
            eventos = traza_pregrabada(self.ID, pregunta)
            if eventos:
                async for evento in reproducir(eventos, run_id):
                    yield evento
                return
            # Sin traza para este nivel: se dice, no se simula.
            yield ej.ev("inicio", pregunta=pregunta, modelo=modelo, desde_cache=True)
            yield ej.ev(
                "aviso",
                gravedad="alerta",
                mensaje=(
                    "Modo replay y no hay traza pregrabada para este nivel. "
                    "Grábalas con: python -m backend.replay.grabar"
                ),
            )
            yield ej.metricas(desde_cache=True)
            yield ej.ev("fin", estado="error")
            return

        # 2 · Caché con fidelidad temporal: quince personas, una sola llamada.
        clave = clave_cache(self.ID, pregunta, prompt, self.variante())
        en_cache = leer_cache(clave)
        if en_cache:
            async for evento in reproducir(en_cache, run_id):
                yield evento
            return

        # 3 · Ejecución real.
        grabados: list[Any] = []
        estado_final = "ok"

        inicio = ej.ev("inicio", pregunta=pregunta, modelo=modelo, desde_cache=False)
        grabados.append(inicio)
        yield inicio

        try:
            async for evento in self.correr(ej, pregunta):
                grabados.append(evento)
                yield evento
                if esta_cancelado(run_id):
                    estado_final = "cancelado"
                    break
        except asyncio.CancelledError:
            estado_final = "cancelado"
        except Exception as exc:  # noqa: BLE001 — un fallo no debe dejar el run sin `fin`
            estado_final = "error"
            evento = ej.ev(
                "error",
                mensaje=f"{type(exc).__name__}: {exc}",
                recuperable=False,
            )
            grabados.append(evento)
            yield evento

        if estado_lab.aviso_replay and estado_final == "ok":
            # El tope de gasto o un 429 persistente conmutó el modo a mitad de
            # camino. Queda en la traza, no solo en la pantalla (spec 07).
            evento = ej.ev("aviso", gravedad="alerta", mensaje=estado_lab.aviso_replay)
            grabados.append(evento)
            yield evento

        metricas = ej.metricas(desde_cache=False)
        grabados.append(metricas)
        yield metricas

        fin = ej.ev("fin", estado=estado_final)
        grabados.append(fin)
        yield fin

        # Solo se cachean los runs completos: cachear un error lo repetiría toda
        # la clase sin que nadie entienda por qué.
        if estado_final == "ok":
            guardar_cache(clave, grabados, pregunta, self.ID)
        CANCELADOS.discard(run_id)
