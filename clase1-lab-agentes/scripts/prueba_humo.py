#!/usr/bin/env python3
"""Prueba de humo del laboratorio completo, SIN gastar cuota de API.

    python scripts/prueba_humo.py

Sustituye el modelo por uno guionado y ejercita los cinco niveles de punta a punta:
tipos y orden de eventos, los diez invariantes del contrato, las métricas, la
anidación de N5 y que el notebook sea resoluble.

Para qué sirve, concretamente: después de editar un system prompt, cambiar una tool o
subir la versión de LangGraph, esto dice en veinte segundos si el laboratorio sigue en
pie. Sin él, la única forma de saberlo sería gastar llamadas reales — con una key
compartida y un tope de gasto, eso no es gratis.

Qué NO prueba: la calidad de las respuestas del modelo real. Eso necesita key y es lo
que hace `python -m backend.replay.grabar` cuando se graban las trazas.

N4 y N5 corren sobre el `create_react_agent` REAL de LangGraph —con su ToolNode y su
bucle— y solo el modelo es falso. Es lo que valida la suposición más frágil del
backend: que `stream_react` lee bien el stream del grafo.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
if str(RAIZ / "scripts") not in sys.path:
    sys.path.insert(0, str(RAIZ / "scripts"))

import warnings  # noqa: E402

# Mismo motivo que en backend/niveles/react.py: `create_react_agent` está deprecada
# en LangGraph 1.x. Se silencia el ruido, no el hecho — está documentado en el README.
warnings.filterwarnings("ignore", message=".*create_react_agent.*")

from langchain_core.callbacks import CallbackManagerForLLMRun  # noqa: E402
from langchain_core.language_models import BaseChatModel  # noqa: E402
from langchain_core.messages import AIMessage, BaseMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from backend.eventos import Traza, resumir, serializar  # noqa: E402
from backend.preguntas import PREGUNTA_INSIGNIA, PREGUNTAS  # noqa: E402
from backend.tools.operaciones import POR_NOMBRE  # noqa: E402
from verificar_contrato import verificar_traza  # noqa: E402

PREGUNTA_CRUZADA = PREGUNTAS[-1]["texto"]
USO = {"input_tokens": 150, "output_tokens": 45, "total_tokens": 195}

_ids = {"n": 0}


def _nuevo_id() -> str:
    _ids["n"] += 1
    return f"call_{_ids['n']:04d}"


# ---------------------------------------------------------------------------
#  Dobles del modelo
# ---------------------------------------------------------------------------


def _mensaje_ai(texto: str = "", tools: list[tuple[str, dict]] | None = None) -> AIMessage:
    tool_calls, crudas = [], []
    for nombre, args in tools or []:
        idl = _nuevo_id()
        tool_calls.append({"name": nombre, "args": args, "id": idl, "type": "tool_call"})
        crudas.append(
            {
                "id": idl,
                "type": "function",
                "function": {"name": nombre, "arguments": json.dumps(args, ensure_ascii=False)},
            }
        )
    return AIMessage(
        content=texto,
        tool_calls=tool_calls,
        usage_metadata=dict(USO),
        additional_kwargs={"tool_calls": crudas} if crudas else {},
    )


class ModeloGuionado(BaseChatModel):
    """Modelo de chat real con respuestas guionadas. LangGraph lo trata como uno más."""

    guion: list = []
    estado: dict = {}

    @property
    def _llm_type(self) -> str:
        return "guionado"

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, esquema, include_raw: bool = False, **kwargs):
        return _EstructuradoGuionado(modelo=self, esquema=esquema)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        i = self.estado.get("i", 0)
        self.estado["i"] = i + 1
        paso = self.guion[min(i, len(self.guion) - 1)]
        mensaje = _mensaje_ai(paso.get("texto", ""), paso.get("tools"))
        return ChatResult(generations=[ChatGeneration(message=mensaje)])


class _EstructuradoGuionado:
    def __init__(self, modelo: ModeloGuionado, esquema: Any) -> None:
        self.modelo, self.esquema = modelo, esquema

    async def ainvoke(self, mensajes, **kwargs):
        campos = self.modelo.guion[0].get("estructurado", {})
        return {
            "raw": _mensaje_ai(""),
            "parsed": self.esquema(**campos),
            "parsing_error": None,
        }


class _CompletionsGuionadas:
    """Imita `openai.AsyncOpenAI().chat.completions` para N3."""

    def __init__(self, guion: list[dict]) -> None:
        self.guion, self.i = guion, 0

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    async def create(self, **kwargs):
        paso = self.guion[min(self.i, len(self.guion) - 1)]
        self.i += 1
        return _RespuestaCruda(paso.get("texto"), paso.get("tools"))


class _RespuestaCruda:
    def __init__(self, texto: str | None, tools: list[tuple[str, dict]] | None) -> None:
        self.texto, self.tools = texto, tools or []

    def model_dump(self) -> dict:
        tcs = [
            {
                "id": _nuevo_id(),
                "type": "function",
                "function": {"name": n, "arguments": json.dumps(a, ensure_ascii=False)},
            }
            for n, a in self.tools
        ]
        return {
            "choices": [{"message": {"content": self.texto, "tool_calls": tcs or None}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 45},
        }


# ---------------------------------------------------------------------------
#  Guiones por nivel
# ---------------------------------------------------------------------------

ARG_INV = {"planta": "Itagüí", "materia_prima": "maíz"}
ARG_DEM = {"planta": "Itagüí", "dias": 7, "materia_prima": "maíz"}

G_N1 = [{"texto": "La planta de Itagüí tiene aproximadamente 450 toneladas de maíz."}]
G_N2 = [{"estructurado": {"dominio": "compras",
                          "motivo": "Habla de inventario de materia prima."}}]
G_N3 = [
    {"tools": [("consultar_inventario", ARG_INV)]},
    {"texto": "La planta de Itagüí tiene 320.0 toneladas de maíz al último corte."},
]
G_N4 = [
    {"texto": "Primero mido el inventario.", "tools": [("consultar_inventario", ARG_INV)]},
    {"texto": "Ahora la demanda en la misma unidad.", "tools": [("consultar_demanda", ARG_DEM)]},
    {"texto": "No alcanza: hay 320.0 t y la semana requiere 1651.9 t; faltan ~1332 t."},
]
G_SUPERVISOR = [
    {"texto": "Consulto a los dos especialistas.",
     "tools": [("agente_abastecimiento", {"instruccion": "¿Déficit de maíz en Itagüí?"}),
               ("agente_operaciones", {"instruccion": "¿Falla de equipos en el pedido?"})]},
    {"texto": "El retraso es por materia prima: Itagüí está muy por debajo del mínimo "
              "de maíz; los equipos operan normal."},
]
G_SUB_ABAS = [
    {"texto": "Reviso inventario.", "tools": [("consultar_inventario", ARG_INV)]},
    {"texto": "Itagüí tiene 320.0 t de maíz contra un mínimo de 1190 t."},
]
G_SUB_OPER = [
    {"texto": "Reviso el pedido.", "tools": [("estado_pedido", {"numero": "PD-24-00871"})]},
    {"texto": "En muelle, posición 6 de la cola. Equipos sin novedad."},
]


def _guion_por_tools(tools) -> list[dict]:
    nombres = {getattr(t, "name", getattr(t, "__name__", "")) for t in tools}
    if "agente_abastecimiento" in nombres:
        return G_SUPERVISOR
    if "consultar_inventario" in nombres and "historial_fallas" not in nombres:
        return G_SUB_ABAS
    if "historial_fallas" in nombres and "consultar_inventario" not in nombres:
        return G_SUB_OPER
    return G_N4


# ---------------------------------------------------------------------------
#  La vista El caso (spec 11)
# ---------------------------------------------------------------------------


def verificar_caso() -> list[str]:
    """La vista El caso, sin servidor y sin modelo.

    Lo frágil de esta vista no es el código sino la DESINCRONIZACIÓN: que alguien
    renombre una tabla y el mapa quede hablando de algo que no existe, o que una
    tool quede sin ejemplo curado y su tarjeta salga sin «Probar». Todo eso se
    descubre acá, no proyectando.
    """
    from backend import caso
    from backend.db import conteo_por_tabla
    from backend.db.descripciones import TABLAS
    from backend.tools import ejemplos
    from backend.tools.operaciones import TODAS

    problemas: list[str] = []

    agregado = caso.agregado()
    tablas_vista = {t["id"] for t in agregado["tablas"]}
    tablas_base = set(conteo_por_tabla())

    # 1 · El mapa y la base hablan de las mismas tablas, en las dos direcciones.
    if tablas_vista != tablas_base:
        problemas.append(
            f"El mapa muestra {sorted(tablas_vista)} y la base tiene {sorted(tablas_base)}"
        )
    sin_describir = tablas_base - set(TABLAS)
    if sin_describir:
        problemas.append(f"Tablas sin qué_aporta en descripciones.py: {sorted(sin_describir)}")
    fantasmas = set(TABLAS) - tablas_base
    if fantasmas:
        problemas.append(f"descripciones.py describe tablas que no existen: {sorted(fantasmas)}")

    # 2 · Cada referencia del mapa apunta a una tabla real.
    for t in agregado["tablas"]:
        for ref in t["referencias"]:
            if ref["hacia"] not in tablas_base:
                problemas.append(f"{t['id']} referencia una tabla inexistente: {ref['hacia']}")

    # 3 · Las 7 tools tienen tarjeta con docstring y al menos un ejemplo.
    herramientas = {h["nombre"]: h for h in agregado["herramientas"]}
    for f in TODAS:
        h = herramientas.get(f.__name__)
        if h is None:
            problemas.append(f"La tool {f.__name__} no tiene tarjeta en El caso")
            continue
        if not h["docstring"].strip():
            problemas.append(f"La tool {f.__name__} tiene la docstring vacía")
        if not h["ejemplos"]:
            problemas.append(f"La tool {f.__name__} no tiene ningún ejemplo curado")

    # 4 · Todos los «Probar» ejecutan y devuelven estructura, sin excepción.
    for nombre in herramientas:
        for i in range(len(ejemplos.ejemplos_de(nombre))):
            try:
                r = ejemplos.ejecutar(nombre, i)
                if not isinstance(r["resultado"], dict):
                    problemas.append(f"Probar {nombre}[{i}] no devolvió un dict")
            except Exception as exc:  # noqa: BLE001
                problemas.append(f"Probar {nombre}[{i}] lanzó: {type(exc).__name__}: {exc}")

    # 5 · El ejemplo de la pregunta insignia trae la cifra con contrato (spec 03).
    r = ejemplos.ejecutar("consultar_inventario", 0)
    item = (r["resultado"].get("items") or [{}])[0]
    if item.get("cantidad_ton") != 320.0:
        problemas.append(
            f"El ejemplo de inventario da {item.get('cantidad_ton')} t de maíz; "
            "el contrato de datos dice 320.0"
        )

    # 6 · Las preguntas no revelan lo que la clase debe descubrir (spec 11).
    for p in agregado["preguntas"]:
        if "nivel_que_la_resuelve" in p:
            problemas.append(f"La pregunta {p['chip']!r} filtra nivel_que_la_resuelve")
        if not p.get("cruza"):
            problemas.append(f"La pregunta {p['chip']!r} no dice qué hay que cruzar")
        for t in p.get("tablas", []):
            if t not in tablas_base:
                problemas.append(f"La pregunta {p['chip']!r} cruza una tabla inexistente: {t}")

    n_probar = sum(len(ejemplos.ejemplos_de(n)) for n in herramientas)
    if problemas:
        print(f"  ✕ El caso: {len(problemas)} problema(s) (ver abajo)")
    else:
        print(
            f"  ✓ El caso: {len(tablas_vista)} tablas · {len(herramientas)} tools · "
            f"{n_probar} «Probar» · 5 preguntas sin respuestas"
        )
    return problemas


# ---------------------------------------------------------------------------
#  Ejecución
# ---------------------------------------------------------------------------


async def _correr(nivel, pregunta: str) -> tuple[list, Traza, list[str]]:
    eventos = [e async for e in nivel.ejecutar(pregunta, f"humo:{nivel.ID}")]
    traza = resumir(eventos)
    fallos = verificar_traza([serializar(e) for e in eventos], nivel.ID.upper())
    return eventos, traza, fallos


def _linea(nivel: str, traza: Traza, fallos: list[str]) -> None:
    marca = "✓" if not fallos else "✕"
    print(
        f"{marca} {nivel.upper()}: {traza.llamadas_llm} llm · "
        f"{traza.llamadas_tools} tools · {traza.tokens_in}+{traza.tokens_out} tok · "
        f"estado={traza.estado}"
    )
    if traza.respuesta_final:
        print(f"    «{traza.respuesta_final[:96]}»")
    for f in fallos:
        print(f"    ✕ {f}")


async def principal() -> int:
    from backend.niveles import (
        n1_procesador,
        n2_router,
        n3_tool_caller,
        n4_react,
        n5_supervisor,
    )
    from backend.niveles import react as R
    from langgraph.prebuilt import create_react_agent

    problemas: list[str] = []

    def modelo(guion: list[dict]) -> ModeloGuionado:
        return ModeloGuionado(guion=guion, estado={})

    print("── Los cinco niveles ──────────────────────────────────────────")

    # N1
    n1_procesador.cliente = lambda *a, **k: modelo(G_N1)
    _, t1, f1 = await _correr(n1_procesador.nivel, PREGUNTA_INSIGNIA)
    _linea("n1", t1, f1)
    problemas += f1
    if t1.llamadas_llm != 1 or t1.llamadas_tools != 0:
        problemas.append("N1 debe hacer 1 llamada y 0 tools")
    if not t1.avisos:
        problemas.append("N1 no emitió el aviso de cifra sin fuente")
    else:
        print(f"    ⚠ {t1.avisos[0]}")

    # N2
    n2_router.cliente = lambda *a, **k: modelo(G_N2)
    _, t2, f2 = await _correr(n2_router.nivel, PREGUNTA_INSIGNIA)
    _linea("n2", t2, f2)
    problemas += f2
    if t2.ruta != "compras":
        problemas.append(f"N2 enrutó a {t2.ruta!r}, se esperaba 'compras'")

    # N3
    n3_tool_caller.cliente_crudo = lambda: _CompletionsGuionadas(G_N3)
    _, t3, f3 = await _correr(n3_tool_caller.nivel, PREGUNTA_INSIGNIA)
    _linea("n3", t3, f3)
    problemas += f3
    if t3.llamadas_llm != 2 or t3.llamadas_tools != 1:
        problemas.append("N3 debe hacer 2 llamadas y 1 sola ronda de tools")
    if not t3.tool_calls or not t3.tool_calls[0].crudo:
        problemas.append("N3 no expuso el JSON crudo de la tool call (ADR-002)")
    else:
        json.loads(t3.tool_calls[0].crudo)
        print(f"    JSON crudo: {t3.tool_calls[0].crudo.splitlines()[1].strip()}")
    if "320" not in t3.respuesta_final:
        problemas.append("N3 no trajo el valor real de la base")

    # N4 y N5 sobre el grafo REAL de LangGraph
    R.construir_agente = lambda tools, prompt, modelo_id=None: create_react_agent(
        modelo(_guion_por_tools(tools)), tools, prompt=prompt
    )

    _, t4, f4 = await _correr(n4_react.nivel, PREGUNTA_INSIGNIA)
    _linea("n4", t4, f4)
    problemas += f4
    if not {"consultar_inventario", "consultar_demanda"} <= set(t4.tools_usadas):
        problemas.append(f"N4 debe encadenar inventario y demanda; usó {t4.tools_usadas}")

    eventos5, t5, f5 = await _correr(n5_supervisor.nivel, PREGUNTA_CRUZADA)
    _linea("n5", t5, f5)
    problemas += f5
    sub = [e for e in eventos5 if e.tipo == "sub_evento"]
    print(f"    delegaciones: {t5.delegaciones} · {len(sub)} sub_eventos")
    if set(t5.delegaciones) != {"agente_abastecimiento", "agente_operaciones"}:
        problemas.append(f"N5 debe delegar en los dos agentes; delegó en {t5.delegaciones}")
    if t5.errores:
        problemas.append(f"N5: un sub-agente falló: {t5.errores}")
    if t5.llamadas_llm <= t4.llamadas_llm:
        problemas.append(
            f"N5 ({t5.llamadas_llm} llamadas) debe costar más que N4 ({t4.llamadas_llm})"
        )

    print("\n── La factura (spec 05) ───────────────────────────────────────")
    base = t1.tokens_in + t1.tokens_out
    for nombre, t in (("n1", t1), ("n2", t2), ("n3", t3), ("n4", t4), ("n5", t5)):
        tok = t.tokens_in + t.tokens_out
        rel = f"{tok / base:.1f}×" if base else "—"
        print(f"  {nombre}: {t.llamadas_llm:>2} llamadas · {tok:>5} tokens · {rel:>5} N1")

    print("\n── Casos que no deben inventar ────────────────────────────────")
    from backend.tools.operaciones import consultar_inventario

    for texto in ("planta de Cali", "la planta de Cali", "Medellín"):
        r = consultar_inventario(texto)
        ok = r.get("encontrado") is False
        print(f"  {'✓' if ok else '✕'} {texto!r} → {'no encontrada' if ok else r.get('planta')}")
        if not ok:
            problemas.append(
                f"consultar_inventario({texto!r}) resolvió a {r.get('planta')!r}: "
                "inventar una coincidencia rompe la demo de cierre de N4"
            )

    print("\n── La vista El caso (spec 11) ───────────────────────────────")
    problemas += verificar_caso()

    print()
    if problemas:
        print(f"✕ {len(problemas)} problema(s):\n")
        for p in problemas:
            print(f"  · {p}")
        return 1
    print("→ Los cinco niveles cumplen el contrato y las tools no inventan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(principal()))
