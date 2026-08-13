# ──────────────────────────────────────────────────────────────────────────
#  app/backend/webhook.py
#  Clase 3 · RAG — Proxy del webhook de n8n.
#
#  El navegador del facilitador (localhost:8000) no ataca CORS del webhook
#  público de n8n directamente: pasa por este proxy, que también evita que
#  un futuro token de auth viva en el JS del frontend (ADR-001 spec 04).
#
#  Ver spec 04 § "Backend — Endpoints FastAPI" y spec 07 § "Riesgo 2".
# ──────────────────────────────────────────────────────────────────────────
"""Cliente del webhook del agente Bios RAG."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
TIMEOUT = 10.0  # spec 04 CA-7.3: 10s


def webhook_url_configurada() -> bool:
    """Para /api/salud."""
    return bool(N8N_WEBHOOK_URL.strip())


def llamar_agente(pregunta: str) -> dict[str, Any]:
    """
    Llama al webhook del agente BIOS RAG. Devuelve un dict con:
      {"ok": True, "respuesta": ..., "citas": [...]}

    En caso de fallo devuelve:
      {"ok": False, "error": "<mensaje>", "curl": "<cmd para probar>"}
    """
    if not webhook_url_configurada():
        return {
            "ok": False,
            "error": (
                "N8N_WEBHOOK_URL no está configurada en .env. "
                "La pantalla 7 no puede llamar al agente de n8n sin esa URL."
            ),
            "curl": ""
        }

    payload = {"pregunta": pregunta}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(N8N_WEBHOOK_URL, json=payload)
        if response.status_code != 200:
            return {
                "ok": False,
                "error": f"HTTP {response.status_code} de n8n",
                "curl": _curl_cmd(pregunta),
                "status_code": response.status_code,
                "body": response.text[:1000]
            }
        data = response.json()
        # el webhook de la clase 3 devuelve {"respuesta": ..., "citas": [...]}
        return {
            "ok": True,
            "respuesta": data.get("respuesta", ""),
            "citas": data.get("citas", []),
            "status_code": 200,
            "curl": _curl_cmd(pregunta)
        }
    except httpx.TimeoutException:
        return {
            "ok": False,
            "error": (
                f"Timeout: el webhook no respondió en {TIMEOUT:.0f}s. "
                "Probablemente n8n está caído o el servicio Chroma no "
                "responde."
            ),
            "curl": _curl_cmd(pregunta)
        }
    except httpx.RequestError as e:
        return {
            "ok": False,
            "error": f"Error de conexión al webhook: {e}",
            "curl": _curl_cmd(pregunta)
        }


def _curl_cmd(pregunta: str) -> str:
    """Construye el comando curl para que el facilitador lo pruebe desde
    terminal (CA-7.4). Lo usamos tanto en error como en éxito — siempre
    queda accesible en el panel de conexión."""
    # Escapar comillas dobles dentro de la pregunta
    pregunta_esc = pregunta.replace('"', '\\"')
    return (
        f'curl -X POST {N8N_WEBHOOK_URL} \\\n'
        f'     -H "Content-Type: application/json" \\\n'
        f'     -d \'{{"pregunta": "{pregunta_esc}"}}\''
    )