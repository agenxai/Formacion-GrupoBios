"""Ciclo ReAct sobre LangGraph, traducido al contrato de eventos.

Lo usan N4 (directamente) y los dos sub-agentes de N5. Que sea un solo módulo es
lo que hace que N5 cueste cuatro líneas: un sub-agente es un ReAct de N4 con otro
prompt y otro subconjunto de tools (spec 05).

Por qué se reconstruyen los eventos desde el stream de mensajes en lugar de usar
callbacks: LangGraph envía al modelo la lista de mensajes acumulada, así que el
historial anterior a cada `AIMessage` **es** exactamente lo que se envió. Leerlo
del stream da el mismo dato que un callback y no depende de los nombres internos
de los nodos del grafo, que cambian entre versiones.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Callable

from backend.eventos import Evento, mensajes_publicables, recortar
from backend.llm import cliente, con_reintentos

MAX_ITERACIONES = 8


def _crudo_de(mensaje: Any, indice: int, tool_call: dict) -> str:
    """JSON de la tool call tal como vino del proveedor (ADR-002).

    `additional_kwargs['tool_calls']` conserva el payload original, incluido el
    campo `arguments` como STRING sin parsear — que es lo que se proyecta al lado
    de la sección 7.2 del ebook. Si por alguna razón no está, se reconstruye y se
    dice que es una reconstrucción: mostrar algo fabricado como si fuera la
    respuesta cruda del modelo sería incoherente con lo que enseña esta clase.
    """
    originales = (getattr(mensaje, "additional_kwargs", {}) or {}).get("tool_calls")
    if isinstance(originales, list) and indice < len(originales):
        return json.dumps(originales[indice], ensure_ascii=False, indent=2)
    return json.dumps(
        {
            "_nota": "reconstruido: el proveedor no expuso el payload original",
            "id": tool_call.get("id"),
            "type": "function",
            "function": {
                "name": tool_call.get("name"),
                "arguments": json.dumps(
                    tool_call.get("args", {}), ensure_ascii=False
                ),
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _tokens(mensaje: Any) -> tuple[int, int]:
    uso = getattr(mensaje, "usage_metadata", None) or {}
    return int(uso.get("input_tokens", 0) or 0), int(uso.get("output_tokens", 0) or 0)


def construir_agente(tools: list[Callable], system_prompt: str, modelo: str | None = None):
    """`create_react_agent` — las tres líneas que abstraen el loop de N3.

    En clase se proyecta esta función al lado de `n3_tool_caller.correr` para que
    se vea qué es exactamente lo que el framework quita de encima (spec 05, N4).

    ─── Sobre la versión de esta API ───────────────────────────────────────────

    En LangGraph 1.x, `langgraph.prebuilt.create_react_agent` está marcada como
    **deprecada** en favor de `langchain.agents.create_agent`, y se elimina en la
    2.0. Sigue funcionando en la versión fijada en `requirements.txt`.

    Se mantiene la del ebook a propósito, por una razón y no por inercia: es el
    nombre que el participante tiene delante en el material de clase, y hacer que
    el código diga otra cosa que el documento cuesta más confusión de la que
    ahorra en 55 minutos.

    **Para los proyectos reales del equipo la recomendación es la nueva API.** El
    cambio son dos líneas: agregar `langchain` a `requirements.txt` e importar
    `from langchain.agents import create_agent`. Está documentado en el README y
    vale mencionarlo en voz alta en el cierre: que la función que acaban de
    aprender ya esté deprecada es, en sí, la lección más útil sobre el ritmo de
    este ecosistema.

    El aviso de deprecación se silencia acá para que no aparezca quince veces en
    la salida de cada notebook. Se silencia el ruido, no el hecho: queda dicho en
    esta docstring, en el README y en el notebook.
    """
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*create_react_agent.*")
        from langgraph.prebuilt import create_react_agent

        return create_react_agent(
            cliente(modelo),
            tools,
            prompt=system_prompt,
        )


async def stream_react(
    ej: Any,
    tools: list[Callable],
    system_prompt: str,
    pregunta: str,
    modelo: str | None = None,
    max_iteraciones: int = MAX_ITERACIONES,
    nombres_tools: list[str] | None = None,
    agente: Any = None,
) -> AsyncIterator[Evento]:
    """Corre un ReAct y emite eventos del contrato. No emite `inicio` ni `fin`.

    Quien llama decide cómo enmarcarlo: N4 lo enmarca como run principal, N5 lo
    enmarca como sub-run dentro de un `sub_evento`.

    `agente` permite pasar un grafo ya construido. Existe para el notebook: el
    participante escribe la llamada a `create_react_agent` con sus propias manos
    —que es el punto del nivel 4— y esta función se encarga del resto.
    """
    if agente is None:
        agente = construir_agente(tools, system_prompt, modelo)
    declaradas = nombres_tools or [getattr(t, "__name__", str(t)) for t in tools]

    historial: list[dict] = [
        {"rol": "system", "contenido": recortar(system_prompt)},
        {"rol": "user", "contenido": pregunta},
    ]
    iteraciones = 0
    ultimo_ms = ej.emisor.ms_transcurridos
    texto_final = ""
    limite_alcanzado = False

    async def arrancar():
        return agente.astream(
            {"messages": [{"role": "user", "content": pregunta}]},
            stream_mode="updates",
            # Holgura sobre el tope propio: el corte lo hace este bucle, con un
            # `aviso` explícito, no una excepción de LangGraph a media demo.
            config={"recursion_limit": max_iteraciones * 2 + 6},
        )

    stream = await con_reintentos(arrancar, nivel=ej.nivel_id)

    async for actualizacion in stream:
        for _nodo, estado in (actualizacion or {}).items():
            if not isinstance(estado, dict):
                continue
            for mensaje in estado.get("messages", []) or []:
                tipo = getattr(mensaje, "type", None)

                if tipo == "ai":
                    n = ej.proxima_llamada()
                    yield ej.ev(
                        "llm_request",
                        n_llamada=n,
                        mensajes=mensajes_publicables(list(historial)),
                        tools_declaradas=declaradas,
                    )
                    tin, tout = _tokens(mensaje)
                    ej.contar_tokens(tin, tout)
                    llamadas = list(getattr(mensaje, "tool_calls", []) or [])
                    ahora = ej.emisor.ms_transcurridos
                    contenido = mensaje.content if isinstance(mensaje.content, str) else ""
                    yield ej.ev(
                        "llm_response",
                        n_llamada=n,
                        texto=contenido or None,
                        hay_tool_calls=bool(llamadas),
                        tokens_in=tin,
                        tokens_out=tout,
                        ms=max(ahora - ultimo_ms, 0),
                    )
                    ultimo_ms = ahora

                    # El "Thought" del patrón ReAct. Puede venir vacío: los modelos
                    # de tool calling no siempre verbalizan el razonamiento. Se
                    # emite vacío en lugar de fabricarlo (spec 04).
                    if llamadas:
                        yield ej.ev("pensamiento", texto=contenido.strip())

                    for i, tc in enumerate(llamadas):
                        ej.llamadas_tools += 1
                        yield ej.ev(
                            "tool_call",
                            id_llamada=str(tc.get("id") or f"call_{i}"),
                            nombre=str(tc.get("name") or "?"),
                            argumentos=dict(tc.get("args") or {}),
                            crudo=_crudo_de(mensaje, i, tc),
                        )
                    historial.append({"rol": "assistant", "contenido": contenido})
                    if llamadas:
                        iteraciones += 1
                    else:
                        texto_final = contenido

                elif tipo == "tool":
                    ahora = ej.emisor.ms_transcurridos
                    bruto = mensaje.content
                    try:
                        resultado = json.loads(bruto) if isinstance(bruto, str) else bruto
                    except (json.JSONDecodeError, TypeError):
                        resultado = bruto
                    filas = None
                    if isinstance(resultado, dict):
                        for clave in ("items", "serie", "cola", "ordenes", "filas"):
                            if isinstance(resultado.get(clave), list):
                                filas = len(resultado[clave])
                                break
                    es_error = getattr(mensaje, "status", None) == "error"
                    yield ej.ev(
                        "tool_result",
                        id_llamada=str(getattr(mensaje, "tool_call_id", "") or "?"),
                        nombre=str(getattr(mensaje, "name", "") or "?"),
                        resultado=resultado,
                        filas=filas,
                        ms=max(ahora - ultimo_ms, 0),
                        error=str(bruto) if es_error else None,
                    )
                    ultimo_ms = ahora
                    historial.append(
                        {"rol": "tool", "contenido": bruto if isinstance(bruto, str) else str(bruto)}
                    )

        if iteraciones >= max_iteraciones:
            limite_alcanzado = True
            break

    if limite_alcanzado:
        yield ej.ev(
            "aviso",
            gravedad="alerta",
            mensaje=(
                f"Se alcanzó el tope de {max_iteraciones} iteraciones. El agente "
                "responde con lo que alcanzó a averiguar. Un agente sin tope se "
                "cuelga; con tope, degrada."
            ),
        )
        if not texto_final:
            texto_final = (
                "No terminé de resolverlo dentro del límite de iteraciones. "
                "Esto es lo que alcancé a consultar; conviene acotar la pregunta."
            )

    ej.respuesta_final = texto_final
