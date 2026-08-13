# ──────────────────────────────────────────────────────────────────────────
#  app/backend/datos.py
#  Clase 3 · RAG — Cargador de data/*.json pre-bakeados.
#
#  Lee del sistema de archivos (no hace I/O de red) los archivos
#  producidos por `scripts/prebakear.py`. Ver spec 02 § "El contrato de
#  datos pre-bakeados" y spec 04 § "Backend — Endpoints FastAPI".
# ──────────────────────────────────────────────────────────────────────────
"""Cargador de datos freezeados para la app visual."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _cargar(nombre: str) -> Any:
    ruta = DATA_DIR / nombre
    if not ruta.exists():
        # No se verifica aquí — el backend lo reporta en /api/salud.
        # Para evitar que el servidor explote al arrancar si faltan
        # archivos generados, devolvemos None y el caller reporta.
        return None
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def cargar_corpus() -> dict[str, Any] | None:
    """Corpus completo con documentos, familias, preguntas semilla y
    anomalías. Si falta, devuelve None."""
    return _cargar("corpus.json")


@lru_cache(maxsize=1)
def cargar_chunks() -> list[dict[str, Any]] | None:
    """Lista plana de chunks (con texto, dominio, anomalias, etc.)."""
    return _cargar("chunks.json")


@lru_cache(maxsize=1)
def cargar_similitudes() -> dict[str, Any] | None:
    """Matriz top-K de similitudes chunk×chunk y ranking query×chunk."""
    return _cargar("similitudes.json")


@lru_cache(maxsize=1)
def cargar_proyeccion() -> dict[str, Any] | None:
    """Coordenadas 3D de cada chunk para Plotly + método (umap/pca)."""
    return _cargar("proyeccion_3d.json")


@lru_cache(maxsize=1)
def cargar_manifest() -> dict[str, Any] | None:
    """Manifest: fecha, modelo, semilla… Candado de honestidad."""
    return _cargar("_manifest.json")


@lru_cache(maxsize=1)
def cargar_ultima_respuesta_webhook() -> dict[str, Any] | None:
    """Última respuesta correcta del webhook pre-grabada
    (plan C del riesgo 2 de spec 07)."""
    return _cargar("last_response.json")


# ──────────────────────────────────────────────────────────────────────────
#  Embeddings — el frontend recibe solo los primeros N valores (preview).
#  El vector completo se expone via /api/embeddings/<chunk_id> (spec 04
#  backend endpoints, embargo útil). Esto escala bien sea 12 o 200 chunks.
# ──────────────────────────────────────────────────────────────────────────
EMBEDDINGS_PREVIEW_SIZE = 16

_embeddings_cache: list[list[float]] | None = None


def _cargar_embeddings() -> list[list[float]] | None:
    global _embeddings_cache
    if _embeddings_cache is not None:
        return _embeddings_cache
    data = _cargar("embeddings.json")
    if data is None:
        return None
    _embeddings_cache = data
    return _embeddings_cache


def cargar_embeddings_preview() -> list[list[float]] | None:
    """Devuelve los primeros 16 valores de cada vector."""
    emb = _cargar_embeddings()
    if emb is None:
        return None
    return [v[:EMBEDDINGS_PREVIEW_SIZE] for v in emb]


def cargar_embedding_chunk(chunk_id: int) -> list[float] | None:
    """Devuelve el vector completo (1536 dim) de un chunk. None si no existe."""
    emb = _cargar_embeddings()
    if emb is None or chunk_id < 0 or chunk_id >= len(emb):
        return None
    return emb[chunk_id]


# ──────────────────────────────────────────────────────────────────────────
#  Compuesto para /api/datos: todo lo que la pantalla necesita para
#  arrancar, sin vector completo.
# ──────────────────────────────────────────────────────────────────────────
def paquete_datos() -> dict[str, Any]:
    """
    Devuelve el paquete completo que el frontend pide al cargar la app.

    ~todos los recursos para pintar pantallas 1-6: chunks, corpus,
    similitudes, proyeccion 3D, manifest, embeddings_preview, ultima
    respuesta webhook (plan C).

    Si faltan datos, el paquete devuelve el campo como None y `listo: False`.
    El frontend decide qué mostrar.
    """
    chunks = cargar_chunks()
    corpus = cargar_corpus()
    similitudes = cargar_similitudes()
    proyeccion = cargar_proyeccion()
    manifest = cargar_manifest()
    emb_preview = cargar_embeddings_preview()
    last_resp = cargar_ultima_respuesta_webhook()

    listo = (chunks is not None
             and corpus is not None
             and similitudes is not None
             and proyeccion is not None)

    return {
        "listo": listo,
        "chunks": chunks,
        "corpus": corpus,
        "similitudes": similitudes,
        "proyeccion": proyeccion,
        "manifest": manifest,
        "embeddings_preview": emb_preview,
        "ultima_respuesta_webhook": last_resp,
        "embedding_dim_completa": 1536
    }


def health() -> dict[str, Any]:
    """Reporta el estado del backend para /api/salud."""
    chunks = cargar_chunks()
    manifest = cargar_manifest()
    return {
        "modo": "vivo",
        "listo": chunks is not None,
        "n_chunks": len(chunks) if chunks else 0,
        "modelo_embeddings": manifest.get("modelo_embeddings", "")
        if manifest else "",
        "fecha_prebakeo": manifest.get("fecha_generacion", "") if manifest else "",
        "version": "3.0.0"
    }