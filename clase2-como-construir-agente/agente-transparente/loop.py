"""El ciclo ReAct a mano — pensamiento → acción → observación.

Spec 02 · ADR-002. Esta es la pieza que la Parte 1b reemplaza por
`create_react_agent(...)`. Al proyectar los dos archivos lado a lado, la lección
es inevitable: el framework abstrae exactamente lo que escribimos acá.

Contrato (spec 04):
    react(cliente, tools, memoria, pregunta) -> str

Pasos:
    1. Agrega la pregunta del usuario a la memoria.
    2. Llama al LLM con la lista de mensajes + los schemas de tools.
    3. Si la respuesta contiene tool_calls:
         a. Imprime [Thought] y [Action].
         b. Para cada tool_call: ejecuta la tool vía `dispatch`.
         c. Agrega cada resultado a la memoria como mensaje 'tool'.
         d. Imprime [Observation].
         e. Vuelve al paso 2.
    4. Si no hay tool_calls: es la respuesta final.
         a. Agrega la respuesta a la memoria como 'assistant'.
         b. Imprime [Respuesta] y devuelve el texto.

Límites:
    MAX_ITERACIONES = 5 — si el agente no resuelve en 5 vueltas, se corta.
    El bloque try/except evita que un fallo de API tumbe el script.
"""

from __future__ import annotations

import json
from typing import Any

from memoria import Memoria
from tools import SCHEMAS, dispatch

MAX_ITERACIONES = 5


def react(cliente: Any, memoria: Memoria, pregunta: str) -> str:
    """Ejecuta el ciclo ReAct sobre una pregunta. Devuelve el texto final."""
    memoria.agregar("user", pregunta)
    print(f"\n[user] {pregunta}")

    # `bind_tools` adjunta los schemas al LLM para que pueda decir "quiero usar X".
    # Llamarlo fuera del bucle evita reatamar las tools en cada iteración.
    llm = cliente.bind_tools(SCHEMAS)

    for iteracion in range(1, MAX_ITERACIONES + 1):
        print(f"\n── iteración {iteracion} ──")

        try:
            respuesta = llm.invoke(memoria.mensajes())
        except Exception as e:
            # Si Azure se cae, no propagamos un stack trace. El agente informa.
            print(f"[error] La llamada al LLM falló: {e}")
            memoria.agregar(
                "assistant",
                "No pude completar la consulta porque el servicio de IA "
                "no respondió. Intenta de nuevo en un momento.",
            )
            return "Fallo en la llamada al LLM."

        # El LLM puede responder con texto final (sin tool_calls) o pedir tools.
        msg = respuesta  # Chat AIMessage de langchain-openai
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            # Respuesta final — ya no necesita más tools.
            texto = msg.content or ""
            memoria.agregar("assistant", texto)
            print(f"\n[Respuesta] {texto}")
            return texto

        # Hay tool_calls: el LLM decidió qué herramienta usar.
        print(f"[Thought] {msg.content or '(sin texto explicativo)'}")

        # Agregamos el mensaje 'assistant' tal cual lo devolvió el LLM al
        # buffer, en formato OpenAI. La próxima iteración lo necesita para
        # saber que el modelo ya pidió estas tools y espere sus resultados.
        memoria.agregar(
            "assistant",
            content=msg.content or "",
            tool_calls=[
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"], ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ],
        )

        # --- Ejecución de cada tool llamada ---
        for tc in tool_calls:
            nombre = tc["name"]
            args = tc["args"]
            # Formatea los argumentos legiblemente para imprimir.
            args_str = json.dumps(args, ensure_ascii=False)
            print(f"[Action]   {nombre}({args_str})")

            # El dispatch ejecuta la función y devuelve un dict.
            try:
                resultado = dispatch(nombre, args)
            except Exception as e:
                resultado = {"error": f"Fallo ejecutando {nombre}: {e}"}

            # Imprime la observación —recortada a 300 chars si es muy larga— para
            # que se vea en terminal sin llenar media pantalla.
            obs_str = json.dumps(resultado, ensure_ascii=False, default=str)
            print(f"[Observation] {obs_str[:300]}{'…' if len(obs_str) > 300 else ''}")

            # Agrega el resultado a la memoria como mensaje 'tool'. El LLM lo
            # necesita en el siguiente turno para dar la respuesta final o pedir
            # otra tool.
            memoria.agregar(
                "tool",
                json.dumps(resultado, ensure_ascii=False, default=str),
                tool_call_id=tc["id"],
            )

    # Si llegamos aquí, el agente se pasó de iteraciones.
    print(f"[corte] El agente no resolvió en {MAX_ITERACIONES} iteraciones.")
    memoria.agregar("assistant", "No pude resolver la consulta en el número "
                     "máximo de intentos. Intenta reformular la pregunta.")
    return "Agente cortado por máximo de iteraciones."


__all__ = ["react", "MAX_ITERACIONES"]