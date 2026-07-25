"""N3 · Llamador de herramientas ★★☆ — `run_function(llm_chosen_tool, llm_chosen_args)`

El loop de function calling **escrito a mano** (ADR-003). Sin `create_react_agent`,
sin `AgentExecutor`. Cuatro pasos explícitos:

    1. Llamada al modelo con las tools declaradas.
    2. Si la respuesta trae `tool_calls`, se ejecuta la función y el resultado se
       agrega al historial como mensaje de tool.
    3. Segunda llamada al modelo, con el resultado en contexto.
    4. Se responde. **Se detiene aquí: máximo una ronda de tools.**

Ese tope es un REQUISITO, no un descuido. Con la pregunta insignia el agente
consulta inventario y responde «tiene 320 toneladas» sin compararlo contra la
demanda, porque no le dieron un segundo turno. Está *correcto pero incompleto*, y la
pregunta «¿qué le falta?» tiene una respuesta de una palabra: **iterar**. Eso es N4.
Un contraste correcto-pero-incompleto enseña más que un error.

Se usa el cliente crudo de OpenAI en lugar de la abstracción de LangChain porque
ADR-002 exige mostrar el JSON de la tool call tal como lo devolvió el modelo, y con
la abstracción de alto nivel ese JSON no se ve.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

from backend.config import config
from backend.eventos import Evento, mensajes_publicables
from backend.llm import cliente_crudo, con_reintentos, esquemas_openai
from backend.niveles.base import Ejecucion, NivelBase
from backend.tools.operaciones import POR_NOMBRE, TODAS

MAX_RONDAS = 1  # el tope del nivel, a propósito


class N3(NivelBase):
    ID = "n3"
    NOMBRE = "Llamador de herramientas"
    ESTRELLAS = "★★☆"
    PATRON = "run_function(llm_chosen_tool, llm_chosen_args)"
    DESCRIPCION = (
        "Loop de function calling escrito a mano: una ronda de herramientas y "
        "responde. No itera — si le falta un dato, no vuelve a consultar."
    )
    TOOLS = TODAS

    async def correr(self, ej: Ejecucion, pregunta: str) -> AsyncIterator[Evento]:
        openai = cliente_crudo()
        esquemas = esquemas_openai(TODAS)
        declaradas = [e["function"]["name"] for e in esquemas]

        mensajes: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt()},
            {"role": "user", "content": pregunta},
        ]

        # ---- Paso 1: primera llamada, con las tools declaradas --------------
        n = ej.proxima_llamada()
        yield ej.ev(
            "llm_request",
            n_llamada=n,
            mensajes=mensajes_publicables(mensajes),
            tools_declaradas=declaradas,
        )

        antes = ej.emisor.ms_transcurridos
        respuesta = await con_reintentos(
            lambda: openai.chat.completions.create(
                model=config.openai_model,
                messages=mensajes,
                tools=esquemas,
                temperature=0,
                # UNA herramienta por respuesta. Requisito del nivel, no un ajuste
                # de rendimiento.
                #
                # Los modelos actuales piden varias tools en paralelo en una sola
                # respuesta. Con eso, N3 consulta inventario Y demanda en su única
                # ronda, responde completo, y el contraste que sostiene todo el
                # paso a N4 —«está correcto y está incompleto, ¿qué le falta?»,
                # respuesta: iterar— simplemente no ocurre. En la primera corrida
                # real contra la API, N3 y N4 dieron la misma respuesta y N3 gastó
                # menos: el nivel superior parecía innecesario.
                #
                # Además rompía el criterio de aceptación `llamadas_tools == 1`
                # (spec 05) y con él el `assert` del notebook, en las 15 máquinas
                # a la vez.
                parallel_tool_calls=False,
            ),
            nivel=self.ID,
        )
        bruto = respuesta.model_dump()
        mensaje = bruto["choices"][0]["message"]
        llamadas = mensaje.get("tool_calls") or []
        uso = bruto.get("usage") or {}
        tin = int(uso.get("prompt_tokens", 0) or 0)
        tout = int(uso.get("completion_tokens", 0) or 0)
        ej.contar_tokens(tin, tout)

        yield ej.ev(
            "llm_response",
            n_llamada=n,
            texto=mensaje.get("content"),
            hay_tool_calls=bool(llamadas),
            tokens_in=tin,
            tokens_out=tout,
            ms=ej.emisor.ms_transcurridos - antes,
        )

        # Si el modelo respondió directo, no hay ronda de tools y el run cuesta
        # una sola llamada. Es un final legítimo del nivel.
        if not llamadas:
            texto = mensaje.get("content") or ""
            ej.respuesta_final = texto
            yield ej.ev("respuesta_final", texto=texto)
            return

        # ---- Paso 2: ejecutar cada tool que pidió el modelo ----------------
        mensajes.append(
            {
                "role": "assistant",
                "content": mensaje.get("content"),
                "tool_calls": llamadas,
            }
        )

        for i, llamada in enumerate(llamadas):
            funcion = llamada.get("function") or {}
            nombre = funcion.get("name") or "?"
            argumentos_crudos = funcion.get("arguments") or "{}"

            # `crudo` es el JSON tal cual lo devolvió el proveedor, sin reformatear
            # su contenido: `arguments` sigue siendo el STRING que produjo el
            # modelo. Es lo que se proyecta al lado de la sección 7.2 del ebook.
            crudo = json.dumps(llamada, ensure_ascii=False, indent=2)

            try:
                argumentos = json.loads(argumentos_crudos)
            except json.JSONDecodeError:
                argumentos = {}

            ej.llamadas_tools += 1
            yield ej.ev(
                "tool_call",
                id_llamada=str(llamada.get("id") or f"call_{i}"),
                nombre=nombre,
                argumentos=argumentos if isinstance(argumentos, dict) else {},
                crudo=crudo,
            )

            antes_tool = time.monotonic()
            error = None
            funcion_py = POR_NOMBRE.get(nombre)
            if funcion_py is None:
                resultado: Any = {
                    "mensaje": f"No existe la herramienta '{nombre}'.",
                }
                error = f"herramienta desconocida: {nombre}"
            else:
                try:
                    resultado = funcion_py(**argumentos)
                except Exception as exc:  # noqa: BLE001
                    # Un error de tool NO aborta el run: se le devuelve al modelo
                    # como observación. Un agente que se recupera de un error de
                    # tool es contenido valioso, no un fallo de la demo (spec 07).
                    resultado = {
                        "error": f"{type(exc).__name__}: {exc}",
                        "mensaje": "La herramienta falló. No inventes el dato.",
                    }
                    error = f"{type(exc).__name__}: {exc}"

            filas = None
            if isinstance(resultado, dict):
                for clave in ("items", "serie", "cola", "ordenes", "filas"):
                    if isinstance(resultado.get(clave), list):
                        filas = len(resultado[clave])
                        break

            yield ej.ev(
                "tool_result",
                id_llamada=str(llamada.get("id") or f"call_{i}"),
                nombre=nombre,
                resultado=resultado,
                filas=filas,
                ms=int((time.monotonic() - antes_tool) * 1000),
                error=error,
            )

            mensajes.append(
                {
                    "role": "tool",
                    "tool_call_id": str(llamada.get("id") or f"call_{i}"),
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                }
            )

        # ---- Paso 3: segunda llamada, con el resultado en contexto ---------
        #
        # Y acá termina. NO hay un `while`: si el modelo pidiera otra tool en esta
        # respuesta, se ignora y se responde con lo que hay. Ese es el nivel.
        n = ej.proxima_llamada()
        yield ej.ev(
            "llm_request",
            n_llamada=n,
            mensajes=mensajes_publicables(mensajes),
            tools_declaradas=declaradas,
        )

        antes = ej.emisor.ms_transcurridos
        segunda = await con_reintentos(
            lambda: openai.chat.completions.create(
                model=config.openai_model,
                messages=mensajes,
                temperature=0,
            ),
            nivel=self.ID,
        )
        bruto2 = segunda.model_dump()
        mensaje2 = bruto2["choices"][0]["message"]
        uso2 = bruto2.get("usage") or {}
        tin2 = int(uso2.get("prompt_tokens", 0) or 0)
        tout2 = int(uso2.get("completion_tokens", 0) or 0)
        ej.contar_tokens(tin2, tout2)

        yield ej.ev(
            "llm_response",
            n_llamada=n,
            texto=mensaje2.get("content"),
            hay_tool_calls=False,
            tokens_in=tin2,
            tokens_out=tout2,
            ms=ej.emisor.ms_transcurridos - antes,
        )

        texto = mensaje2.get("content") or ""
        ej.respuesta_final = texto
        yield ej.ev("respuesta_final", texto=texto)


nivel = N3()
