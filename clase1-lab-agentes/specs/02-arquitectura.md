# 02 · Arquitectura

## Vista de componentes

```
┌─────────────────────────────────────────────────────────────────┐
│  docker compose up                                              │
│                                                                 │
│  ┌──────────────────────────┐    ┌──────────────────────────┐   │
│  │  servicio: tablero       │    │  servicio: notebook      │   │
│  │  FastAPI + Uvicorn :8000 │    │  JupyterLab :8888        │   │
│  │                          │    │                          │   │
│  │  / ............ frontend │    │  5-niveles-de-agencia    │   │
│  │  /api/* ....... JSON     │    │  .ipynb                  │   │
│  │  /api/stream .. SSE      │    │                          │   │
│  └────────────┬─────────────┘    └────────────┬─────────────┘   │
│               │                               │                 │
│               └───────────┬───────────────────┘                 │
│                           │  (mismo código, mismo volumen)      │
│              ┌────────────▼────────────┐                        │
│              │  backend/  (paquete)    │                        │
│              │  ├── niveles/ n1..n5    │                        │
│              │  ├── tools/             │                        │
│              │  ├── eventos.py         │                        │
│              │  └── llm.py             │                        │
│              └────────────┬────────────┘                        │
│                           │                                     │
│              ┌────────────▼────────────┐                        │
│              │  bios_ops.db  (SQLite)  │  ← generado en build    │
│              └─────────────────────────┘                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
                   ┌────────▼────────┐
                   │  API de OpenAI  │
                   └─────────────────┘
```

Un solo paquete `backend/` compartido por los dos servicios. El notebook importa
exactamente los mismos módulos que corren detrás del tablero: si el notebook
funciona, el tablero funciona. No hay dos implementaciones que se desincronicen.

## Estructura de directorios

```
clase1-lab-agentes/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example                 # plantilla; nunca la key real
├── .gitignore                   # DEBE incluir .env, *.db, __pycache__
├── README.md                    # setup y ejecución del repositorio
                                 # (el guion de clase está en specs/10)
├── specs/                       # este directorio
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI: rutas y SSE
│   ├── config.py                # variables de entorno, tipadas
│   ├── eventos.py               # contrato de eventos (spec 04)
│   ├── llm.py                   # cliente + backoff + caché + contador de gasto
│   ├── prompts.py               # system prompts, editables en runtime
│   ├── db/
│   │   ├── __init__.py
│   │   ├── esquema.sql
│   │   └── seed.py              # generador sintético, semilla fija
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── operaciones.py       # las 6 tools de dominio
│   │   └── sql_seguro.py        # ejecutar_sql de solo lectura
│   ├── niveles/
│   │   ├── __init__.py
│   │   ├── base.py              # protocolo común: ejecutar(pregunta) -> eventos
│   │   ├── n1_procesador.py
│   │   ├── n2_router.py
│   │   ├── n3_tool_caller.py
│   │   ├── n4_react.py
│   │   └── n5_supervisor.py
│   └── replay/
│       └── trazas.json          # trazas pregrabadas (plan B)
├── frontend/
│   ├── index.html
│   ├── app.js
│   ├── estilos.css
│   └── assets/
│       ├── grupo-bios.png       # copiado de "Clase 1 - Agentes/Grupo Bios.png"
│       ├── qypher.png
│       └── vendor/              # CSS y Alpine vendorizados — ver ADR-004
└── notebook/
    └── 2-los-cinco-niveles-taller.ipynb
```

## Contrato interno de los niveles

Los cinco módulos de nivel DEBEN exponer la misma firma. Es lo que permite que el
tablero los ejecute en paralelo y que la comparación sea honesta:

```python
# backend/niveles/base.py
from typing import AsyncIterator, Protocol
from backend.eventos import Evento

class Nivel(Protocol):
    ID: str            # "n1" .. "n5"
    NOMBRE: str        # "Procesador simple"
    ESTRELLAS: str     # "☆☆☆"
    PATRON: str        # "process_llm_output(llm_response)"

    async def ejecutar(self, pregunta: str, run_id: str) -> AsyncIterator[Evento]:
        """Emite eventos del contrato (spec 04) hasta 'fin'."""
```

Toda diferencia entre niveles vive **dentro** de `ejecutar`. Ninguna vive en el
frontend. Un nivel nuevo se agrega creando un módulo; el tablero lo descubre.

## Decisiones (ADR)

### ADR-001 · Un solo proveedor: OpenAI en los cinco niveles
**Contexto.** Se evaluó usar Claude Agent SDK en N5 para contrastar "framework vs.
harness".
**Decisión.** Todo OpenAI. N5 es un supervisor en LangGraph con sub-agentes expuestos
como tools.
**Razón.** Una sola API key, una sola dependencia, una sola cosa que puede fallar en
vivo. El contraste con harnesses pre-construidos se cubre conceptualmente en el
cierre y se materializa en la Sesión 4, que es donde corresponde.
**Consecuencia.** N5 requiere escribir el supervisor a mano. Es más código, pero
también más didáctico: se ve la arquitectura "supervisor con agentes como tools" del
ebook, sección 8.1.

### ADR-002 · El JSON crudo de la tool call es un requisito, no un detalle
**Decisión.** El evento `tool_call` DEBE incluir el campo `crudo`: el string JSON
exacto que devolvió el modelo, sin parsear ni embellecer.
**Razón.** La sección 7.2 del ebook muestra ese JSON. Verlo en pantalla, idéntico al
del documento, es el momento en que function calling deja de ser abstracto.
**Consecuencia.** No se puede usar únicamente la abstracción de alto nivel de
LangChain en N3; hay que acceder a la respuesta cruda del modelo.

### ADR-003 · N3 implementa el loop de function calling a mano
**Decisión.** N3 NO usa `create_react_agent` ni `AgentExecutor`. Escribe el ciclo
llamada → tool_call → ejecución → segunda llamada explícitamente (~30 líneas).
**Razón.** Si el framework aparece antes de entender qué abstrae, es magia. N4
introduce `create_react_agent` y el participante reconoce lo que le quitaron de
encima.
**Consecuencia.** Duplicación aparente entre N3 y N4. Es intencional y pedagógica.

### ADR-004 · Frontend sin build step y sin CDN
**Decisión.** HTML + CSS propio + Alpine.js, con las dependencias **vendorizadas** en
`frontend/assets/vendor/`. Sin Tailwind por CDN, sin fuentes de Google, sin Node en
la imagen.
**Razón.** El sin-build-step era el objetivo; el CDN es un riesgo aparte. Una red de
sala corporativa con proxy puede bloquear `cdn.tailwindcss.com` y dejar el tablero sin
estilos justo al proyectar. Vendorizar cuesta dos archivos y elimina el riesgo.
**Consecuencia.** El CSS se escribe a mano en lugar de con utilidades Tailwind. Para
un tablero de una vista es un costo menor.

### ADR-005 · Semilla fija en el generador de datos
**Decisión.** `seed.py` usa una semilla constante. La base es byte-idéntica en toda
máquina.
**Razón.** Tres beneficios: la demo del facilitador coincide con lo que ve el
participante; las respuestas se pueden cachear entre participantes (crítico con key
compartida, spec 09); y las trazas de replay siguen siendo válidas.
**Consecuencia.** Los datos no cambian entre corridas. Si se quiere variación,
`SEMILLA_DATOS` en el entorno, documentando que rompe el caché.

### ADR-006 · SSE, no WebSocket
**Decisión.** Streaming de eventos por Server-Sent Events.
**Razón.** Unidireccional servidor→cliente es exactamente lo que se necesita.
`EventSource` es nativo del navegador, reconecta solo, y se depura con `curl`. Un
WebSocket agregaría manejo de estado sin aportar nada.
**Consecuencia.** `EventSource` solo hace GET. Por eso el flujo es `POST /api/ejecutar`
(crea el run y devuelve `run_id`) y luego `GET /api/stream/{run_id}`.

## Dependencias

`requirements.txt` DEBE fijar versiones exactas (`==`). Una imagen que se construye
distinto la semana siguiente es un fallo en clase.

| Paquete | Para qué |
|---|---|
| `fastapi`, `uvicorn[standard]` | Servidor y SSE |
| `langchain-openai` | Cliente del modelo |
| `langchain-core` | Definición de tools, mensajes |
| `langgraph` | N4 y N5 |
| `openai` | Acceso a la respuesta cruda en N3 |
| `pydantic`, `pydantic-settings` | Contratos y configuración tipada |
| `jupyterlab` | Servicio del notebook |
| `python-dotenv` | Carga del `.env` |

NO se incluyen: bases vectoriales, frameworks de test, SDKs de observabilidad.
Pertenecen a sesiones posteriores.

## Variables de entorno

| Variable | Default | Efecto |
|---|---|---|
| `OPENAI_API_KEY` | — | Requerida en modo vivo. Sin ella el sistema arranca en `replay`. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo para todos los niveles. **Confirmar contra los modelos habilitados en la cuenta de Grupo Bios antes de la clase.** |
| `MODELO_SUPERVISOR` | = `OPENAI_MODEL` | Permite un modelo mayor solo en N5. |
| `MODO` | `vivo` | `vivo` \| `replay` \| `auto` (usa replay si falta la key o se agota el tope). |
| `TOPE_USD` | `10.00` | Gasto acumulado máximo. Al alcanzarlo se conmuta a `replay`. |
| `MAX_CONCURRENCIA` | `4` | Llamadas simultáneas a OpenAI. Protege la key compartida. |
| `CACHE_ACTIVO` | `true` | Caché de respuestas en disco. |
| `SEMILLA_DATOS` | `42` | Semilla del generador. |
| `PUERTO_TABLERO` | `8000` | |
| `PUERTO_NOTEBOOK` | `8888` | |

`config.py` DEBE validarlas con `pydantic-settings` y fallar al arrancar con un
mensaje legible si algo es inconsistente. No se descubren errores de configuración a
mitad de la demo.
