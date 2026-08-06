"""Interfaz de terminal: conversa con el agente en un bucle de `input()`.

Spec 02. La interfaz es deliberadamente simple — un `while` con `input()`. Es
para que se vea que la interfaz (terminal, web, API) es lo de menos: el agente
recibe un string y devuelve uno. Todo lo interesante vive en `agente.py`.

Uso (el guion en el nombre de carpeta impide `-m`, así que se corre directo):
    cd agente-transparente
    python chat.py            # conversa
    python chat.py --demo     # corre los 4 turnos de la conversación insignia solo

Escribe una pregunta y Enter. Escribe `salir` para terminar.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Agrega el directorio de este paquete al path para que `from agente import ...`
# funcione al correr con `python -m agente-transparente.chat`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agente import AgenteReAct  # noqa: E402

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  Agente ReAct · bios_ops.db  ·  Azure OpenAI               ║
║  Construido pieza por pieza. Prueba la conversación.        ║
╠══════════════════════════════════════════════════════════════╣
║  Sugerencia: itera estos 4 turnos (teoría de la clase 1):    ║
║   1. ¿Cuánto maíz le queda a la planta de Itagüí?            ║
║   2. ¿Y me alcanza para la demanda proyectada de esta semana? ║
║   3. ¿Hay algún equipo de esa misma planta en riesgo?        ║
║   4. ¿Cómo va el pedido PD-24-00871?                        ║
╚══════════════════════════════════════════════════════════════╝

Escribe "salir" para terminar. Llama con --demo para correr esos 4 turnos solo.
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


def main() -> None:
    print(_AVISO, end="\n\n")
    print(BANNER)

    agente = AgenteReAct()

    if "--demo" in sys.argv:
        # Modo demo: corre los 4 turnos sin intervención.
        for pregunta in _DEMO:
            agente.preguntar(pregunta)
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
        agente.preguntar(pregunta)


if __name__ == "__main__":
    main()