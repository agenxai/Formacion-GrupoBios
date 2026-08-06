"""El cerebro del agente: configuración del cliente Azure AI Foundry.

Spec 02 · ADR-001. Bios usa Azure AI Foundry como puerta corporativa a los modelos.
Lo que se ve en clase es lo que van a usar en sus proyectos: no se mezcla con OpenAI
directo.

El endpoint de Foundry (`*.services.ai.azure.com/openai/v1`) es compatible con la
API de OpenAI, así que lo consumimos con `ChatOpenAI` apuntando `base_url` al
endpoint y usando el nombre del *deployment* como `model`. Es el mismo contrato que
`AzureChatOpenAI` (mensajes en/out, tool_calls, bind_tools), solo que por la ruta
de Foundry en vez de la del Azure OpenAI clásico.

Uso:
    from cliente import cliente
    resp = cliente.chat.completions.create(model=..., messages=[...])

Configuración: copia `.env.example` a `.env` y completa las tres variables
obligatorias. El script falla aquí al arrancar si falta alguna — no en el minuto 10
de la demo.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Carga el .env del directorio del proyecto (sube dos niveles desde este archivo).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# Plantilla de aviso: la falta de credenciales se detecta al cargar, no en runtime.
_REQUERIDAS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
_faltan = [k for k in _REQUERIDAS if not os.getenv(k)]
if _faltan:
    raise SystemExit(
        "Faltan variables de entorno requeridas: "
        + ", ".join(_faltan)
        + ". Copia .env.example a .env y complétalas."
    )

cliente = ChatOpenAI(
    base_url=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    temperature=0.2,
)
"""El cerebro. Una instancia de ChatOpenAI contra el endpoint de Foundry de Bios,
lista para que el loop la llame.

`temperature=0.2` reduce el riesgo de invención de cifras operativas — la clase 1
ya mostró que un LLM sin datos inventa con seguridad; aquí queremos que razonne,
no que imagine.
"""

__all__ = ["cliente"]