"""Cliente del modelo, caché, reintentos y contador de gasto.

Spec 09. Todo lo de este módulo existe por una decisión tomada: **una sola API key
para las 15 personas**. Sin mitigaciones, en el bloque de N3 quince personas
ejecutan sus celdas casi al mismo tiempo, los límites del proveedor se aplican por
organización y el resultado son errores 429 en cascada justo en el momento
pedagógico más importante de la clase. No es un riesgo hipotético; es la
consecuencia aritmética de la decisión.

Cuatro capas, en orden de importancia:

  1a. Caché en disco con FIDELIDAD TEMPORAL (la principal)
  1b. Semáforo de concurrencia
  1c. Reintentos con backoff exponencial y jitter
  1d. Modelo económico por defecto (en `config`)

Más el tope duro de gasto del Riesgo 3.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from backend.config import VERSION, config
from backend.eventos import deserializar, serializar

# --- Reintentos (spec 09, 1c) -------------------------------------------------
MAX_REINTENTOS = 4
BASE_ESPERA_S = 1.0
FACTOR = 2.0
JITTER = 0.30  # ±30%


# ---------------------------------------------------------------------------
#  Estado del laboratorio: modo, gasto, conmutación
# ---------------------------------------------------------------------------


class EstadoLab:
    """Estado mutable compartido por el tablero y el notebook del mismo proceso."""

    def __init__(self) -> None:
        self.modo: str = config.modo_inicial()
        self.gasto_usd: float = 0.0
        self.llamadas: int = 0
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.por_nivel: dict[str, dict[str, float]] = {}
        # Motivo de la conmutación automática a replay. El tablero lo convierte en
        # un banner de ancho completo, NO en un badge (spec 07): el facilitador
        # está mirando al grupo, no la esquina de la pantalla.
        self.aviso_replay: str | None = None
        self._semaforo: asyncio.Semaphore | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # El semáforo se crea perezosamente y atado al loop en uso: en el notebook y
    # en uvicorn el loop no es el mismo, y un semáforo creado en otro loop falla.
    def semaforo(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._semaforo is None or self._loop is not loop:
            self._semaforo = asyncio.Semaphore(config.max_concurrencia)
            self._loop = loop
        return self._semaforo

    @property
    def vivo(self) -> bool:
        return self.modo == "vivo"

    def conmutar_a_replay(self, motivo: str) -> None:
        if self.modo == "replay":
            return
        self.modo = "replay"
        self.aviso_replay = motivo

    def registrar_uso(self, nivel: str, tokens_in: int, tokens_out: int) -> float:
        costo = config.costo_usd(tokens_in, tokens_out)
        self.llamadas += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.gasto_usd += costo
        n = self.por_nivel.setdefault(
            nivel, {"llamadas": 0, "tokens_in": 0, "tokens_out": 0, "costo_usd": 0.0}
        )
        n["llamadas"] += 1
        n["tokens_in"] += tokens_in
        n["tokens_out"] += tokens_out
        n["costo_usd"] += costo

        # Tope duro (spec 09, Riesgo 3): al alcanzarlo se conmuta a replay y se
        # avisa. No falla ni se detiene.
        if config.costo_configurado and self.gasto_usd >= config.tope_usd:
            self.conmutar_a_replay(
                f"Se alcanzó el tope de gasto configurado (${config.tope_usd:.2f}). "
                "El laboratorio sigue funcionando con trazas pregrabadas."
            )
        return costo

    def resumen(self) -> dict:
        return {
            "modo": self.modo,
            "gasto_usd": round(self.gasto_usd, 6),
            "tope_usd": config.tope_usd,
            "costo_configurado": config.costo_configurado,
            "llamadas_totales": self.llamadas,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "por_nivel": {
                k: {**v, "costo_usd": round(v["costo_usd"], 6)}
                for k, v in self.por_nivel.items()
            },
            "aviso_replay": self.aviso_replay,
        }


estado_lab = EstadoLab()


def estado() -> dict:
    """Imprime y devuelve el estado. Es la primera celda útil del notebook.

    Nunca imprime la key, solo si está presente.
    """
    r = estado_lab.resumen()
    print(f"modo            : {r['modo']}")
    print(f"modelo          : {config.openai_model}")
    print(f"key presente    : {'sí' if config.key_presente else 'no'}")
    if config.costo_configurado:
        print(f"gasto acumulado : ${r['gasto_usd']:.4f} de ${config.tope_usd:.2f}")
    else:
        print(
            f"gasto acumulado : costo no configurado "
            f"({r['tokens_in']}+{r['tokens_out']} tokens en {r['llamadas_totales']} llamadas)"
        )
    print(f"caché           : {'activo' if config.cache_activo else 'desactivado'}")
    if r["aviso_replay"]:
        print(f"⚠ {r['aviso_replay']}")
    return r


# ---------------------------------------------------------------------------
#  Clientes
# ---------------------------------------------------------------------------


def cliente(modelo: str | None = None, **kwargs: Any):
    """Cliente de chat de LangChain. Lo usan N2, N4 y N5.

    `temperature=0` a propósito: con quince personas haciendo la misma pregunta,
    la variación aleatoria entre respuestas hace imposible comparar niveles y
    arruina el caché.
    """
    from langchain_openai import ChatOpenAI

    if not config.key_presente:
        raise RuntimeError(
            "No hay OPENAI_API_KEY configurada. El laboratorio funciona en "
            "MODO=replay sin key; si quieres ejecución real, pega la key en .env."
        )
    opciones = {"model": modelo or config.openai_model, "temperature": 0}
    opciones.update(kwargs)
    return ChatOpenAI(api_key=config.openai_api_key, **opciones)


def cliente_crudo():
    """Cliente de OpenAI sin envolturas. Lo usa N3.

    ADR-002/003: N3 escribe el loop de function calling a mano y necesita la
    respuesta cruda del proveedor para poder mostrar el JSON de la tool call tal
    como llegó. Con la abstracción de alto nivel ese JSON no se ve.
    """
    from openai import AsyncOpenAI

    if not config.key_presente:
        raise RuntimeError(
            "No hay OPENAI_API_KEY configurada. El laboratorio funciona en "
            "MODO=replay sin key; si quieres ejecución real, pega la key en .env."
        )
    return AsyncOpenAI(api_key=config.openai_api_key)


def esquemas_openai(funciones: list[Callable]) -> list[dict]:
    """Convierte funciones Python al esquema de tools de OpenAI.

    Lo que viaja al modelo sale de las anotaciones de tipo y de la docstring. Es
    la demostración literal de que **la docstring es el prompt**: se puede
    imprimir esto en clase y ver la propia docstring dentro del payload.
    """
    from langchain_core.utils.function_calling import convert_to_openai_tool

    return [convert_to_openai_tool(f) for f in funciones]


# ---------------------------------------------------------------------------
#  Concurrencia y reintentos (spec 09, 1b y 1c)
# ---------------------------------------------------------------------------


def _es_reintentable(exc: BaseException) -> bool:
    nombre = type(exc).__name__
    if nombre in {"RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError"}:
        return True
    codigo = getattr(exc, "status_code", None)
    return isinstance(codigo, int) and (codigo == 429 or 500 <= codigo < 600)


def _espera(intento: int) -> float:
    """Backoff exponencial con jitter de ±30%.

    El jitter no es un detalle: sin él, quince clientes que reciben 429 al mismo
    tiempo esperan lo mismo, reintentan sincronizados y se vuelven a chocar.
    """
    base = BASE_ESPERA_S * (FACTOR**intento)
    return base * random.uniform(1 - JITTER, 1 + JITTER)


async def con_reintentos(
    accion: Callable[[], Any],
    nivel: str = "?",
    al_reintentar: Callable[[str, int, float], Any] | None = None,
) -> Any:
    """Ejecuta `accion` respetando el semáforo, reintentando 429 y 5xx.

    `al_reintentar` recibe (mensaje, n_intento, espera_s) para que el nivel emita
    un evento `error` con `recuperable: true`. Que el reintento se vea en la traza
    es contenido de clase, no ruido: manejo de errores es tema de la Sesión 5.
    """
    ultimo: BaseException | None = None
    for intento in range(MAX_REINTENTOS + 1):
        try:
            async with estado_lab.semaforo():
                return await accion()
        except Exception as exc:  # noqa: BLE001 — se reclasifica abajo
            ultimo = exc
            if not _es_reintentable(exc) or intento == MAX_REINTENTOS:
                raise
            espera = _espera(intento)
            if al_reintentar is not None:
                al_reintentar(f"{type(exc).__name__}: {exc}", intento + 1, espera)
            await asyncio.sleep(espera)
    if ultimo:
        raise ultimo
    raise RuntimeError("con_reintentos terminó sin resultado")


# ---------------------------------------------------------------------------
#  Caché con fidelidad temporal (spec 04 y spec 09, 1a)
# ---------------------------------------------------------------------------


def clave_cache(
    nivel: str, pregunta: str, system_prompt: str, variante: str = ""
) -> str:
    """sha256(nivel + pregunta + modelo + hash(prompt) + semilla + fecha + variante).

    Dos componentes de la clave no son obvios y los dos vienen de un fallo real:

    · **La fecha de referencia.** Los datos se generan hacia atrás desde ella, así
      que con `FECHA_REFERENCIA` vacía la base cambia cada día. Una clave que la
      ignorara serviría hoy las respuestas de la base de ayer.

    · **La variante.** Es la huella de la implementación que se está ejecutando. Sin
      ella, un participante con un N3 a medio escribir recibiría la traza cacheada
      del N3 correcto del facilitador, sus `assert` pasarían y el ejercicio quedaría
      anulado sin que nadie lo note. Con ella, el caché se comparte entre quienes
      escribieron el MISMO código —que es la mayoría, y ahí sigue protegiendo la key
      compartida— y no entre implementaciones distintas.
    """
    modelo = (
        config.modelo_del_supervisor if nivel == "n5" else config.openai_model
    )
    material = "|".join(
        [
            nivel,
            " ".join(pregunta.strip().lower().split()),
            modelo,
            hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16],
            str(config.semilla_datos),
            config.fecha_base.isoformat(),
            variante,
            VERSION,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _ruta_cache(clave: str) -> Path:
    return config.ruta_cache / f"{clave}.json"


def leer_cache(clave: str) -> list[dict] | None:
    if not config.cache_activo:
        return None
    ruta = _ruta_cache(clave)
    if not ruta.exists():
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    eventos = datos.get("eventos")
    return eventos if isinstance(eventos, list) and eventos else None


def guardar_cache(clave: str, eventos: list[Any], pregunta: str, nivel: str) -> None:
    """Guarda la SECUENCIA COMPLETA de eventos, con sus `ts_ms` y sus métricas.

    Guardar solo el texto final sería la implementación obvia y destruiría la
    lección central del laboratorio: el valor de la vista comparación está en que
    N1 termina en un segundo y N5 sigue trabajando diez segundos después. Un caché
    que devuelve en 20 ms aplana esa asimetría y las cinco columnas se ven iguales.
    """
    if not config.cache_activo or not eventos:
        return
    try:
        config.ruta_cache.mkdir(parents=True, exist_ok=True)
        _ruta_cache(clave).write_text(
            json.dumps(
                {
                    "nivel": nivel,
                    "pregunta": pregunta,
                    "modelo": config.openai_model,
                    "version": VERSION,
                    "eventos": [serializar(e) for e in eventos],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        # Un caché que no se puede escribir no debe tumbar una ejecución válida.
        pass


async def reproducir(
    eventos: list[dict],
    run_id: str,
    fidelidad_temporal: bool = True,
) -> AsyncIterator[Any]:
    """Reemite eventos guardados respetando sus tiempos originales.

    Es el mecanismo compartido por el caché (por pregunta) y por el modo replay
    (por traza pregrabada). En los dos casos la ejecución tarda en pantalla lo
    mismo que tardó la real, así que la asimetría entre columnas se conserva.

    `desde_cache` se marca en `inicio` y en `metricas`, y el costo se reporta en 0
    con las métricas originales de tokens y tiempo. Es honesto y didáctico: la
    primera vez que alguien ve que su ejecución fue gratis hay una conversación de
    treinta segundos sobre caching.
    """
    inicio_real = time.monotonic()
    for crudo in eventos:
        datos = dict(crudo)
        datos["run_id"] = run_id
        if datos.get("tipo") in {"inicio", "metricas"}:
            datos["desde_cache"] = True
        if datos.get("tipo") == "metricas":
            datos["costo_usd"] = 0.0
            datos["costo_configurado"] = config.costo_configurado

        if fidelidad_temporal:
            objetivo = datos.get("ts_ms", 0) / 1000.0
            retraso = objetivo - (time.monotonic() - inicio_real)
            if retraso > 0:
                await asyncio.sleep(min(retraso, 30.0))
        yield deserializar(datos)


# ---------------------------------------------------------------------------
#  Trazas pregrabadas (modo replay, spec 09, Riesgo 2)
# ---------------------------------------------------------------------------

_trazas: dict[str, list[dict]] | None = None


def _cargar_trazas() -> dict[str, list[dict]]:
    global _trazas
    if _trazas is None:
        ruta = config.ruta_trazas
        if ruta.exists():
            try:
                _trazas = json.loads(ruta.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _trazas = {}
        else:
            _trazas = {}
    return _trazas


def clave_traza(nivel: str, pregunta: str) -> str:
    return f"{nivel}|{' '.join(pregunta.strip().lower().split())}"


def traza_pregrabada(nivel: str, pregunta: str) -> list[dict] | None:
    """Traza exacta para esa pregunta, o la del mismo nivel más parecida.

    El respaldo por nivel existe porque en replay alguien va a escribir una
    pregunta libre, y una columna vacía en medio de la demo es peor que una traza
    de otra pregunta claramente marcada como pregrabada.
    """
    trazas = _cargar_trazas()
    exacta = trazas.get(clave_traza(nivel, pregunta))
    if exacta:
        return exacta
    for clave, eventos in trazas.items():
        if clave.startswith(f"{nivel}|"):
            return eventos
    return None


# ---------------------------------------------------------------------------
#  Verificación de entorno (spec 08, sección 0)
# ---------------------------------------------------------------------------


def verificar_entorno(probar_api: bool = True) -> bool:
    """Comprueba que todo está listo. Cada fallo dice QUÉ HACER, no solo qué pasó.

    Es lo que se pide correr en el preflight de 24-48 h antes de la clase
    (spec 09, Riesgo 4). Si el preflight se hace en clase, se van 25 de los 55
    minutos de hands-on.
    """
    import sys

    ok = True
    print(f"✓ Python {sys.version.split()[0]}")

    try:
        import langgraph

        print(f"✓ langgraph {getattr(langgraph, '__version__', '?')}")
    except ImportError:
        print("✕ Falta langgraph.  → pip install -r requirements.txt")
        ok = False

    try:
        from backend.db import conteo_por_tabla

        conteos = conteo_por_tabla()
        total = sum(conteos.values())
        print(f"✓ bios_ops.db  ({len(conteos)} tablas, {total:,} filas)".replace(",", "."))
    except Exception as exc:  # noqa: BLE001
        print(f"✕ Base de datos: {exc}")
        ok = False

    from backend.tools import TODAS

    print(f"✓ {len(TODAS)} tools cargadas")

    if config.key_presente:
        print("✓ OPENAI_API_KEY presente")
    else:
        print(
            "◐ OPENAI_API_KEY ausente o sin editar.\n"
            "  El notebook funciona igual en modo replay. Para ejecución real:\n"
            "    1. cp .env.example .env\n"
            "    2. pega la key en OPENAI_API_KEY"
        )

    if probar_api and config.key_presente:
        try:
            t0 = time.monotonic()
            resp = cliente().invoke("Responde solo: ok")
            ms = int((time.monotonic() - t0) * 1000)
            texto = (resp.content or "").strip()[:20]
            print(f"✓ Conectividad con la API: {ms} ms  (respondió «{texto}»)")
        except Exception as exc:  # noqa: BLE001
            print(
                f"✕ No pude llamar a la API: {type(exc).__name__}: {exc}\n"
                "  Revisa: la key es válida · el modelo está habilitado en la cuenta ·\n"
                "  hay salida a internet. Mientras tanto, usa MODO=replay."
            )
            ok = False

    print(f"\nmodo actual: {estado_lab.modo}")
    print(
        "→ Todo listo. Puedes empezar por la sección 1."
        if ok
        else "→ Resuelve lo marcado con ✕ antes de la clase."
    )
    return ok
