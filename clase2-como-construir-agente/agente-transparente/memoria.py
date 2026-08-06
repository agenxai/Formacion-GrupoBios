"""La memoria del agente: un buffer de mensajes en formato OpenAI.

Spec 02 · ADR-004. La memoria es una lista de mensajes, no una abstracción. Se
envuelve en una clase para que `agente.py` se lea como prosa: `memoria.agregar(...)`
y `memoria.mensajes()`. El punto pedagógico no es la clase —es que la memoria ES
esa lista, y la clase solo la envuelve para que se lea bien.

No hay persistencia entre ejecuciones: al cerrar el script, el buffer se pierde.
La persistencia es tema de producción → acompañamiento (S5-S7). Se declara fuera
de alcance en la spec 01.

Uso:
    mem = Memoria(system_prompt="...")
    mem.agregar("user", "¿Cuánto maíz le queda?")
    respuesta = mem.mensajes()  # lista lista para pasársela al cliente
"""

from __future__ import annotations


class Memoria:
    """Un buffer de mensajes en formato OpenAI.

    Formato que devuelve `mensajes()`:
        [{"role": "system", "content": "..."},
         {"role": "user",   "content": "..."},
         {"role": "assistant", "content": "..."},
         {"role": "tool", "tool_call_id": "...", "content": "..."}]
    """

    def __init__(self, system_prompt: str = ""):
        """Arranca con el mensaje de sistema (la identidad y reglas del agente)."""
        self._mensajes: list[dict] = (
            [{"role": "system", "content": system_prompt}] if system_prompt else []
        )

    def agregar(self, rol: str, contenido: str | None = None, **extra) -> None:
        """Agrega un mensaje.

        rol: 'system' | 'user' | 'assistant' | 'tool'.
        contenido: el texto del mensaje.
        **extra: campos adicionales (ej. `tool_calls`, `tool_call_id` para assistant
                 cuando pide una tool, o el `tool_call_id` y `content` para 'tool').
        """
        msg = {"role": rol}
        if contenido is not None:
            msg["content"] = contenido
        msg.update(extra)
        self._mensajes.append(msg)

    def mensajes(self) -> list[dict]:
        """Devuelve la lista —la memoria es eso: se pasa al LLM en la próxima llamada."""
        return self._mensajes

    def __len__(self) -> int:
        return len(self._mensajes)

    def __repr__(self) -> str:
        return f"<Memoria con {len(self._mensajes)} mensajes>"


__all__ = ["Memoria"]