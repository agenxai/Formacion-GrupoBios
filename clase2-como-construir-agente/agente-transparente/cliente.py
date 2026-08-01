"""El cerebro del agente: configuración del cliente Azure OpenAI.

Spec 02 · ADR-001. Bios usa Azure OpenAI como puerta corporativa a los modelos. Lo
que se ve en clase es lo que van a usar en sus proyectos: no se mezcla con OpenAI
directo.

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
from langchain_openai import AzureChatOpenAI

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

cliente = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    temperature=0.2,
)
"""El cerebro. Una instancia de AzureChatOpenAI lista para que el loop la llame.

`temperature=0.2` reduce el riesgo de invención de cifras operativas — la clase 1
ya mostró que un LLM sin datos inventa con seguridad; aquí queremos que razonne,
no que imagine.
"""

__all__ = ["cliente"]