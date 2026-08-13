# ──────────────────────────────────────────────────────────────────────────
#  app/backend/main.py
#  Clase 3 · RAG — Backend FastAPI del tablero.
#
#  Sirve el frontend `rag-class.html` (en la raíz del proyecto — es la
#  maqueta curada por el usuario) y los endpoints del contrato (spec 04).
#  Sin lógica de RAG aquí: todo viene freezeado en app/data/*.json.
#  El único llamado vivo es el proxy webhook (spec 07, riesgo 2).
# ──────────────────────────────────────────────────────────────────────────
"""Servidor FastAPI del tablero de la clase 3."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .datos import (
    cargar_embedding_chunk,
    cargar_manifest,
    cargar_proyeccion,
    paquete_datos,
    health as datos_health,
)
from .webhook import llamar_agente, webhook_url_configurada

load_dotenv()

# raíz del proyecto — clase3-rag/
RAIZ = Path(__file__).resolve().parent.parent.parent
# Frontend: archivo único self-contained (el artefacto curado del usuario).
FRONTEND_HTML = RAIZ / "rag-class.html"
# assets compartidos (logo Bios, fuentes woff2 si llegan a colocarse…)
ASSETS_DIR = RAIZ / "app" / "frontend" / "assets"

app = FastAPI(title="Clase 3 · RAG · Tablero", version="3.0.0")


# ──────────────────────────────────────────────────────────────────────────
#  API.
# ──────────────────────────────────────────────────────────────────────────

@app.get("/api/salud")
def salud() -> dict:
    """Estado del tablero. Lo primero que prueba el facilitador al arrancar."""
    base = datos_health()
    base["webhook_url_presente"] = webhook_url_configurada()
    base["webhook_listo_para_pantalla_7"] = webhook_url_configurada()
    return base


@app.get("/api/datos")
def datos() -> dict:
    """Paquete único para que el frontend pinte las pantallas con datos Bios."""
    return paquete_datos()


@app.get("/api/proyeccion")
def proyeccion() -> dict:
    """Coordenadas 3D de cada chunk + método."""
    p = cargar_proyeccion()
    if p is None:
        raise HTTPException(503, "proyeccion_3d.json no existe. "
                                  "Corré `python scripts/prebakear.py`.")
    return p


@app.get("/api/manifest")
def manifest() -> dict:
    """Candado de honestidad (fecha, modelo, semilla)."""
    m = cargar_manifest()
    if m is None:
        raise HTTPException(503, "_manifest.json no existe. "
                                  "Corré `python scripts/prebakear.py`.")
    return m


@app.get("/api/embeddings/{chunk_id}")
def embeddings(chunk_id: int) -> dict:
    """Vector completo (1536 dim) de un chunk, on demand."""
    v = cargar_embedding_chunk(chunk_id)
    if v is None:
        raise HTTPException(404, f"Embedding de chunk {chunk_id} no existe.")
    return {"chunk_id": chunk_id, "vector": v, "dim": len(v)}


@app.post("/api/webhook")
def webhook(body: dict) -> dict:
    """
    Proxy del webhook del agente Bios RAG. Devuelve el JSON del workflow.
    Si la URL no está configurada o el webhook tarda más de 10s, devuelve
    un error estructurado con el comando `curl` listo para probar.
    """
    pregunta = body.get("pregunta", "").strip()
    if not pregunta:
        raise HTTPException(400, "Falta 'pregunta' en el body.")
    return llamar_agente(pregunta)


# ──────────────────────────────────────────────────────────────────────────
#  Frontend — archivo único rag-class.html servido desde la raíz del repo.
#  Sin build step. Las fuentes vienen de Google Fonts (necesita internet
#  en clase), el resto es todo inline. Si en clase no hay internet, las
#  fuentes caen a fallbacks del sistema y la app sigue funcionando.
# ──────────────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    """Servir rag-class.html (artefacto curado por el usuario)."""
    if not FRONTEND_HTML.exists():
        raise HTTPException(500, f"Frontend no encontrado: {FRONTEND_HTML}")
    return FileResponse(FRONTEND_HTML, media_type="text/html")


# /assets/ — logo Bios + cualquier woff2 que se coloque vendorizado luego.
if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=ASSETS_DIR, html=False),
        name="assets"
    )


# Entrada uvicorn standalone (Plan C sin Docker — spec 07 riesgo 1).
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PUERTO_TABLERO", "8000")),
        reload=False,
        log_level="info"
    )