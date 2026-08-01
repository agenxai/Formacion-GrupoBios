"""EL MISMO agente con framework — todo lo que escribimos a mano, en 3 líneas.

Spec 02 · ADR-002. Esta carpeta comparte `cliente.py`, `tools.py` y `memoria.py`
**idénticos** con `agente-transparente/` — para que al proyectar los dos `agente.py`
lado a lado, la diferencia visual sea la lección: el framework abstrae el loop, el
dispatch y el manejo de errores, y nada más.

Uso:
    cd agente-framework
    python chat.py            # conversa
    python chat.py --demo      # los 4 turnos solos
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from cliente import cliente
from tools import (
    consultar_inventario, consultar_demanda, estado_pedido, historial_fallas,
)

# El system prompt es el MISMO de `agente-transparente/agente.py`. Acá se duplica
# (no se importa de la otra carpeta) para que el diff entre los dos `agente.py`
# se reduzca a "cómo se construye el agente", no a "de dónde viene el prompt".
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


def construir_agente():
    """Construye el mismo agente ReAct en 1 línea de framework.

    Lo que `create_react_agent` encapsula:
      - el ciclo Thought → Action → Observation (en la Parte 1a era `loop.py`)
      - el dispatch de tools (en la Parte 1a era `dispatch`)
      - el manejo de errores y el límite de iteraciones
      - el agregado de mensajes a la memoria

    Lo que NO encapsula (sigue siendo nuestro):
      - el cliente Azure OpenAI → `cliente.py`, igual
      - las funciones y docstrings de tools → `tools.py`, igual
      - la decisión de cuáles tools y cuál prompt → la tomamos acá
    """
    # Las 4 funciones se envuelven en StructuredTool. LangChain lee las
    # anotaciones de tipo y la docstring (¡la docstring sigue siendo el prompt!).
    herramientas = [
        StructuredTool.from_function(f) for f in (
            consultar_inventario, consultar_demanda,
            estado_pedido, historial_fallas,
        )
    ]
    return create_react_agent(cliente, herramientas, prompt=SYSTEM_PROMPT)


__all__ = ["construir_agente", "SYSTEM_PROMPT"]