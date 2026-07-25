"""Contrato de eventos — el módulo del que depende todo lo demás.

Spec 04, sección 1. Los cinco niveles son arquitecturas distintas: uno solo llama al
modelo, otro corre un grafo de LangGraph, otro delega en sub-agentes. Si cada uno
reportara su actividad a su manera, el frontend tendría cinco lógicas de render y la
comparación entre niveles sería incomparable — estaríamos midiendo con cinco reglas
distintas.

Todos los niveles emiten el mismo stream de eventos tipados. El frontend no sabe qué
nivel está renderizando.

Seguridad (spec 09, Riesgo 5): la serialización es por **lista blanca** de campos.
Eso lo garantiza `extra="forbid"` más el hecho de que Pydantic solo serializa los
campos declarados: un campo que nadie previó no puede colarse en el stream. El
chequeo de `_sin_credenciales` es una segunda barrera redundante, no la principal.
"""

from __future__ import annotations

import time
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

# Recorte de los mensajes que viajan al frontend (spec 04: "ya recortado a 2000 car.")
LIMITE_CARACTERES_MENSAJE = 2000


class _Base(BaseModel):
    """Campos comunes a todo evento (spec 04, "Campos comunes")."""

    # extra="forbid" es la lista blanca: nada que no esté declarado entra al evento.
    model_config = ConfigDict(extra="forbid")

    nivel: str
    run_id: str
    seq: int
    # Milisegundos desde el inicio del run. RELATIVO, no epoch — así las columnas
    # del modo comparación se alinean en el mismo eje temporal.
    ts_ms: int


class Inicio(_Base):
    tipo: Literal["inicio"] = "inicio"
    pregunta: str
    modelo: str
    desde_cache: bool = False


class LlmRequest(_Base):
    tipo: Literal["llm_request"] = "llm_request"
    n_llamada: int  # 1-indexado dentro del run
    mensajes: list[dict]  # rol + contenido, ya recortado
    tools_declaradas: list[str]  # [] en N1 y N2


class LlmResponse(_Base):
    tipo: Literal["llm_response"] = "llm_response"
    n_llamada: int
    texto: str | None = None
    hay_tool_calls: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    ms: int = 0


class Pensamiento(_Base):
    """El "Thought" del patrón ReAct (ebook 6.1). Solo N4/N5.

    Puede venir vacío: con los modelos actuales de tool calling el razonamiento
    previo a la acción no siempre llega como texto separado. El tablero lo muestra
    vacío en lugar de fabricarlo — presentar un "Thought" inventado por la UI sería
    enseñar mal el patrón (spec 04, "Nota sobre pensamiento").
    """

    tipo: Literal["pensamiento"] = "pensamiento"
    texto: str


class Ruta(_Base):
    """Exclusivo de N2."""

    tipo: Literal["ruta"] = "ruta"
    dominio: Literal["mantenimiento", "compras", "logistica", "demanda"]
    motivo: str


class ToolCall(_Base):
    tipo: Literal["tool_call"] = "tool_call"
    id_llamada: str
    nombre: str
    argumentos: dict
    # ADR-002: el JSON tal cual lo devolvió el modelo, sin parsear ni embellecer.
    # Es lo que se proyecta al lado de la sección 7.2 del ebook.
    crudo: str


class ToolResult(_Base):
    tipo: Literal["tool_result"] = "tool_result"
    id_llamada: str
    nombre: str
    resultado: Any = None
    filas: int | None = None
    ms: int = 0
    error: str | None = None


class Delegacion(_Base):
    """Exclusivo de N5. Abre un sub-run anidado."""

    tipo: Literal["delegacion"] = "delegacion"
    agente: str
    instruccion: str


class RespuestaFinal(_Base):
    tipo: Literal["respuesta_final"] = "respuesta_final"
    texto: str


class Metricas(_Base):
    tipo: Literal["metricas"] = "metricas"
    llamadas_llm: int
    llamadas_tools: int
    tokens_in: int
    tokens_out: int
    costo_usd: float
    ms_total: int
    desde_cache: bool = False
    # False cuando no hay tarifas configuradas: el tablero muestra entonces
    # «costo no configurado» y compara por tokens (spec 09, Riesgo 3).
    costo_configurado: bool = True


class Aviso(_Base):
    tipo: Literal["aviso"] = "aviso"
    mensaje: str
    gravedad: Literal["info", "alerta"] = "info"


class Error(_Base):
    tipo: Literal["error"] = "error"
    mensaje: str
    recuperable: bool = False
    reintento: int | None = None


class Fin(_Base):
    tipo: Literal["fin"] = "fin"
    estado: Literal["ok", "error", "cancelado", "tope_excedido"]


class SubEvento(_Base):
    """Exclusivo de N5: la actividad interna de un sub-agente.

    Invariante 8: el `Evento` anidado numera su `seq` desde 0 dentro de su
    sub-run, y este `sub_evento` consume un `seq` del run padre. Hay un contador
    por run y un contador por sub-run, y no se mezclan.

    Invariante 10: la anidación es de un solo nivel. Un `sub_evento` no contiene
    otro `sub_evento` — un sub-agente no delega. Lo valida `_validar_anidacion`.
    """

    tipo: Literal["sub_evento"] = "sub_evento"
    agente: str
    evento: "Evento"


# Unión discriminada por `tipo`. Es lo que permite que el frontend haga un
# `switch (evento.tipo)` y que FastAPI documente el stream en /docs.
Evento = Annotated[
    Union[
        Inicio,
        LlmRequest,
        LlmResponse,
        Pensamiento,
        Ruta,
        ToolCall,
        ToolResult,
        Delegacion,
        SubEvento,
        RespuestaFinal,
        Metricas,
        Aviso,
        Error,
        Fin,
    ],
    Field(discriminator="tipo"),
]

SubEvento.model_rebuild()

CLASES: dict[str, type[_Base]] = {
    "inicio": Inicio,
    "llm_request": LlmRequest,
    "llm_response": LlmResponse,
    "pensamiento": Pensamiento,
    "ruta": Ruta,
    "tool_call": ToolCall,
    "tool_result": ToolResult,
    "delegacion": Delegacion,
    "sub_evento": SubEvento,
    "respuesta_final": RespuestaFinal,
    "metricas": Metricas,
    "aviso": Aviso,
    "error": Error,
    "fin": Fin,
}

TIPOS = tuple(CLASES)


# --- Emisión ------------------------------------------------------------------


class Emisor:
    """Asigna `seq` y `ts_ms` para que ningún nivel tenga que llevar la cuenta.

    Que los cinco niveles usen el mismo emisor es lo que hace que los invariantes
    2 (seq sin huecos) y 6 (ts_ms monótono) se cumplan por construcción en lugar
    de por disciplina de quien escribe el nivel.
    """

    def __init__(self, nivel: str, run_id: str, t0: float | None = None) -> None:
        self.nivel = nivel
        self.run_id = run_id
        self._seq = 0
        self._t0 = t0 if t0 is not None else time.monotonic()

    @property
    def ms_transcurridos(self) -> int:
        return int((time.monotonic() - self._t0) * 1000)

    def emitir(self, tipo: str, **campos: Any) -> Any:
        """Construye un evento del contrato. Falla si el tipo o los campos no existen."""
        clase = CLASES.get(tipo)
        if clase is None:
            raise ValueError(f"Tipo de evento desconocido: {tipo!r}")
        evento = clase(
            nivel=self.nivel,
            run_id=self.run_id,
            seq=self._seq,
            ts_ms=self.ms_transcurridos,
            **campos,
        )
        self._seq += 1
        return evento

    def sub_emisor(self, nivel: str | None = None) -> "Emisor":
        """Emisor para un sub-run de N5, con su propio contador de `seq`.

        Comparte `t0` con el padre a propósito: así los `ts_ms` del sub-run son
        comparables con los del run que lo contiene y el tablero puede dibujarlos
        en el mismo eje.
        """
        return Emisor(nivel or self.nivel, self.run_id, t0=self._t0)


def recortar(texto: str, limite: int = LIMITE_CARACTERES_MENSAJE) -> str:
    """Recorta dejando dicho explícitamente que se recortó."""
    if len(texto) <= limite:
        return texto
    return texto[:limite] + f"… [recortado, {len(texto)} caracteres en total]"


def mensajes_publicables(mensajes: list[dict]) -> list[dict]:
    """Deja los mensajes en la forma mínima que necesita el tablero.

    Lista blanca de dos campos: `rol` y `contenido`. Cualquier otra cosa que
    traiga el mensaje del proveedor —ids internos, metadata, encabezados— no
    entra al stream.
    """
    salida = []
    for m in mensajes:
        rol = str(m.get("role") or m.get("rol") or "?")
        contenido = m.get("content", m.get("contenido", ""))
        if not isinstance(contenido, str):
            contenido = str(contenido)
        salida.append({"rol": rol, "contenido": recortar(contenido)})
    return salida


def serializar(evento: Any) -> dict:
    """Evento → dict listo para SSE o para el caché.

    Segunda barrera de seguridad, redundante con la lista blanca: si la API key
    apareciera en algún campo, esto lanza en lugar de publicarla.
    """
    datos = evento.model_dump(mode="json")
    _sin_credenciales(datos)
    return datos


def _sin_credenciales(datos: dict) -> None:
    from backend.config import config

    key = config.openai_api_key.strip()
    if not config.key_presente or len(key) < 12:
        return
    # Se busca la key completa y su prefijo largo: un fragmento suelto de 8
    # caracteres produciría falsos positivos.
    import json

    plano = json.dumps(datos, ensure_ascii=False)
    if key in plano or key[:20] in plano:
        raise RuntimeError(
            "Un evento contenía la API key y no se publicó. Esto es un defecto "
            "del nivel que lo emitió, no del contrato."
        )


def deserializar(datos: dict) -> Any:
    """dict → evento tipado. Se usa al leer el caché y las trazas de replay."""
    clase = CLASES.get(datos.get("tipo", ""))
    if clase is None:
        raise ValueError(f"Traza con tipo de evento desconocido: {datos.get('tipo')!r}")
    return clase.model_validate(datos)


# --- Resumen de una traza (lo que usa el notebook) ----------------------------


class Traza(BaseModel):
    """Vista agregada de un run. Es lo que devuelve `ultima_traza()` en el notebook.

    Existe para que las celdas de verificación de la spec 08 se lean como los
    criterios de aceptación de la spec 05:

        assert traza.llamadas_llm == 2
        assert traza.tool_calls[0].crudo
    """

    nivel: str
    run_id: str
    llamadas_llm: int = 0
    llamadas_tools: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    costo_usd: float = 0.0
    ms_total: int = 0
    desde_cache: bool = False
    respuesta_final: str = ""
    ruta: str | None = None
    delegaciones: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tools_usadas: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    errores: list[str] = Field(default_factory=list)
    estado: str = "?"
    eventos: list[Any] = Field(default_factory=list)

    def imprimir(self) -> None:
        """Traza legible en una celda de notebook."""
        print(f"── {self.nivel.upper()} · run {self.run_id[:8]} ─────────────")
        for ev in self.eventos:
            _imprimir_evento(ev, sangria=0)
        print("──")
        costo = f"${self.costo_usd:.4f}" if self.costo_usd else "—"
        print(
            f"{self.llamadas_llm} llamadas al modelo · "
            f"{self.llamadas_tools} tools · "
            f"{self.tokens_in}+{self.tokens_out} tokens · "
            f"{self.ms_total} ms · {costo}"
            + ("  ⚡ caché" if self.desde_cache else "")
        )


def _imprimir_evento(ev: Any, sangria: int) -> None:
    pad = "  " * sangria
    t = ev.tipo
    if t == "llm_request":
        print(f"{pad}→ llamada {ev.n_llamada} al modelo · tools: {ev.tools_declaradas or '—'}")
    elif t == "llm_response":
        marca = "con tool_calls" if ev.hay_tool_calls else "texto"
        print(f"{pad}← respuesta {ev.n_llamada} ({marca}, {ev.ms} ms)")
    elif t == "pensamiento":
        print(f"{pad}  💭 {ev.texto or '(el modelo no razonó en voz alta)'}")
    elif t == "ruta":
        print(f"{pad}  ruta → {ev.dominio}: {ev.motivo}")
    elif t == "tool_call":
        print(f"{pad}  🔧 {ev.nombre}({ev.argumentos})")
        for linea in ev.crudo.splitlines():
            print(f"{pad}     {linea}")
    elif t == "tool_result":
        detalle = f"error: {ev.error}" if ev.error else f"{ev.filas if ev.filas is not None else '—'} filas"
        print(f"{pad}  ✓ {ev.nombre} → {detalle} ({ev.ms} ms)")
    elif t == "delegacion":
        print(f"{pad}  ⇒ delega en {ev.agente}: {ev.instruccion}")
    elif t == "sub_evento":
        _imprimir_evento(ev.evento, sangria + 2)
    elif t == "aviso":
        print(f"{pad}  {'⚠' if ev.gravedad == 'alerta' else 'ℹ'} {ev.mensaje}")
    elif t == "error":
        print(f"{pad}  ✕ {ev.mensaje}" + (f" (reintento {ev.reintento})" if ev.reintento else ""))
    elif t == "respuesta_final":
        print(f"{pad}  «{ev.texto}»")


def resumir(eventos: list[Any]) -> Traza:
    """Colapsa una lista de eventos en una `Traza`.

    Los `sub_evento` de N5 cuentan hacia los totales del padre: el invariante 9
    dice que las métricas del run padre son la suma de las suyas más las de todos
    sus sub-runs, y para el participante «cuántas llamadas costó N5» significa el
    total, no solo las del supervisor.
    """
    if not eventos:
        return Traza(nivel="?", run_id="?")

    t = Traza(nivel=eventos[0].nivel, run_id=eventos[0].run_id, eventos=eventos)

    def recorrer(lista: list[Any], anidado: bool) -> None:
        for ev in lista:
            tipo = ev.tipo
            if tipo == "llm_request":
                t.llamadas_llm += 1
            elif tipo == "llm_response":
                t.tokens_in += ev.tokens_in
                t.tokens_out += ev.tokens_out
            elif tipo == "tool_call":
                t.llamadas_tools += 1
                t.tool_calls.append(ev)
                t.tools_usadas.append(ev.nombre)
            elif tipo == "ruta":
                t.ruta = ev.dominio
            elif tipo == "delegacion":
                t.delegaciones.append(ev.agente)
            elif tipo == "aviso":
                t.avisos.append(ev.mensaje)
            elif tipo == "error":
                t.errores.append(ev.mensaje)
            elif tipo == "sub_evento":
                recorrer([ev.evento], anidado=True)
            elif tipo == "respuesta_final" and not anidado:
                t.respuesta_final = ev.texto
            elif tipo == "metricas" and not anidado:
                # Las métricas del run padre ya vienen sumadas por el nivel.
                t.costo_usd = ev.costo_usd
                t.ms_total = ev.ms_total
                t.desde_cache = ev.desde_cache
            elif tipo == "fin" and not anidado:
                t.estado = ev.estado

    recorrer(eventos, anidado=False)
    return t
