#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────
#  scripts/prebakear.py
#  Clase 3 · RAG — Pipeline de pre-bakeo.
#
#  Lee `app/data/corpus.json`, parte en chunks, embeda con
#  `text-embedding-3-small` de Azure (una sola vez, en pre-prod),
#  calcula similitudes coseno, proyecta a 3D con UMAP y construye
#  `app/data/{chunks,embeddings,similitudes,proyeccion_3d,_manifest}.json`.
#
#  Ver spec 02 § "El contrato de datos pre-bakeados" y spec 03 § "El
#  pipeline de embeddings".
#
#  Determinista: con semilla 42 (UMAP + PCA) los outputs son byte-idénticos
#  en cualquier máquina para el mismo corpus + modelo de embeddings.
#
#  Validación: aborta si:
#    - Faltan credenciales Azure OpenAI.
#    - El número de embeddings no coincide con el de chunks.
#    - Algún embedding no es de 1536 dimensiones o es nulo.
#    - El coseno de un chunk consigo mismo no es ~1.000.
#    - Para cada pregunta semilla, el chunk con metadata.anomalia: "RAG-N"
#      correspondiente NO está dentro del top-3 (CA-6.1, spec 04).
#
#  Uso:
#      python scripts/prebakear.py
#      python scripts/prebakear.py --dry-run           # chunks + UMAP con
#                                                      # PCA local, sin
#                                                      # llamar a Azure
#                                                      # (valida la
#                                                      # estructura)
# ──────────────────────────────────────────────────────────────────────────
"""Pipeline de pre-bakeo de la clase 3."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv

SEMILLA = 42
EMBEDDING_DIM = 1536
CHUNK_SIZE_CARACTERES = 2400      # ~500 tokens en español
CHUNK_OVERLAP_CARACTERES = 240    # ~50 tokens
TOP_K_VALIDACION = 3              # CA-6.1: chunk plantado en top-3

CORPUS_PATH = Path("app/data/corpus.json")
SALIDA_DIR = Path("app/data")


# ──────────────────────────────────────────────────────────────────────────
#  Carga de variables de entorno.
# ──────────────────────────────────────────────────────────────────────────
def cargar_env() -> dict[str, str]:
    load_dotenv()
    return {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
        "deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                                "text-embedding-3-small"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION",
                                  "2024-10-21")
    }


# ──────────────────────────────────────────────────────────────────────────
#  Chunking — splitter recursivo por caracteres. Idéntico en comportamiento
#  al RecursiveCharacterTextSplitter de langchain, sin usar langchain.
#  Corta en [\n\n, \n, ". ", " ", ""] recursivamente hasta que cada chunk
#  cae en chunk_size. El overlap preserva contexto entre límites.
# ──────────────────────────────────────────────────────────────────────────
SEPARADORES = ["\n\n", "\n", ". ", " ", ""]


def _split_rec(texto: str, separadores: list[str],
               chunk_size: int, overlap: int) -> list[str]:
    """
    Split recursivo estilo langchain. Intenta separar por el primer
    separador; si los pedazos siguen siendo demasiado grandes, baja al
    siguiente separador.
    """
    if len(texto) <= chunk_size:
        return [texto] if texto.strip() else []

    sep = separadores[0]
    restantes = separadores[1:]
    partes = texto.split(sep) if sep else [texto]

    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len = 0

    def flushar() -> None:
        nonlocal buffer, buffer_len
        if buffer:
            chunk = (sep if sep else "").join(buffer)
            if chunk.strip():
                chunks.append(chunk)
            buffer = []
            buffer_len = 0

    for parte in partes:
        # Si la parte sola es más grande que el chunk_size, recibe
        # recursión con el siguiente separador.
        if len(parte) > chunk_size and restantes:
            flushar()
            sub = _split_rec(parte, restantes, chunk_size, overlap)
            # solapar:
            if chunks and overlap > 0:
                cola = chunks[-1][-overlap:]
                sub[0] = cola + (sep if sep else " ") + sub[0]
            chunks.extend(sub)
            continue

        if buffer_len + len(parte) + (len(sep) if buffer else 0) \
                > chunk_size:
            flushar()
            # Mantener overlap con el chunk anterior
            if chunks and overlap > 0:
                colita = chunks[-1][-overlap:] if chunks else ""
                if colita:
                    buffer = [colita, parte]
                    buffer_len = len(colita) + len(sep) + len(parte)
                else:
                    buffer = [parte]
                    buffer_len = len(parte)
            else:
                buffer = [parte]
                buffer_len = len(parte)
        else:
            buffer.append(parte)
            buffer_len += len(parte) + (len(sep) if len(buffer) > 1 else 0)

    flushar()
    return chunks


def partir_documento(texto: str,
                     chunk_size: int = CHUNK_SIZE_CARACTERES,
                     overlap: int = CHUNK_OVERLAP_CARACTERES
                     ) -> list[str]:
    """Partir un documento en chunks con solapamiento."""
    return _split_rec(texto, SEPARADORES + [""], chunk_size, overlap)


# ──────────────────────────────────────────────────────────────────────────
#  Indexación de chunks con metadata.
#  Cada chunk lleva: id secuencial, texto, dominio, doc_fuente,
#  parrafo_idx (índice del párrafo dentro del documento),
#  anomalias (lista de RAG-N si este chunk contiene un pasaje plantado).
# ──────────────────────────────────────────────────────────────────────────
def construir_chunks(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Recorre el corpus chunk por chunk y construye la lista de chunks con
    metadata. Devuelve lista plana.
    """
    chunks: list[dict[str, Any]] = []
    chunk_id = 0

    for fam in corpus["familias"]:
        for doc in fam["documentos"]:
            texto_completo = "\n\n".join(doc["parrafos"])
            trozos = partir_documento(texto_completo)

            # Cartografía de chunks → párrafo dominante: el párrafo cuyo
            # texto tiene el solapamiento más grande con el chunk.
            parrafos_texto = doc["parrafos"]

            # Mapa chunk_idx → lista de anomalías que toca este chunk.
            anomalias_por_parrafo = {an["parrafo_idx"]: an["id"]
                                     for an in doc.get("anomalias_plantadas",
                                                       [])}

            for trozo in trozos:
                if not trozo.strip():
                    continue
                # Determinar párrafo dominante: el de mayor solapamiento de
                # chars con el trozo.
                parrafo_idx = _parrafo_dominante(trozo, parrafos_texto)

                anomalias_aqui = []
                if parrafo_idx in anomalias_por_parrafo:
                    an_id = anomalias_por_parrafo[parrafo_idx]
                    # Confirmar que el trozo contiene un pedazo no trivial
                    # (>=40 chars) del párrafo anomalía.
                    solape = _solapamiento_chars(
                        trozo, parrafos_texto[parrafo_idx]
                    )
                    if solape >= 40:
                        anomalias_aqui.append(an_id)

                chunks.append({
                    "id": chunk_id,
                    "texto": trozo,
                    "dominio": doc["dominio"],
                    "dominio_label": doc["dominio_label"],
                    "doc_fuente": doc["id"],
                    "doc_titulo": doc["titulo"],
                    "parrafo_idx": parrafo_idx,
                    "anomalias": anomalias_aqui,
                    "tokens_aprox": len(trozo.split())
                })
                chunk_id += 1

    return chunks


def _parrafo_dominante(chunk: str, parrafos: list[str]) -> int:
    """Devuelve índice del párrafo con mayor solapamiento (chars)."""
    mejor = 0
    mejor_score = -1
    for i, p in enumerate(parrafos):
        score = _solapamiento_chars(chunk, p)
        if score > mejor_score:
            mejor_score = score
            mejor = i
    return mejor


def _solapamiento_chars(a: str, b: str) -> int:
    """Mide cuántos chars de 'b' aparecen en 'a'. Aproximado: substring
    match por tramos de 12 chars."""
    if not a or not b:
        return 0
    ventana = 12
    cuenta = 0
    for i in range(0, len(b) - ventana + 1, ventana):
        if b[i:i + ventana] in a:
            cuenta += ventana
    return cuenta


# ──────────────────────────────────────────────────────────────────────────
#  Embeddings con Azure OpenAI (text-embedding-3-small).
# ──────────────────────────────────────────────────────────────────────────
def _client_azure(env: dict[str, str]):
    """
    Construye un cliente de Azure OpenAI SDK v1.x.
    """
    if not env["endpoint"] or not env["api_key"]:
        raise SystemExit(
            "✗ Faltan credenciales Azure OpenAI en .env. "
            "Definí AZURE_OPENAI_ENDPOINT y AZURE_OPENAI_API_KEY."
        )

    try:
        from openai import AzureOpenAI
    except ImportError as e:
        raise SystemExit(
            "✗ Falta el paquete 'openai'. Instalá con:\n"
            "  pip install -r scripts/requirements.txt"
        ) from e

    return AzureOpenAI(
        azure_endpoint=env["endpoint"],
        api_key=env["api_key"],
        api_version=env["api_version"]
    )


def embedar(client, textos: list[str], deployment: str) -> list[list[float]]:
    """
    Embeda una lista de textos; hace batching (Azure admite hasta 16
    inputs por request con text-embedding-3-small).
    """
    BATCH = 16
    embeddings: list[list[float]] = []
    total = len(textos)

    for i in range(0, total, BATCH):
        lote = textos[i:i + BATCH]
        print(f"  embedando {i+1}-{i+len(lote)} de {total}…", end="",
              flush=True)
        t0 = time.time()
        resp = client.embeddings.create(model=deployment, input=lote)
        print(f" OK ({time.time()-t0:.1f}s)")
        # El orden del response respeta el orden del input
        for item in resp.data:
            embeddings.append(list(item.embedding))
        # Cortesía: no aglutinar al proveedor
        time.sleep(0.2)

    return embeddings


# ──────────────────────────────────────────────────────────────────────────
#  Dry-run: embeddings sintéticos deterministas para verificar estructura.
#  NO se commitean: solo en `--dry-run` para depurar el pipeline.
# ──────────────────────────────────────────────────────────────────────────
def embedar_dry_run(textos: list[str]) -> list[list[float]]:
    rng = np.random.default_rng(SEMILLA)
    return [
        # Vector aleatorio determinista, normalizado a norma 1
        (lambda v: (v / np.linalg.norm(v)).tolist())
        (rng.standard_normal(EMBEDDING_DIM))
        for _ in textos
    ]


# ──────────────────────────────────────────────────────────────────────────
#  Similitud coseno + ranking para preguntas semilla.
# ──────────────────────────────────────────────────────────────────────────
def coseno(q: np.ndarray, c: np.ndarray) -> float:
    denom = (np.linalg.norm(q) * np.linalg.norm(c))
    if denom == 0:
        return 0.0
    return float(np.dot(q, c) / denom)


def matriz_similitudes_chunks(emb: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(emb, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    norm_emb = emb / normas
    return norm_emb @ norm_emb.T


def ranking_para_query(query_emb: list[float],
                       chunks_emb: np.ndarray,
                       top_k: int = 5) -> list[dict[str, Any]]:
    q = np.array(query_emb, dtype=np.float32)
    scores = np.array([coseno(q, c) for c in chunks_emb])
    # top_k índices ordenados desc
    idx_sorted = np.argsort(-scores)[:top_k].tolist()
    return [
        {"chunk_id": int(i), "score": float(scores[i])} for i in idx_sorted
    ]


# ──────────────────────────────────────────────────────────────────────────
#  Proyección 3D: UMAP o PCA fallback.
# ──────────────────────────────────────────────────────────────────────────
def proyectar_3d(emb: np.ndarray) -> tuple[dict[int, list[float]], str]:
    """
    Proyecta a 3 dimensiones. Intenta UMAP (ADR-003); si no está
    instalado o falla, vía PCA. Devuelve (coords por chunk_id, método).
    """
    random.seed(SEMILLA)
    np.random.seed(SEMILLA)

    n = emb.shape[0]
    if n < 3:
        metodo = "pca"
        coords = _pca(emb)
        return {i: list(map(float, coords[i])) for i in range(n)}, metodo

    try:
        import umap
        # n_neighbors=8 porque corpus pequeño
        reducer = umap.UMAP(
            n_neighbors=min(8, n - 1),
            n_components=3,
            random_state=SEMILLA,
            transform_seed=SEMILLA,
            metric="cosine",
            init="spectral",
        )
        coords = reducer.fit_transform(emb)
        metodo = "umap"
    except Exception as e:
        print(f"  ⚠ UMAP no disponible ({e}). Usando PCA.")
        coords = _pca(emb)
        metodo = "pca"

    # Acotar coordenadas (UMAP puede salir raro)
    coords = np.array(coords)
    if np.abs(coords).max() > 30:
        # Escalar para mantener en rango [-30, 30] (CA del spec 03)
        m = np.abs(coords).max()
        coords = coords * (30 / m)

    return {i: list(map(float, coords[i])) for i in range(coords.shape[0])}, \
        metodo


def _pca(emb: np.ndarray) -> np.ndarray:
    from sklearn.decomposition import PCA
    n = emb.shape[0]
    n_comp = min(3, n)
    reducer = PCA(n_components=n_comp, random_state=SEMILLA)
    coords = reducer.fit_transform(emb)
    # Si PCA da menos de 3 componentes, rellenar con ceros
    if coords.shape[1] < 3:
        coords = np.hstack([
            coords,
            np.zeros((coords.shape[0], 3 - coords.shape[1]))
        ])
    return coords


# ──────────────────────────────────────────────────────────────────────────
#  Validación de thresholds — aborta si algo falla.
#  Ver spec 03 § "Thresholds de reproducibilidad (must)".
# ──────────────────────────────────────────────────────────────────────────
def validar_thresholds(chunks: list[dict[str, Any]],
                        embeddings: list[list[float]],
                        similitudes_chunk_chunk: np.ndarray,
                        rankings_query: dict[str, list[dict[str, Any]]],
                        corpus: dict[str, Any],
                        skip_ca_6_1: bool = False
                        ) -> list[str]:
    errores: list[str] = []

    # 1) Número de embeddings coincide con número de chunks.
    if len(embeddings) != len(chunks):
        errores.append(
            f"Número de embeddings ({len(embeddings)}) != número de chunks "
            f"({len(chunks)})"
        )

    # 2) Todas las dimensiones == 1536.
    for i, e in enumerate(embeddings):
        if len(e) != EMBEDDING_DIM:
            errores.append(f"Embedding {i} tiene {len(e)} dim "
                           f"(esperadas {EMBEDDING_DIM})")
            break

    # 3) Ningún embedding es nulo o NaN.
    arr = np.array(embeddings)
    if np.isnan(arr).any():
        errores.append("Algún embedding contiene NaN")
    if np.all(arr == 0, axis=1).any():
        errores.append("Algún embedding es cero")

    # 4) Coseno de un chunk consigo mismo ≈ 1.000.
    for i in range(len(chunks)):
        if abs(similitudes_chunk_chunk[i, i] - 1.0) > 1e-3:
            errores.append(
                f"Diagonal de similitud chunk {i} no es 1.0 "
                f"(vale {similitudes_chunk_chunk[i, i]})"
            )
            break

# 5) Para cada pregunta semilla, el chunk con anomalia:RAG-N
    #    correspondiente está dentro del top-3. CA-6.1.
    if skip_ca_6_1:
        print("  (skip CA-6.1: en --dry-run los embeddings son aleatorios)")
    else:
        mapa_anomalias = {an["id"]: an for an in corpus["anomalias_plantadas"]}
        for q in corpus["preguntas_semilla"]:
            an_id = q["id"]
            an_info = mapa_anomalias[an_id]
            # Encontrar chunk_id cuyo doc_fuente coincide con el doc anomalía
            # y que tenga el anomalia en metadata
            chunk_esperado = None
            for c in chunks:
                if an_id in c["anomalias"]:
                    chunk_esperado = c["id"]
                    break
            if chunk_esperado is None:
                errores.append(
                    f"Anomalía {an_id} no aparece en ningún chunk "
                    f"(¿chunking muy fino?)."
                )
                continue

            top = rankings_query[an_id][:TOP_K_VALIDACION]
            ids_top = [t["chunk_id"] for t in top]
            if chunk_esperado not in ids_top:
                errores.append(
                    f"CA-6.1 falla para {an_id}: chunk esperado {chunk_esperado} "
                    f"no está en top-{TOP_K_VALIDACION} ({ids_top}). "
                    f"Verificá el chunking o el modelo de embeddings."
                )
            else:
                pos = ids_top.index(chunk_esperado)
                score = top[pos]["score"]
                print(f"  ✓ {an_id}: chunk {chunk_esperado} en posición "
                      f"{pos+1} (score {score:.4f})")

    return errores


# ──────────────────────────────────────────────────────────────────────────
#  Orquestación.
# ──────────────────────────────────────────────────────────────────────────
def escribir_json(nombre: str, datos: Any) -> None:
    ruta = SALIDA_DIR / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    print(f"✓ Escrito {ruta}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pre-bakea el corpus de la clase 3 (embeddings + UMAP + "
                    "similitudes).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Lo que produce:\n"
            "  app/data/chunks.json\n"
            "  app/data/embeddings.json\n"
            "  app/data/similitudes.json\n"
            "  app/data/proyeccion_3d.json\n"
            "  app/data/_manifest.json\n"
            "\n"
            "Requiere credenciales Azure OpenAI. Si querés validar la "
            "estructura sin gastar, usa --dry-run (embeddings aleatorios "
            "deterministas, NO se usan en producción)."
        )
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="No llamar a Azure; embeddings aleatorios deterministas. "
             "Valida estructura del pipeline. NO se commitean los "
             "embeddings.json resultantes."
    )
    args = parser.parse_args()

    if not CORPUS_PATH.exists():
        print(f"✗ No existe {CORPUS_PATH}. Corré primero:")
        print("    python scripts/generar_corpus.py")
        return 1

    print(f"→ Cargando corpus: {CORPUS_PATH}")
    with CORPUS_PATH.open(encoding="utf-8") as f:
        corpus = json.load(f)
    print(f"  ✓ {corpus['_stats']['documentos']} documentos · "
          f"{corpus['_stats']['paragrafos']} párrafos · "
          f"{corpus['_stats']['palabras_aprox']} palabras")

    # ── 1) Chunks ─────────────────────────────────────────────────────────
    print(f"\n→ Chunking (target ~{CHUNK_SIZE_CARACTERES} chars, "
          f"overlap {CHUNK_OVERLAP_CARACTERES})")
    chunks = construir_chunks(corpus)
    n_chunks = len(chunks)
    print(f"  ✓ {n_chunks} chunks")

    # Reporte: anomalías encontradas
    anomalias_en_chunks: dict[str, int] = {}
    for c in chunks:
        for an in c["anomalias"]:
            anomalias_en_chunks[an] = c["id"]
    for an_id, chunk in anomalias_en_chunks.items():
        print(f"    └ {an_id}: chunk {chunk} ({chunks[chunk]['doc_fuente']})")

    faltantes = {"RAG-1", "RAG-2", "RAG-3"} - set(anomalias_en_chunks)
    if faltantes:
        print(f"\n✗ CHUNKING FALLÓ: anomalías {faltantes} no aparecen en "
              f"ningún chunk. El documento anomalía está demasiado corto "
              f"o el chunk_size es demasiado grande.")
        # No abortamos todavía: dejamos que la validación final trate de
        # pasar y muestre el error formal.

    # ── 2) Embeddings ─────────────────────────────────────────────────────
    print(f"\n→ Embeddings ({EMBEDDING_DIM} dim)")
    if args.dry_run:
        print("  (modo --dry-run: embeddings aleatorios deterministas)")
        embeddings = embedar_dry_run([c["texto"] for c in chunks])
    else:
        env = cargar_env()
        if not env["endpoint"] or not env["api_key"]:
            print("✗ Faltan credenciales Azure OpenAI.")
            print("  Definí en .env las variables AZURE_OPENAI_ENDPOINT y "
                  "AZURE_OPENAI_API_KEY.")
            print("  Si solo querés validar estructura, usá --dry-run.")
            return 1
        if not env["deployment"]:
            print("✗ Falta AZURE_OPENAI_EMBEDDING_DEPLOYMENT en .env")
            return 1
        client = _client_azure(env)
        embeddings = embedar(client, [c["texto"] for c in chunks],
                              env["deployment"])

    arr_emb = np.array(embeddings, dtype=np.float32)

    # ── 3) Similitud chunk×chunk ──────────────────────────────────────────
    print(f"\n→ Matriz de similitud chunk×chunk (coseno)")
    sim_chunk = matriz_similitudes_chunks(arr_emb)
    # Convertir a sparse structure para no meter 200x200 floats en el json
    # Vamos a guardar la diagonal y los top-K vecinos de cada chunk
    TOP_VECINOS = 10
    vecinos: dict[int, list[dict[str, float]]] = {}
    for i in range(n_chunks):
        scores = sim_chunk[i]
        idx_sorted = np.argsort(-scores)[:TOP_VECINOS + 1]
        idx_sorted = [int(j) for j in idx_sorted if j != i][:TOP_VECINOS]
        vecinos[i] = [
            {"chunk_id": int(j), "score": float(sim_chunk[i, j])}
            for j in idx_sorted
        ]

    # ── 4) Similitud query×chunk para preguntas semilla ───────────────────
    print(f"\n→ Embeddings de las 3 preguntas semilla")
    preguntas_emb: list[list[float]] = []
    if args.dry_run:
        preguntas_emb = embedar_dry_run([p["texto"]
                                          for p in corpus["preguntas_semilla"]])
    else:
        env = cargar_env()
        client = _client_azure(env) if 'client' not in dir() else client
        preguntas_emb = embedar(
            client,
            [p["texto"] for p in corpus["preguntas_semilla"]],
            env["deployment"]
        )

    print(f"\n→ Ranking top-K para cada pregunta semilla")
    rankings_query: dict[str, list[dict[str, Any]]] = {}
    for i, p in enumerate(corpus["preguntas_semilla"]):
        ranking = ranking_para_query(preguntas_emb[i], arr_emb, top_k=10)
        rankings_query[p["id"]] = ranking
        top5 = ranking[:5]
        print(f"  · {p['id']}: top-5 = "
              f"{[(t['chunk_id'], round(t['score'], 3)) for t in top5]}")

    # ── 5) Proyección 3D (UMAP o PCA) ─────────────────────────────────────
    print(f"\n→ Proyección 3D (UMAP o PCA fallback)")
    proyeccion, metodo = proyectar_3d(arr_emb)
    print(f"  ✓ Método: {metodo}")

    # ── 6) Validación ────────────────────────────────────────────────────
    print(f"\n→ Validación de thresholds")
    errores = validar_thresholds(
        chunks, embeddings, sim_chunk, rankings_query, corpus,
        skip_ca_6_1=args.dry_run
    )

    if errores:
        print(f"\n✗ Validación FALLÓ ({len(errores)} errores):")
        for e in errores:
            print(f"    └ {e}")
        return 1

    print("\n✓ Validación OK")

    if args.dry_run:
        print(
            "\n⚠ modo --dry-run: embeddings ALEATORIOS (no usables para clase)."
            "\n  Útil para probar la estructura del frontend en desarrollo."
            "\n  Para clase real, corré sin --dry-run con credenciales Azure."
        )
        print("\n  Escribiendo archivos de todos modos (manifest los marca "
              "como `dry_run: true`).")
    else:
        print("\n✓ Validación OK")

    # ── 7) Escritura ─────────────────────────────────────────────────────
    print(f"\n→ Escritura de outputs en {SALIDA_DIR}")

    escribir_json("chunks.json", chunks)
    escribir_json("embeddings.json", embeddings)

    similitudes_out = {
        "chunk_x_chunk_top": vecinos,
        "query_x_chunk_top": rankings_query,
        "preguntas_emb": None  # se setea abajo
    }
    # Guardar las preguntas_emb como datos aparte para que la app pueda
    # mostrarlas en la pantalla 6 (validación visual del vector de query):
    similitudes_out["preguntas_emb"] = preguntas_emb
    escribir_json("similitudes.json", similitudes_out)

    escribir_json("proyeccion_3d.json", {
        "metodo": metodo,
        "semilla": SEMILLA,
        "coords": proyeccion
    })

    manifest = {
        "fecha_generacion": date.today().isoformat(),
        "modelo_embeddings": "text-embedding-3-small" if not args.dry_run
                             else "dry-run-random",
        "modelo_emb_dim": EMBEDDING_DIM,
        "semilla": SEMILLA,
        "n_chunks": n_chunks,
        "n_docs": corpus["_stats"]["documentos"],
        "n_familias": corpus["_stats"]["familias"],
        "n_preguntas_semilla": len(corpus["preguntas_semilla"]),
        "anomalias_plantadas": [
            {"id": an_id, "chunk_id": chunk}
            for an_id, chunk in anomalias_en_chunks.items()
        ],
        "metodo_proyeccion": metodo,
        "dry_run": bool(args.dry_run),
        "generado_en": datetime.now().isoformat(timespec="seconds"),
        "version": "3.0.0"
    }
    escribir_json("_manifest.json", manifest)

    print(f"\n✓ Pre-bakeo completo. Validá con:")
    print(f"    cat app/data/_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())