"""Ensambla el agente: cliente + tools + memoria + loop, en una clase.

Spec 02 · ADR-002. Esta es la pieza que la Parte 1b reemplaza con 3 líneas de
`create_react_agent`. La intención aquí es que el participante VEA la composición:
el agente es la suma de cliente (cerebro) + memoria + loop. Nada más.

Uso:
    from agente import AgenteReAct
    a = AgenteReAct()
    print(a.preguntar("¿Cuánto maíz le queda a Itagüí?"))
"""

from __future__ import annotations

from cliente import cliente
from loop import react
from memoria import Memoria
from tools import TOOLS_FUNC

# La identidad del agente. Es el system prompt — lo que le dice al LLM qué es y
# cómo debe comportarse. Se proyecta en clase y se discute: prohibir inventar
# cifras operativas es la salvaguarda más barata que hay.
SYSTEM_PROMPT = """Eres un asistente de operaciones de Grupo Bios. Tu trabajo es
responder preguntas de negocio sobre inventario, demanda, logística y
mantenimiento usando las herramientas que se te dan.

REGLAS:
- NUNCA inventes una cifra operativa. Si una herramienta no te da el dato, di
  "no tengo esa información" y explica qué herramienta se necesitaría.
- Usa las herramientas SIEMPRE que la pregunta requiera un dato del negocio.
  No respondas con conocimiento general.
- Si la pregunta es ambigua, pide aclaración.
- Responde en español, con unidades (toneladas, días, COP).
- Eres exacto. No redondees sin decirlo.
"""


class AgenteReAct:
    """Un agente ReAct con memoria conversacional.

    Composición:
        cerebro    ← cliente (AzureChatOpenAI)
        memoria    ← buffer de mensajes en formato OpenAI
        herramientas ← las 4 tools de bios_ops.db
        decisión   ← el ciclo ReAct ( Thought → Action → Observation )
    """

    def __init__(self):
        self.cliente = cliente
        self.memoria = Memoria(system_prompt=SYSTEM_PROMPT)
        self.tools = TOOLS_FUNC

    def preguntar(self, pregunta: str) -> str:
        """Envía una pregunta al agente y devuelve su respuesta final."""
        return react(self.cliente, self.memoria, pregunta)

    def historial(self) -> list[dict]:
        """Expone los mensajes internos — para depurar o mostrar en clase."""
        return self.memoria.mensajes()


__all__ = ["AgenteReAct", "SYSTEM_PROMPT"]