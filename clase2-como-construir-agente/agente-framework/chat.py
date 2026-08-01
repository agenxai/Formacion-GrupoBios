"""Interfaz de terminal para el agente con framework.

Idéntico a `agente-transparente/chat.py` salvo el `agente.preguntar(...)`: como
el resultado de `create_react_agent` es un grafo, la llamada es `.invoke(...)`
con un mensaje de usuario en lugar de `react(cliente, memoria, pregunta)`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agente import construir_agente  # noqa: E402

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  Agente ReAct · bios_ops.db  ·  Azure OpenAI  + LangGraph  ║
║  MISMO agente construido con framework. Compara con el     ║
║  transparente.                                             ║
╠══════════════════════════════════════════════════════════════╣
║  Sugerencia: los mismos 4 turnos:                            ║
║   1. ¿Cuánto maíz le queda a la planta de Itagüí?            ║
║   2. ¿Y me alcanza para la demanda proyectada de esta semana? ║
║   3. ¿Hay algún equipo de esa misma planta en riesgo?        ║
║   4. ¿Cómo va el pedido PD-24-00871?                        ║
╚══════════════════════════════════════════════════════════════╝

Escribe "salir" para terminar. Llama con --demo para los 4 turnos solos.
"""

_AVISO = (
    "Datos: bios_ops.db es sintética — no representa datos reales de Grupo Bios."
)

_DEMO = [
    "¿Cuánto maíz le queda a la planta de Itagüí?",
    "¿Y me alcanza para la demanda proyectada de esta semana?",
    "¿Hay algún equipo de esa misma planta en riesgo de falla?",
    "¿Cómo va el pedido PD-24-00871?",
]


def _preguntar(agente, pregunta: str) -> str:
    """Adapta la llamada al grafo de LangGraph.

    La abstracción trae su propio formato de entrada/salida: dict con `messages`.
    En el transparente era `react(cliente, memoria, pregunta)` — son 2 firmas
    distintas para el mismo concepto. Aprendérsela es el costo del framework.
    """
    resultado = agente.invoke({"messages": [{"role": "user", "content": pregunta}]})
    # El último mensaje es la respuesta final del agente.
    ultimo = resultado["messages"][-1]
    return getattr(ultimo, "content", str(ultimo))


def main() -> None:
    print(_AVISO, end="\n\n")
    print(BANNER)

    agente = construir_agente()

    if "--demo" in sys.argv:
        for pregunta in _DEMO:
            print(f"\n[user] {pregunta}")
            respuesta = _preguntar(agente, pregunta)
            print(f"\n[Respuesta] {respuesta}")
        print("\n[fin del demo]")
        return

    while True:
        try:
            pregunta = input("\ntú › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n[salida]")
            break
        if not pregunta:
            continue
        if pregunta.lower() in {"salir", "exit", "quit"}:
            print("\n[salida]")
            break
        respuesta = _preguntar(agente, pregunta)
        print(f"\n[Respuesta] {respuesta}")


if __name__ == "__main__":
    main()