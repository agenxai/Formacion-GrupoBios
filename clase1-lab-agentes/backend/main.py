"""FastAPI: rutas y SSE. Spec 04, sección 3.

Sobre `run_id` y `seq` — decisión que vale explicar porque afecta a los invariantes:

`POST /api/ejecutar` con cinco niveles arranca **cinco runs independientes**, no uno
con cinco ramas. Cada nivel lleva su propio `run_id` (`{grupo}:{nivel}`) y su propio
`seq` desde 0. Es lo que hace que el invariante 2 —`seq` estrictamente creciente y
sin huecos dentro de un run— se pueda verificar por nivel, y lo que permite cachear
y reproducir un nivel suelto.

El `run_id` que devuelve el POST y que va en `GET /api/stream/{run_id}` es el id del
**grupo**: un solo stream por el que llegan los eventos de los cinco niveles,
intercalados y separados por el campo `nivel`.

ADR-006: SSE y no WebSocket. Unidireccional servidor→cliente es exactamente lo que
se necesita, `EventSource` reconecta solo y se depura con `curl`. Y como
`EventSource` solo hace GET, el flujo es POST para crear y GET para escuchar.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import preguntas as cat_preguntas
from backend import prompts
from backend.config import VERSION, config
from backend.db.constantes import AVISO_DATOS_SINTETICOS
from backend.eventos import serializar
from backend.llm import estado_lab
from backend.niveles import NIVELES, ORDEN, cancelar, metadatos

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

SEGUNDOS_PING = 15
# Cuántos grupos de ejecución se guardan en memoria. Alcanza de sobra para una
# sesión y evita que el proceso crezca sin techo si alguien deja el tablero abierto.
MAX_GRUPOS = 60

@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Ciclo de vida del servicio. `lifespan`, no `on_event`: este último está
    deprecado en FastAPI y su aviso saldría en la consola durante la clase."""
    anunciar()
    yield


app = FastAPI(
    title="Laboratorio · Niveles de Agencia",
    description=(
        "Componente práctico de la Sesión 1 del programa de IA de Qypher para "
        "Grupo Bios. Los datos son sintéticos: " + AVISO_DATOS_SINTETICOS
    ),
    version=VERSION,
    lifespan=ciclo_de_vida,
)


def anunciar() -> None:
    """Banner de arranque. Es lo que se ve en `docker compose up`.

    Existe para que el estado del laboratorio se lea de un vistazo antes de
    proyectar: base, modo, modelo y si hay trazas de replay. Descubrir en el
    minuto 12 de la clase que faltaban las trazas es evitable con cuatro líneas.

    NUNCA imprime el valor de la key, solo si está presente (spec 09, Riesgo 5).
    """
    from backend.db import conteo_por_tabla

    try:
        conteos = conteo_por_tabla()
        filas = f"{sum(conteos.values()):,}".replace(",", ".")
        print(f"✓ bios_ops.db  {len(conteos)} tablas · {filas} filas")
    except Exception as exc:  # noqa: BLE001
        print(f"✕ bios_ops.db no disponible: {exc}")

    key = "presente" if config.key_presente else "ausente"
    print(
        f"✓ modo: {estado_lab.modo}   modelo: {config.openai_model}   key: {key}"
    )
    if not config.costo_configurado:
        print(
            "◐ tarifas sin configurar: el tablero mostrará «costo no configurado» "
            "y comparará por tokens"
        )
    if estado_lab.modo == "replay":
        n = len(_cargar_trazas_para_banner())
        if n:
            print(f"✓ modo replay con {n} trazas pregrabadas")
        else:
            print(
                "◐ modo replay SIN trazas pregrabadas. Grábalas con:\n"
                "    docker compose exec tablero python -m backend.replay.grabar"
            )


def _cargar_trazas_para_banner() -> dict:
    from backend.llm import _cargar_trazas

    return _cargar_trazas()


# ---------------------------------------------------------------------------
#  Registro de ejecuciones
# ---------------------------------------------------------------------------


class Grupo:
    """Una pulsación de «Ejecutar»: N runs de nivel compartiendo un stream."""

    def __init__(self, grupo_id: str, pregunta: str, niveles: list[str]) -> None:
        self.id = grupo_id
        self.pregunta = pregunta
        self.niveles = niveles
        self.eventos: list[dict] = []
        self.suscriptores: list[asyncio.Queue] = []
        self.pendientes = len(niveles)
        self.creado = time.time()

    @property
    def terminado(self) -> bool:
        return self.pendientes <= 0

    def publicar(self, evento: dict) -> None:
        """Guarda el evento en la traza y lo reparte. El índice en `eventos` es el
        `id:` del SSE, así que aquí solo entra lo que se emite de verdad."""
        self.eventos.append(evento)
        for cola in list(self.suscriptores):
            cola.put_nowait(evento)

    def notificar(self, control: dict) -> None:
        """Señal interna para los suscriptores. NO entra a la traza.

        Si entrara, el índice de `eventos` dejaría de coincidir con el `id:` que
        va por el stream y una reconexión con `Last-Event-ID` reenviaría desde el
        lugar equivocado.
        """
        for cola in list(self.suscriptores):
            cola.put_nowait(control)

    def ultimo_seq(self, nivel_id: str) -> int:
        for evento in reversed(self.eventos):
            if evento.get("nivel") == nivel_id:
                return int(evento.get("seq", -1))
        return -1

    def suscribir(self, desde: int = 0) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue()
        # Reenvío desde `seq` para que una reconexión de EventSource no pierda
        # nada: un corte de red no arruina la demo en curso.
        for evento in self.eventos[desde:]:
            cola.put_nowait(evento)
        self.suscriptores.append(cola)
        return cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        if cola in self.suscriptores:
            self.suscriptores.remove(cola)


GRUPOS: dict[str, Grupo] = {}


def _podar() -> None:
    if len(GRUPOS) <= MAX_GRUPOS:
        return
    viejos = sorted(GRUPOS.values(), key=lambda g: g.creado)[: len(GRUPOS) - MAX_GRUPOS]
    for g in viejos:
        GRUPOS.pop(g.id, None)


async def _correr_nivel(grupo: Grupo, nivel_id: str) -> None:
    nivel = NIVELES[nivel_id]
    run_id = f"{grupo.id}:{nivel_id}"
    try:
        async for evento in nivel.ejecutar(grupo.pregunta, run_id):
            grupo.publicar(serializar(evento))
    except Exception as exc:  # noqa: BLE001
        # `NivelBase.ejecutar` ya captura sus fallos y cierra con `fin`. Si algo
        # llegara acá, se publica para que la columna no quede colgada en silencio.
        # El `seq` continúa el del run para no romper el invariante 2.
        siguiente = grupo.ultimo_seq(nivel_id) + 1
        grupo.publicar(
            {
                "tipo": "error",
                "nivel": nivel_id,
                "run_id": run_id,
                "seq": siguiente,
                "ts_ms": 0,
                "mensaje": f"{type(exc).__name__}: {exc}",
                "recuperable": False,
                "reintento": None,
            }
        )
        grupo.publicar(
            {
                "tipo": "fin",
                "nivel": nivel_id,
                "run_id": run_id,
                "seq": siguiente + 1,
                "ts_ms": 0,
                "estado": "error",
            }
        )
    finally:
        grupo.pendientes -= 1
        # Despierta a los suscriptores para que evalúen si ya terminó todo.
        grupo.notificar({"__control__": "nivel_terminado", "nivel": nivel_id})


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------


class Peticion(BaseModel):
    pregunta: str = Field(min_length=1, max_length=2000)
    niveles: list[str] = Field(default_factory=lambda: list(ORDEN))


class PruebaTool(BaseModel):
    """El botón «Probar» de la vista El caso (spec 11).

    Pide «el ejemplo N de la tool X»; los argumentos salen del catálogo curado de
    `tools/ejemplos.py`, nunca del cliente. No hay forma de pasar argumentos
    arbitrarios — es la lista blanca de siempre aplicada a la demo.
    """

    herramienta: str
    ejemplo: int = 0


@app.get("/api/salud")
def salud() -> dict:
    """Estado del laboratorio. Nunca incluye la API key, solo si está presente."""
    return {
        "modo": estado_lab.modo,
        "modelo": config.openai_model,
        "key_presente": config.key_presente,
        "gasto_usd": round(estado_lab.gasto_usd, 6),
        "tope_usd": config.tope_usd,
        "costo_configurado": config.costo_configurado,
        "cache_activo": config.cache_activo,
        "aviso_replay": estado_lab.aviso_replay,
        "aviso_datos": AVISO_DATOS_SINTETICOS,
        "version": VERSION,
    }


@app.get("/api/niveles")
def niveles() -> list[dict]:
    return metadatos()


@app.get("/api/preguntas")
def preguntas() -> dict:
    return cat_preguntas.catalogo()


@app.get("/api/esquema")
def esquema() -> dict:
    from backend.db import conteo_por_tabla

    try:
        conteos = conteo_por_tabla()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"Base de datos no disponible: {exc}") from exc
    return {
        "aviso_datos": AVISO_DATOS_SINTETICOS,
        "tablas": conteos,
        "total_filas": sum(conteos.values()),
        "semilla": config.semilla_datos,
        "fecha_referencia": config.fecha_base.isoformat(),
    }


# ---------------------------------------------------------------------------
#  El caso (spec 11): la vista previa a los niveles
# ---------------------------------------------------------------------------


@app.get("/api/caso")
def el_caso() -> dict:
    """El agregado de la vista El caso: escenario, tablas, herramientas, preguntas.

    Todo se lee de la base y de los módulos de dominio en cada llamada: si la base
    se regenera, la vista cambia con ella sin tocar una línea.
    """
    from backend import caso

    try:
        return caso.agregado()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"Base de datos no disponible: {exc}") from exc


@app.post("/api/tools/probar")
def probar_tool(peticion: PruebaTool) -> dict:
    """Ejecuta un ejemplo curado de una tool, SIN llamar al modelo.

    Los tres invariantes de la spec 11: no pasa por `llm.py` (el gasto queda
    idéntico), no escribe en la base (hereda la conexión de solo lectura de las
    tools) y solo ejecuta ejemplos del catálogo curado.
    """
    from backend.tools import ejemplos

    try:
        return ejemplos.ejecutar(peticion.herramienta, peticion.ejemplo)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — una tool no lanza; si lanzó, es un defecto
        raise HTTPException(
            500, f"La herramienta falló: {type(exc).__name__}: {exc}"
        ) from exc


@app.get("/api/prompts")
def leer_prompts() -> dict:
    return {"vigentes": prompts.todos(), "originales": dict(prompts.ORIGINALES)}


@app.put("/api/prompts/{nivel}")
def escribir_prompt(nivel: str, texto: str = Body(..., embed=True)) -> dict:
    """Reemplaza un system prompt en runtime. Sin persistencia y SIN AUTENTICACIÓN.

    Es deliberado: es una herramienta de demo en una red de sala. Por eso los
    puertos se publican solo en 127.0.0.1 (spec 09, Riesgo 5). Exponer este
    endpoint en la red de la oficina sería entregar el prompt del sistema a
    cualquiera.
    """
    try:
        prompts.fijar(nivel, texto)
    except KeyError as exc:
        raise HTTPException(404, f"No existe el nivel '{nivel}'.") from exc
    return {"nivel": nivel, "texto": prompts.obtener(nivel)}


@app.post("/api/prompts/reset")
def reset_prompts() -> dict:
    return {"vigentes": prompts.restaurar()}


@app.post("/api/ejecutar")
async def ejecutar(peticion: Peticion) -> dict:
    """Crea el grupo y devuelve su id. No bloquea: los niveles corren en paralelo."""
    pedidos = [n for n in peticion.niveles if n in NIVELES]
    if not pedidos:
        raise HTTPException(
            400,
            f"Ningún nivel válido en {peticion.niveles}. Válidos: {', '.join(ORDEN)}",
        )
    pedidos = [n for n in ORDEN if n in pedidos]  # orden estable de columnas

    grupo = Grupo(str(uuid.uuid4()), peticion.pregunta.strip(), pedidos)
    GRUPOS[grupo.id] = grupo
    _podar()

    for nivel_id in pedidos:
        asyncio.create_task(_correr_nivel(grupo, nivel_id))

    return {"run_id": grupo.id, "niveles": pedidos, "modo": estado_lab.modo}


@app.get("/api/stream/{run_id}")
async def stream(run_id: str, request: Request) -> StreamingResponse:
    grupo = GRUPOS.get(run_id)
    if grupo is None:
        raise HTTPException(404, f"No existe la ejecución '{run_id}'.")

    ultimo = request.headers.get("last-event-id")
    desde = 0
    if ultimo and ultimo.isdigit():
        desde = int(ultimo) + 1

    async def generar():
        cola = grupo.suscribir(desde)
        indice = desde
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evento = await asyncio.wait_for(cola.get(), timeout=SEGUNDOS_PING)
                except asyncio.TimeoutError:
                    # Comentario SSE de keep-alive. Sin esto, un proxy corporativo
                    # puede cortar la conexión en medio de la demo.
                    yield ": ping\n\n"
                    if grupo.terminado and cola.empty():
                        break
                    continue

                if evento.get("__control__"):
                    if grupo.terminado and cola.empty():
                        yield "event: cerrado\ndata: {}\n\n"
                        break
                    continue

                yield (
                    f"id: {indice}\n"
                    f"event: evento\n"
                    f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
                )
                indice += 1
        finally:
            grupo.desuscribir(cola)

    return StreamingResponse(
        generar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/cancelar/{run_id}")
def cancelar_run(run_id: str) -> dict:
    grupo = GRUPOS.get(run_id)
    if grupo is None:
        raise HTTPException(404, f"No existe la ejecución '{run_id}'.")
    for nivel_id in grupo.niveles:
        cancelar(f"{run_id}:{nivel_id}")
    return {"run_id": run_id, "cancelado": True}


@app.post("/api/marcar_sin_fuente/{run_id}")
def marcar_sin_fuente(run_id: str, nivel: str = "n1") -> dict:
    """Respaldo manual del aviso de N1 (spec 05).

    La heurística por expresión regular falla ante «alrededor de media tonelada» o
    «unas 450», y falla en el clímax de la demo con el grupo mirando. Diseñar la
    demo para que dependa de un regex acertando en vivo es exactamente el tipo de
    fragilidad que esta formación enseña a evitar; este endpoint es la
    implementación de ese principio sobre nuestro propio producto.

    El evento entra a la traza del grupo, no solo a la pantalla.
    """
    grupo = GRUPOS.get(run_id)
    if grupo is None:
        raise HTTPException(404, f"No existe la ejecución '{run_id}'.")
    from backend.niveles.n1_procesador import TEXTO_AVISO

    evento = {
        "tipo": "aviso",
        "nivel": nivel,
        "run_id": f"{run_id}:{nivel}",
        "seq": len(grupo.eventos),
        "ts_ms": 0,
        "mensaje": TEXTO_AVISO + " (marcado por el facilitador)",
        "gravedad": "alerta",
    }
    grupo.publicar(evento)
    return evento


@app.get("/api/gasto")
def gasto() -> dict:
    return estado_lab.resumen()


@app.get("/api/traza/{run_id}")
def traza(run_id: str) -> dict:
    """Eventos completos de un grupo. Lo usa la Vista B del tablero."""
    grupo = GRUPOS.get(run_id)
    if grupo is None:
        raise HTTPException(404, f"No existe la ejecución '{run_id}'.")
    return {
        "run_id": run_id,
        "pregunta": grupo.pregunta,
        "niveles": grupo.niveles,
        "terminado": grupo.terminado,
        "eventos": grupo.eventos,
    }


# ---------------------------------------------------------------------------
#  Frontend — servido por el mismo FastAPI: sin CORS, sin segundo puerto
# ---------------------------------------------------------------------------

if (FRONTEND / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/app.js")
def app_js() -> FileResponse:
    return FileResponse(FRONTEND / "app.js", media_type="application/javascript")


@app.get("/diagrama.js")
def diagrama_js() -> FileResponse:
    return FileResponse(FRONTEND / "diagrama.js", media_type="application/javascript")


@app.get("/caso.js")
def caso_js() -> FileResponse:
    return FileResponse(FRONTEND / "caso.js", media_type="application/javascript")


@app.get("/estilos.css")
def estilos() -> FileResponse:
    return FileResponse(FRONTEND / "estilos.css", media_type="text/css")


@app.get("/caso.css")
def caso_css() -> FileResponse:
    return FileResponse(FRONTEND / "caso.css", media_type="text/css")
