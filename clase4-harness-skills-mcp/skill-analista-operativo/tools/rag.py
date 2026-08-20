"""Tool de documentos — recuperación RAG contra el vector store de OpenAI.

La Skill "analista operativo" llama a `retrieve_docs(pregunta, top_k)` cuando
la pregunta pide un procedimiento, política o manual. Esta función usa el
SDK de OpenAI para buscar en el vector store ya configurado en la cuenta
de OpenAI de la agencia — **no se construye ni se levanta ningún RAG local**.

El vector store (`OPENAI_VECTOR_STORE_ID`) ya está indexado con el corpus
sintético de documentos de Bios (políticas, manuales, procedimientos) que
se subió una sola vez. La Skill solo recupera — no indexa.

Contrato:
    retrieve_docs(pregunta: str, top_k: int = 4) -> list[dict]

Cada dict del resultado:
    {"id": str, "texto": str, "score": float,
     "doc_fuente": str, "dominio": str}

Si la API de OpenAI no responde (sin credenciales, sin red, vector store
no encontrado), degrada con un mensaje legible — la Skill debe responder
"no encontré documentación sobre eso".
"""

from __future__ import annotations

import os
from typing import Any

_VECTOR_STORE_ID = os.getenv(
    "OPENAI_VECTOR_STORE_ID",
    "vs_6a7dc97b07ac8191aa9240583a27c133",
)
_TOP_K_DEFAULT = int(os.getenv("RAG_TOP_K", "4"))
_DOMINIOS_VALIDOS = {"mant", "comp", "logi", "prod"}


def retrieve_docs(
    consulta: str,
    dominios: list[str] | None = None,
    top_k: int = _TOP_K_DEFAULT,
) -> list[dict[str, Any]]:
    """Recupera los fragmentos de documentos más relevantes para una consulta.

    Usa esta herramienta cuando la pregunta pida un procedimiento, una política
    o un manual interno. NO la uses para cifras operativas (inventario, demanda,
    fallas, pedidos) — para eso está `bios_ops.py`.

    La búsqueda se hace contra el vector store de OpenAI ya indexado con el
    corpus de documentos de Bios. No se construye ni se levanta ningún RAG
    local — el índice vive en OpenAI.

    IMPORTANTE — `consulta` no es la pregunta literal del usuario:
    reformulá con el vocabulario del documento. Ej.: el usuario dice
    "¿cada cuánto reviso el molino?" → pasás "periodicidad inspección molino
    criticidad alta". El documento no habla el lenguaje del usuario; hablá
    el del documento.

    Args:
        consulta: La pregunta reformulada con vocabulario documental.
        dominios: Opcional. Lista de dominios para filtrar. Valores válidos:
            "mant" (Mantenimiento), "comp" (Compras), "logi" (Logística),
            "prod" (Producción/TD). Si la pregunta cruza áreas, incluí varios.
            Si no se pasa, busca en todo el corpus.
        top_k: Cuántos fragmentos devolver. Por defecto 4.

    Returns:
        Una lista de fragmentos, cada uno con: id, texto, score, doc_fuente,
        dominio. Si la API de OpenAI no responde, devuelve una lista con un
        único marcador de error — la Skill debe responder
        "no encontré documentación sobre eso".
    """
    if not consulta:
        return [{"error": "consulta vacía"}]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return [{
            "error": "no_encontrado",
            "mensaje": (
                "No encuentro OPENAI_API_KEY en el entorno. "
                "Configurá la variable en el .env para consultar el vector "
                "store de documentos de Bios."
            ),
        }]

    try:
        from openai import OpenAI
    except ImportError:
        return [{
            "error": "no_encontrado",
            "mensaje": (
                "El paquete `openai` no está instalado. "
                "Corré `pip install openai` en el venv de la Skill."
            ),
        }]

    # Filtro por dominio — mismo patrón que el nodo rag_openai de S3.
    dominios_filtrados: list[str] | None = None
    if dominios:
        dominios_filtrados = [
            d.strip().lower() for d in dominios
            if d.strip().lower() in _DOMINIOS_VALIDOS
        ]
        if not dominios_filtrados:
            dominios_filtrados = None  # no había ninguno válido → sin filtro

    try:
        client = OpenAI(api_key=api_key)
        kwargs: dict[str, Any] = {
            "vector_store_id": _VECTOR_STORE_ID,
            "query": consulta,
            "top_k": top_k,
        }
        if dominios_filtrados:
            kwargs["filters"] = {
                "type": "in",
                "key": "dominio",
                "value": dominios_filtrados,
            }
        result = client.vector_stores.search(**kwargs)
    except Exception as e:
        return [{
            "error": "no_encontrado",
            "mensaje": (
                f"No pude consultar el vector store de OpenAI "
                f"({_VECTOR_STORE_ID}). Detalle: {e}"
            ),
        }]

    return _normalizar(result)


def _normalizar(result: Any) -> list[dict[str, Any]]:
    """Convierte la respuesta de OpenAI al contrato de la Skill."""
    out: list[dict[str, Any]] = []
    # La respuesta de vector_stores.search trae .data con cada hit.
    # Cada hit tiene .content (lista de fragmentos con .text) y .attributes.
    hits = getattr(result, "data", None) or getattr(result, "results", None) or []
    for h in hits:
        # content puede ser una lista de fragmentos con .text
        content = getattr(h, "content", None)
        if isinstance(content, list) and content:
            texto = getattr(content[0], "text", "") or ""
        elif isinstance(content, str):
            texto = content
        else:
            texto = getattr(h, "text", "") or ""

        attrs = getattr(h, "attributes", {}) or {}
        out.append({
            "id": getattr(h, "id", "") or attrs.get("id", ""),
            "texto": texto,
            "score": round(float(getattr(h, "score", 0.0) or 0.0), 4),
            "doc_fuente": (
                attrs.get("doc_fuente")
                or attrs.get("doc")
                or attrs.get("documento")
                or attrs.get("file_name")
                or ""
            ),
            "dominio": attrs.get("dominio", "") or "",
        })
    if not out:
        out = [{
            "error": "no_encontrado",
            "mensaje": (
                "El vector store respondió sin resultados para esa pregunta. "
                "Revisá que el corpus esté indexado en el vector store "
                f"{_VECTOR_STORE_ID}."
            ),
        }]
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  CLI de verificación — `python -m tools.rag --probar`
# ─────────────────────────────────────────────────────────────────────────────


def _main() -> None:
    import sys
    if "--probar" in sys.argv:
        consulta = "umbral vibración molino criticidad alta procedimiento"
        dominios = ["mant"]
        print(f"› retrieve_docs(consulta={consulta!r}, dominios={dominios})")
        print(f"  vector store: {_VECTOR_STORE_ID}")
        chunks = retrieve_docs(consulta=consulta, dominios=dominios)
        if chunks and "error" in chunks[0]:
            print(f"  ⚠ {chunks[0].get('mensaje', chunks[0])}")
            print("  (esperado si OPENAI_API_KEY no está configurada)")
        else:
            for c in chunks:
                print(f"  · {c.get('doc_fuente')} (score={c.get('score')})")
                print(f"    {c.get('texto', '')[:120]}...")
        print("\n✓ rag.py responde (o degrada con mensaje legible).")


if __name__ == "__main__":
    _main()
