"""N2 · Enrutador ★☆☆ — `if llm_decision(): path_a() else: path_b()`

El modelo clasifica la pregunta en uno de cuatro dominios y devuelve el motivo. El
sistema **no ejecuta** la ruta: solo la reporta.

Dos momentos pedagógicos. El LLM como **decisor**, no como generador de texto — el
cambio mental que abre la puerta a los agentes. Y la frontera visible del nivel:
ante «¿me alcanza el maíz?» enruta a `compras` y no sirve de nada. La pregunta
natural del grupo —«¿y ahora quién ejecuta?»— es la entrada a N3.

Se implementa con salida estructurada, no con parsing de texto libre. Es la ocasión
para introducirla, porque se usa todo el resto del programa.
"""

from __future__ import annotations

from typing import AsyncIterator, Literal

from pydantic import BaseModel, Field

from backend.eventos import Evento
from backend.llm import cliente, con_reintentos
from backend.niveles.base import Ejecucion, NivelBase

DOMINIOS = ("mantenimiento", "compras", "logistica", "demanda")


class Clasificacion(BaseModel):
    """Salida estructurada del router.

    Las descripciones de los campos no son documentación: viajan al modelo como
    parte del esquema de la función. Son prompt.
    """

    dominio: Literal["mantenimiento", "compras", "logistica", "demanda"] = Field(
        description="El dominio al que corresponde la pregunta."
    )
    motivo: str = Field(
        description="En una frase, por qué corresponde a ese dominio."
    )


class N2(NivelBase):
    ID = "n2"
    NOMBRE = "Enrutador"
    ESTRELLAS = "★☆☆"
    PATRON = "if llm_decision(): path_a() else: path_b()"
    DESCRIPCION = (
        "El modelo decide a qué dominio pertenece la pregunta y se detiene. "
        "Salida estructurada con un modelo Pydantic, no parsing de texto."
    )
    TOOLS: list = []

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        system = self.system_prompt()
        # include_raw=True conserva el mensaje original del modelo, y con él el
        # conteo de tokens. Sin eso, la fila de métricas de N2 quedaría en cero y
        # la comparación de costo entre niveles perdería una columna.
        modelo = cliente().with_structured_output(Clasificacion, include_raw=True)
        mensajes = [
            {"role": "system", "content": system},
            {"role": "user", "content": pregunta},
        ]

        n = ej.proxima_llamada()
        yield ej.ev(
            "llm_request",
            n_llamada=n,
            mensajes=[{"rol": m["role"], "contenido": m["content"]} for m in mensajes],
            tools_declaradas=[Clasificacion.__name__],
        )

        antes = ej.emisor.ms_transcurridos
        salida = await con_reintentos(lambda: modelo.ainvoke(mensajes), nivel=self.ID)

        crudo = salida.get("raw") if isinstance(salida, dict) else None
        parseado = salida.get("parsed") if isinstance(salida, dict) else salida
        uso = getattr(crudo, "usage_metadata", None) or {}
        tin = int(uso.get("input_tokens", 0) or 0)
        tout = int(uso.get("output_tokens", 0) or 0)
        ej.contar_tokens(tin, tout)

        yield ej.ev(
            "llm_response",
            n_llamada=n,
            texto=None,
            hay_tool_calls=True,
            tokens_in=tin,
            tokens_out=tout,
            ms=ej.emisor.ms_transcurridos - antes,
        )

        if parseado is None:
            error = salida.get("parsing_error") if isinstance(salida, dict) else None
            yield ej.ev(
                "error",
                mensaje=f"El modelo no devolvió una clasificación válida: {error}",
                recuperable=False,
            )
            ej.respuesta_final = "No pude clasificar la pregunta."
            yield ej.ev("respuesta_final", texto=ej.respuesta_final)
            return

        yield ej.ev("ruta", dominio=parseado.dominio, motivo=parseado.motivo)

        # El nivel NO ejecuta la ruta. Decir a dónde iría es todo lo que hace, y
        # que se note es el contenido del nivel.
        ej.respuesta_final = (
            f"Corresponde a {parseado.dominio}. {parseado.motivo} "
            "(Este nivel solo enruta: no consulta datos ni responde la pregunta.)"
        )
        yield ej.ev("respuesta_final", texto=ej.respuesta_final)


nivel = N2()
