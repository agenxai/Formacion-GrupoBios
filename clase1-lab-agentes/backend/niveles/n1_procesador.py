"""N1 · Procesador simple ☆☆☆ — `process_llm_output(llm_response)`

Una única llamada al modelo. Sin tools. Sin decisiones. Sin forma de saber nada
real.

El momento pedagógico: el modelo **producirá una cifra inventada** o se negará
vagamente, y los dos resultados sirven. Si inventa, se contrasta con el valor real
de la base proyectado al lado. Si se niega, la lección es igual de buena —incluso
portándose bien, es inútil para la operación— y el facilitador presiona con «estima
un valor típico», que normalmente sí produce la cifra (spec 05 y guion, minuto 0-4).
"""

from __future__ import annotations

import re
from typing import AsyncIterator

from backend.eventos import Evento
from backend.llm import cliente, con_reintentos
from backend.niveles.base import Ejecucion, NivelBase

# Heurística de la spec 05: un número con unidad de masa en una respuesta que no
# consultó ninguna fuente.
#
# Es UNA HEURÍSTICA, no un detector de alucinaciones, y así se declara en la UI. No
# se le enseña al grupo que existe una forma barata de detectar alucinaciones.
# Falla ante «alrededor de media tonelada» o «unas 450», y falla en el clímax de la
# demo — por eso existe además el botón manual del facilitador
# (POST /api/marcar_sin_fuente), que emite este mismo evento a mano.
PATRON_CIFRA_MASA = re.compile(
    r"\d+([.,]\d+)?\s*(ton\b|toneladas?\b|t\b|kg\b|kilos?\b)", re.IGNORECASE
)

TEXTO_AVISO = "El modelo afirmó una cantidad sin haber consultado ninguna fuente."


class N1(NivelBase):
    ID = "n1"
    NOMBRE = "Procesador simple"
    ESTRELLAS = "☆☆☆"
    PATRON = "process_llm_output(llm_response)"
    DESCRIPCION = (
        "Una llamada al modelo, sin herramientas. No puede consultar nada: "
        "responde con lo que trae de su entrenamiento."
    )
    TOOLS: list = []

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        modelo = cliente()
        system = self.system_prompt()
        mensajes = [
            {"role": "system", "content": system},
            {"role": "user", "content": pregunta},
        ]

        n = ej.proxima_llamada()
        yield ej.ev(
            "llm_request",
            n_llamada=n,
            mensajes=[{"rol": m["role"], "contenido": m["content"]} for m in mensajes],
            # Vacío, y eso es el punto del nivel: no hay nada que llamar.
            tools_declaradas=[],
        )

        antes = ej.emisor.ms_transcurridos

        # Los reintentos se acumulan y se emiten después: `con_reintentos` no es
        # un generador, así que no puede hacer `yield` desde dentro.
        pendientes: list[tuple[str, int, float]] = []

        def reintento(mensaje: str, intento: int, espera: float) -> None:
            pendientes.append((mensaje, intento, espera))

        respuesta = await con_reintentos(
            lambda: modelo.ainvoke(mensajes), nivel=self.ID, al_reintentar=reintento
        )
        for mensaje, intento, espera in pendientes:
            yield ej.ev(
                "error",
                mensaje=f"{mensaje} · reintentando en {espera:.1f}s",
                recuperable=True,
                reintento=intento,
            )

        texto = respuesta.content if isinstance(respuesta.content, str) else ""
        uso = getattr(respuesta, "usage_metadata", None) or {}
        tin = int(uso.get("input_tokens", 0) or 0)
        tout = int(uso.get("output_tokens", 0) or 0)
        ej.contar_tokens(tin, tout)

        yield ej.ev(
            "llm_response",
            n_llamada=n,
            texto=texto,
            hay_tool_calls=False,
            tokens_in=tin,
            tokens_out=tout,
            ms=ej.emisor.ms_transcurridos - antes,
        )

        if PATRON_CIFRA_MASA.search(texto or ""):
            yield ej.ev("aviso", gravedad="alerta", mensaje=TEXTO_AVISO)

        ej.respuesta_final = texto
        yield ej.ev("respuesta_final", texto=texto)


nivel = N1()
