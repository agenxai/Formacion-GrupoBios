#!/usr/bin/env python3
"""Verifica los diez invariantes del contrato de eventos. Spec 04.

Un contrato declarado verificable y no verificado es solo prosa — y en la Sesión 6
estas specs se presentan como ejemplo de especificación válida.

Uso:
    python scripts/verificar_contrato.py backend/replay/trazas.json
    python scripts/verificar_contrato.py .cache_llm/*.json
    curl -s localhost:8000/api/traza/<run_id> | python scripts/verificar_contrato.py -

Reporta el `seq` exacto donde falla.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

TIPOS_VALIDOS = {
    "inicio", "llm_request", "llm_response", "pensamiento", "ruta", "tool_call",
    "tool_result", "delegacion", "sub_evento", "respuesta_final", "metricas",
    "aviso", "error", "fin",
}


class Fallo(Exception):
    pass


def _fallos_de_un_run(eventos: list[dict], etiqueta: str) -> list[str]:
    """Invariantes 1 a 7 sobre una secuencia de eventos de un solo run."""
    fallos: list[str] = []
    if not eventos:
        return [f"{etiqueta}: run vacío"]

    tipos = [e.get("tipo") for e in eventos]

    # 1 · Empieza con `inicio` y termina con `fin`, sin excepción.
    if tipos[0] != "inicio":
        fallos.append(f"{etiqueta}: [inv.1] empieza con '{tipos[0]}', no con 'inicio'")
    if tipos[-1] != "fin":
        fallos.append(f"{etiqueta}: [inv.1] termina con '{tipos[-1]}', no con 'fin'")

    # 2 · `seq` estrictamente creciente y sin huecos.
    for i, evento in enumerate(eventos):
        seq = evento.get("seq")
        if seq != i:
            fallos.append(
                f"{etiqueta}: [inv.2] el evento en posición {i} tiene seq={seq}; "
                f"se esperaba {i} (creciente y sin huecos)"
            )
            break

    # 3 · Todo `tool_call` tiene exactamente un `tool_result` con el mismo id, o
    #     un `error` que lo referencie.
    llamadas = [e for e in eventos if e.get("tipo") == "tool_call"]
    resultados = [e for e in eventos if e.get("tipo") == "tool_result"]
    ids_resultado: dict[str, int] = {}
    for e in resultados:
        ids_resultado[str(e.get("id_llamada"))] = ids_resultado.get(str(e.get("id_llamada")), 0) + 1
    hubo_error = any(e.get("tipo") == "error" for e in eventos)
    for e in llamadas:
        idl = str(e.get("id_llamada"))
        cuantos = ids_resultado.get(idl, 0)
        if cuantos == 0 and not hubo_error:
            fallos.append(
                f"{etiqueta}: [inv.3] tool_call seq={e.get('seq')} id={idl} "
                "no tiene tool_result ni error que lo referencie"
            )
        elif cuantos > 1:
            fallos.append(
                f"{etiqueta}: [inv.3] tool_call id={idl} tiene {cuantos} tool_result"
            )

    # 4 · `metricas` justo antes de `fin`, siempre — también en error.
    if len(tipos) >= 2 and tipos[-1] == "fin" and tipos[-2] != "metricas":
        fallos.append(
            f"{etiqueta}: [inv.4] antes de 'fin' hay '{tipos[-2]}', no 'metricas'"
        )
    if "metricas" not in tipos:
        fallos.append(f"{etiqueta}: [inv.4] el run no emitió 'metricas'")

    # 5 · `respuesta_final` a lo sumo una vez.
    n_final = tipos.count("respuesta_final")
    if n_final > 1:
        fallos.append(f"{etiqueta}: [inv.5] hay {n_final} eventos 'respuesta_final'")

    # 6 · `ts_ms` monótono no decreciente.
    anterior = -1
    for e in eventos:
        ts = e.get("ts_ms", 0)
        if not isinstance(ts, int) or ts < anterior:
            fallos.append(
                f"{etiqueta}: [inv.6] ts_ms retrocede en seq={e.get('seq')} "
                f"({anterior} → {ts})"
            )
            break
        anterior = ts

    # 7 · Ningún evento contiene la API key ni fragmentos de ella.
    try:
        from backend.config import config

        key = config.openai_api_key.strip()
        if config.key_presente and len(key) >= 12:
            plano = json.dumps(eventos, ensure_ascii=False)
            if key in plano or key[:20] in plano:
                fallos.append(f"{etiqueta}: [inv.7] la traza contiene la API key")
    except Exception:  # noqa: BLE001 — sin configuración, este invariante no aplica
        pass

    # Tipos declarados
    for e in eventos:
        if e.get("tipo") not in TIPOS_VALIDOS:
            fallos.append(
                f"{etiqueta}: tipo de evento desconocido '{e.get('tipo')}' "
                f"en seq={e.get('seq')}"
            )

    return fallos


def verificar_traza(eventos: list[dict], etiqueta: str) -> list[str]:
    """Aplica los diez invariantes a un run y a todos sus sub-runs."""
    fallos: list[str] = []

    # Invariantes 1-7 en el run padre, contando los `sub_evento` como un evento
    # propio del padre (que es lo que son: consumen un `seq` del padre).
    fallos += _fallos_de_un_run(eventos, etiqueta)

    # 8 y 9 · Cada sub-run se verifica por separado, con su propio `seq` desde 0.
    sub_runs: dict[str, list[dict]] = {}
    for e in eventos:
        if e.get("tipo") != "sub_evento":
            continue
        agente = str(e.get("agente"))
        anidado = e.get("evento") or {}

        # 10 · La anidación es de un solo nivel.
        if anidado.get("tipo") == "sub_evento":
            fallos.append(
                f"{etiqueta}: [inv.10] sub_evento anidado dentro de otro "
                f"(seq={e.get('seq')}); un sub-agente no delega"
            )
        sub_runs.setdefault(agente, []).append(anidado)

    for agente, sub in sub_runs.items():
        fallos += _fallos_de_un_run(sub, f"{etiqueta} › {agente}")

    # 9 · Las métricas del padre son la suma de las suyas más las de sus sub-runs.
    padre = next((e for e in reversed(eventos) if e.get("tipo") == "metricas"), None)
    if padre and sub_runs:
        propias_llm = sum(
            1
            for e in eventos
            if e.get("tipo") == "llm_request"
        )
        sub_llm = sum(
            1
            for sub in sub_runs.values()
            for e in sub
            if e.get("tipo") == "llm_request"
        )
        esperado = propias_llm + sub_llm
        if padre.get("llamadas_llm") != esperado:
            fallos.append(
                f"{etiqueta}: [inv.9] metricas.llamadas_llm={padre.get('llamadas_llm')} "
                f"pero el run tiene {propias_llm} propias + {sub_llm} de sub-runs "
                f"= {esperado}"
            )
    return fallos


def _extraer_runs(datos: Any) -> dict[str, list[dict]]:
    """Acepta los tres formatos en que aparece una traza en este repositorio."""
    runs: dict[str, list[dict]] = {}

    if isinstance(datos, dict) and "eventos" in datos:
        # Entrada de caché o respuesta de /api/traza/{run_id}
        eventos = datos["eventos"]
        por_run: dict[str, list[dict]] = {}
        for e in eventos:
            por_run.setdefault(str(e.get("run_id", "?")), []).append(e)
        return por_run

    if isinstance(datos, dict):
        # backend/replay/trazas.json → {"n1|pregunta": [eventos]}
        for clave, eventos in datos.items():
            if isinstance(eventos, list):
                runs[clave] = eventos
        return runs

    if isinstance(datos, list):
        return {"(traza)": datos}

    return runs


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2

    total_runs = 0
    todos_los_fallos: list[str] = []

    for ruta in argv:
        if ruta == "-":
            datos = json.load(sys.stdin)
            origen = "(stdin)"
        else:
            p = Path(ruta)
            if not p.exists():
                todos_los_fallos.append(f"{ruta}: no existe")
                continue
            try:
                datos = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                todos_los_fallos.append(f"{ruta}: JSON inválido — {exc}")
                continue
            origen = p.name

        runs = _extraer_runs(datos)
        if not runs:
            todos_los_fallos.append(f"{origen}: no encontré trazas dentro")
            continue

        for clave, eventos in runs.items():
            total_runs += 1
            fallos = verificar_traza(eventos, f"{origen}[{clave}]")
            if fallos:
                todos_los_fallos += fallos
            else:
                print(f"✓ {origen}[{clave}] · {len(eventos)} eventos · 10 invariantes")

    print()
    if todos_los_fallos:
        print(f"✕ {len(todos_los_fallos)} incumplimiento(s) en {total_runs} run(s):\n")
        for f in todos_los_fallos:
            print(f"  · {f}")
        return 1

    print(f"→ {total_runs} run(s) cumplen los diez invariantes del contrato.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
