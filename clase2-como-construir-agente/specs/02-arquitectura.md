# 02 · Arquitectura — Clase 2

## Vista de componentes

La clase 2 es **una demo guiada**, no una aplicación. No hay servidor, no hay frontend,
no hay streaming. Tres artefactos, cada uno con un único propósito:

```
clase2-como-construir-agente/
│
├── agente-transparente/          ← Parte 1a · el agente pieza por pieza a mano
│   ├── cliente.py                  el cerebro (AzureChatOpenAI)
│   ├── tools.py                    los brazos (funciones + schemas sobre bios_ops.db)
│   ├── memoria.py                  la memoria (buffer de conversación)
│   ├── loop.py                     el ciclo ReAct, escrito a mano
│   ├── agente.py                   ensambla todo en una clase AgenteReAct
│   ├── chat.py                     interfaz de terminal: conversación con el usuario
│   └── bios_ops.db                 ← copia de la base de la clase 1 (sintética)
│
├── agente-framework/             ← Parte 1b · mismo agente con LangGraph
│   ├── cliente.py                  IDÉNTICO a agente-transparente/cliente.py
│   ├── tools.py                    IDÉNTICAS a agente-transparente/tools.py
│   ├── memoria.py                  IDÉNTICA a agente-transparente/memoria.py
│   ├── agente.py                   ~3 líneas: create_react_agent + conversación
│   └── chat.py                     interfaz de terminal (idéntica)
│
├── n8n/
│   └── plantilla-agente-bios-react.json   ← Parte 2 · workflow exportado a importar
│
├── .env.example                   ← plantilla de configuración (Azure OpenAI)
├── requirements.txt               ← versiones fijadas
├── COMO-MONTARLO.md                ← guía paso a paso para reproducirlo solo
└── specs/                         ← este directorio
```

**El punto clave de la arquitectura:** las carpetas `agente-transparente/` y
`agente-framework/` **comparten tres archivos idénticos** (`cliente.py`, `tools.py`,
`memoria.py`). Solo difieren en `agente.py` (el loop a mano vs `create_react_agent`).
Al proyectar los dos `agente.py` lado a lado, la lección es inevitable: el framework
empaqueta el loop que escribimos a mano, nada más.

**No hay Docker.** La clase 1 lo necesitaba porque corría una app web + Jupyter para
15 personas en paralelo. La clase 2 es un script de terminal que corre el facilitador
en su máquina y proyecta. Los participantes que quieran montarlo a la par usan un
`venv` con `requirements.txt`. Es deliberadamente más simple.

## Flujo de ejecución

```
                 ┌──────────────────────────────────────────────────┐
                 │  El facilitador corre en su máquina y proyecta    │
                 │                                                   │
   Parte 1a ──▶  │  python -m agente-transparente.chat                │
                 │     ↳ loop ReAct a mano + memoria                │
                 │     ↳ conversación por terminal con bios_ops.db   │
                 │                                                   │
   Parte 1b ──▶  │  python -m agente-framework.chat                  │
                 │     ↳ create_react_agent + memoria                │
                 │     ↳ la misma conversación, misma base           │
                 └────────────────────┬─────────────────────────────┘
                                      │
                                      │  (cambio de pantalla)
                                      ▼
                 ┌──────────────────────────────────────────────────┐
                 │  n8n cloud de Bios (vía navegador)               │
   Parte 2 ──▶   │  workflow "Agente Bios ReAct" ya importado        │
                 │     ↳ nodo AI Agent + 2-3 Tools + Window Buffer  │
                 │     ↳ la misma pregunta de Bios, ejecutada ahí    │
                 └──────────────────────────────────────────────────┘
                                      │
                                      ▼
                            ┌─────────────────┐
                            │  Azure OpenAI   │  ← proveedor del LLM (endpoint de Bios)
                            └─────────────────┘
```

Tres implementaciones del mismo agente, mismo dataset, mismas preguntas. El concepto
vive independiente del medio.

## El agente transparente — contrato interno de archivos

Cada archivo expone una interfaz mínima y legible. La firma de importación es lo que
se proyecta al explicar:

```python
# agente-transparente/cliente.py
def cliente() -> AzureChatOpenAI: ...          # el cerebro

# agente-transparente/tools.py
TOOLS: list                       # los brazos (funciones + schemas)
def consultar_inventario(planta, materia_prima=None) -> dict: ...
def consultar_demanda(planta, materia_prima=None, dias=7) -> dict: ...
def estado_pedido(pedido_id) -> dict: ...
def historial_fallas(planta, dias=30) -> dict: ...

# agente-transparente/memoria.py
class Memoria:
    def agregar(self, rol: str, contenido: str) -> None: ...
    def mensajes(self) -> list[dict]: ...     # formato OpenAI

# agente-transparente/loop.py
def react(cliente, tools, memoria, pregunta) -> str: ...
    # Thought → Action → Observation, iterativo, a mano

# agente-transparente/agente.py
class AgenteReAct:
    def __init__(self, cliente, tools, memoria): ...
    def preguntar(self, pregunta: str) -> str: ...

# agente-transparente/chat.py
def main() -> None: ...   # bucle de conversación por terminal, lee stdin
```

El `agente-framework/` reexporta `cliente`, `tools` y `memoria` de la carpeta
transparente (o las copia idénticas — preferimos copia para que el diff sea trivial)
y solo reescribe `agente.py`:

```python
# agente-framework/agente.py — la pieza que cambia
from langgraph.prebuilt import create_react_agent

def agente(cliente, tools, prompt):
    return create_react_agent(cliente, tools, prompt=prompt)  # eso es todo
```

## Decisiones (ADR)

### ADR-001 · Azure OpenAI como proveedor, no OpenAI directo
**Contexto.** Bios usa Azure OpenAI como puerta corporativa a los modelos. Soapenai
directo no está permitido por su TI.
**Decisión.** `cliente.py` instancia `AzureChatOpenAI` con `azure_endpoint`,
`api_key`, `api_version` y `azure_deployment` desde `.env`.
**Razón.** Lo que se ve en clase es lo que van a usar en sus proyectos. Usar OpenAI
directo en clase yAzure en producción rompería la transferencia.
**Consecuencia.** Hay que confirmar con TI de Bios las credenciales y el deployment
**antes** de la fecha. Bloqueante (spec 01).

### ADR-002 · Loop ReAct a mano como protagonista, framework como comparación
**Contexto.** Podríamos enseñar directamente con `langgraph.prebuilt.create_react_agent`
y saltarnos el loop transparente.
**Decisión.** La Parte 1a construye el loop Thought → Action → Observation a mano
(~35 líneas); la Parte 1b muestra el mismo agente con `create_react_agent` en 3 líneas.
**Razón.** El tema de la clase es "cómo se construye un agente". Si el loop es una
línea de framework, no se ve qué se construye — se ve cómo se invoca. El loop a mano
hace visible la decisión, la tool call, la observación. La comparación final enseña
qué abstrae el framework, que es la lección que se llevan a sus proyectos reales.
**Consecuencia.** Duplicación aparente entre carpetas. Es intencional y pedagógica:
`cliente`/`tools`/`memoria` son idénticos para que el diff se reduzca a `agente.py`.

### ADR-003 · bios_ops.db reutilizada, no regenerada
**Contexto.** La clase 1 ya generó `bios_ops.db` (11 tablas, 12.497 filas sintéticas)
con semilla fija. La clase 2 no necesita datos nuevos.
**Decisión.** La base se copia desde `clase1-lab-agentes/bios_ops.db` (o se regenera
con `backend.db.seed`Si el original no está). No hay un generador nuevo.
**Razón.** Los 4 dominios (Mantenimiento, Compras, Logística, Producción/TD) ya están
modelados con las tools que la clase 1 ya escribió. Regenerar rompería la continuidad
y desperdiciaría trabajo probado.
**Consecuencia.** Las tools de la clase 2 son una **versión simplificada y
autocontenida** de `clase1-lab-agentes/backend/tools/operaciones.py`: mismas
funciones, sin depender del paquete `backend/` de la clase 1. Se(destẽja) la
conexión ahişiday para que `tools.py` sea legible de arriba a abajo en una pantalla.

### ADR-004 · Memoria conversacional simple: una lista de mensajes
**Contexto.** Podríamos usar `langchain.memory.ConversationBufferMemory` o un store
persistente (SQLite, Redis). Pero la clase 1 ya mostró memoria como concepto; acá
enseñamos **cómo se construye**.
**Decisión.** `memoria.py` implementa un buffer como una lista de dicts formato
OpenAI (`{"role": ..., "content": ...}`). Sin persistencia entre ejecuciones.
**Razón.** Que la memoria sea una lista de Python hace visible que la "memoria" no es
magia: es acumular los mensajes previos y pasarlos de nuevo en la próxima llamada.
Cuando en la Parte 1b vean `Window Buffer Memory` en n8n, el concepto ya está claro.
**Consecuencia.** La memoria se pierde al cerrar el script. La persistencia es tema
de producción (aparece en acompañamiento S5–S7 cuando un proyecto lo necesite). Se
declara explícitamente fuera de alcance en la spec 01.

### ADR-005 · Sin Docker: Python local con venv y requirements.txt
**Contexto.** La clase 1 requería Docker (app web + Jupyter para 15 en paralelo). La
clase 2 es una demo que corre el facilitador y proyecta; los participantes que montan
a la par usan su Python.
**Decisión.** No se incluye Dockerfile ni docker-compose. `requirements.txt` con
versiones fijadas y un `venv` estándar. `COMO-MONTARLO.md` guía el setup paso a paso.
**Razón.** Menos dependencias = menos superficie de fallo en clase. Si un técnico
no tiene venv configurado, sigue la demo proyectada y la reproduce después con el `.md`.
**Consecuencia.** El facilitador debe tener su venv funcionando antes de la clase
(checklist spec 09). No se instala nada en vivo.

### ADR-006 · Plantilla n8n pre-importada, no armando en vivo
**Contexto.** Mostrar n8n armar un workflow desde cero en vivo toma 20+ min y falla
si la red oscila.
**Decisión.** El workflow `n8n/plantilla-agente-bios-react.json` se importa a la
instancia n8n de Bios **antes** de la clase. En la Parte 2 se abre, se explica
nodo por nodo y se ejecuta.
**Razón.** El tiempo de la Parte 2 (25 min) se gasta en **entender** el workflow, no
en armarlo. La lección es "así se ve el mismo agente en n8n", no "así se arrastra un
nodo".
**Consecuencia.** Bloqueante: el acceso a n8n de Bios y la importación se resuelven
con TI antes de la fecha (spec 01). En clase solo se abre y se ejecuta.

## Dependencias

`requirements.txt` DEBE fijar versiones exactas (`==`).

| Paquete | Para qué |
|---|---|
| `langchain-openai` | `AzureChatOpenAI` (cliente del modelo en Azure) |
| `langchain-core` | Definición de tools y mensajes |
| `langgraph` | Parte 1b: `create_react_agent` |
| `openai` | SDK subyacente (lo usa langchain-openai) |
| `python-dotenv` | Carga del `.env` |

No se incluyen: bases vectoriales (S3), frameworks de test (acompañamiento),
observabilidad (acompañamiento),niveles N1-N2-N5 (S1). El alcance es un solo agente
ReAct con memoria, en dos implementaciones + n8n.

## Variables de entorno

`.env` (jamás en el repo; `.env.example` es la plantilla):

| Variable | Default | Efecto |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | — | Endpoint del recurso de Azure OpenAI de Bios. Requerido. |
| `AZURE_OPENAI_API_KEY` | — | Key del recurso. Requerido. |
| `AZURE_OPENAI_DEPLOYMENT` | — | Nombre del deployment (ej. `gpt-4o-mini`). Requerido. |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | Versión de la API de Azure. |
| `BIOS_DB_PATH` | `agente-transparente/bios_ops.db` | Ruta a la base sintética. |

`cliente.py` DEBE cargarlas con `python-dotenv` y fallar con un mensaje legible si
falta alguna de las tres requeridas. No se descubre la falta de credenciales a mitad
de la demo.

## Diferencias结构与s clave con la clase 1

| | Clase 1 | Clase 2 |
|---|---|---|
| Mecánica | Taller con TODOs en notebook | Demo guiada por el facilitador |
| Stack | FastAPI + Jupyter + Docker | Python scripts + venv |
| Proveedor | OpenAI directo | **Azure OpenAI** |
| Modo replay | Sí (trazas pregrabadas) | No (si la API falla, plan C: transcripción de la conversación esperada) |
| Salida | Tablero web, notebook, comparación | Terminal + n8n |
| Datos | Generados por `seed.py` | Reutilizados de la clase 1 |
| Esperado de los participantes | Escribir 13 líneas | Ver construir, leer `.md` después |