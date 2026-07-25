"""Graba las trazas del modo replay ejecutando de verdad. Spec 09, Riesgo 2.

    python -m backend.replay.grabar                 # las 5 preguntas × 5 niveles
    python -m backend.replay.grabar --niveles n4 n5
    python -m backend.replay.grabar --extras        # incluye las dos de apoyo

REQUIERE API KEY y `MODO=vivo`. No hay forma honesta de generar estas trazas sin
ejecutar: una traza fabricada presentada como grabación real sería exactamente lo
que este laboratorio enseña a no hacer.

Regrábalas si cambian los prompts, el modelo o la semilla de datos. Después,
valida con:

    python scripts/verificar_contrato.py backend/replay/trazas.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from backend.config import config
from backend.eventos import serializar
from backend.llm import clave_traza, estado_lab
from backend.niveles import NIVELES, ORDEN
from backend.preguntas import PREGUNTA_AMBIGUA, PREGUNTA_SIN_DATOS, PREGUNTAS


async def grabar_una(nivel_id: str, pregunta: str) -> list[dict]:
    nivel = NIVELES[nivel_id]
    eventos: list[dict] = []
    async for evento in nivel.ejecutar(pregunta, f"grabacion:{uuid.uuid4().hex[:8]}"):
        eventos.append(serializar(evento))
    return eventos


async def principal(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--niveles", nargs="*", default=list(ORDEN))
    ap.add_argument("--extras", action="store_true")
    args = ap.parse_args(argv)

    if not config.key_presente:
        print(
            "✕ No hay OPENAI_API_KEY. Las trazas de replay se graban ejecutando "
            "de verdad;\n  no se pueden fabricar sin mentir sobre lo que son.\n"
            "  Pega la key en .env y vuelve a intentar.",
            file=sys.stderr,
        )
        return 2
    if not estado_lab.vivo:
        print(
            f"✕ El laboratorio está en modo '{estado_lab.modo}'. Para grabar hace "
            "falta MODO=vivo.",
            file=sys.stderr,
        )
        return 2

    # El caché se ignora al grabar: se quiere la ejecución real, con sus tiempos.
    original_cache = config.cache_activo
    config.cache_activo = False

    textos = [p["texto"] for p in PREGUNTAS]
    if args.extras:
        textos += [PREGUNTA_SIN_DATOS, PREGUNTA_AMBIGUA]

    ruta = config.ruta_trazas
    trazas: dict[str, list[dict]] = {}
    if ruta.exists():
        try:
            trazas = json.loads(ruta.read_text(encoding="utf-8"))
            print(f"Actualizando {ruta.name} ({len(trazas)} trazas existentes)")
        except json.JSONDecodeError:
            print(f"{ruta.name} estaba corrupto; se regenera completo")

    total = len(textos) * len(args.niveles)
    hecho = 0
    for pregunta in textos:
        for nivel_id in args.niveles:
            if nivel_id not in NIVELES:
                print(f"  ✕ nivel desconocido: {nivel_id}")
                continue
            hecho += 1
            etiqueta = f"[{hecho}/{total}] {nivel_id} · {pregunta[:52]}…"
            try:
                eventos = await grabar_una(nivel_id, pregunta)
                estado = eventos[-1].get("estado") if eventos else "?"
                if estado != "ok":
                    print(f"  ⚠ {etiqueta} → terminó en '{estado}', NO se guarda")
                    continue
                trazas[clave_traza(nivel_id, pregunta)] = eventos
                metricas = next(
                    (e for e in reversed(eventos) if e["tipo"] == "metricas"), {}
                )
                print(
                    f"  ✓ {etiqueta} → {len(eventos)} eventos · "
                    f"{metricas.get('llamadas_llm', '?')} llm · "
                    f"{metricas.get('ms_total', '?')} ms"
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  ✕ {etiqueta} → {type(exc).__name__}: {exc}")

    config.cache_activo = original_cache

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(trazas, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\n→ {len(trazas)} trazas en {ruta}")
    print(f"  gasto de esta grabación: ${estado_lab.gasto_usd:.4f}")
    print("  valida el contrato con:")
    print("    python scripts/verificar_contrato.py backend/replay/trazas.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
