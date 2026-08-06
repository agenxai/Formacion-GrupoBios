# 06 · Plantilla n8n — Clase 2

## Qué es

Un workflow **exportado como JSON** que se importa en la instancia n8n cloud de Bios
antes de la clase. En la Parte 2 (min 53–78 del guion) el facilitador lo abre, lo
recorre nodo por nodo y lo ejecuta. **No se construye en vivo** (ADR-006) — el
tiempo se gasta en explicar, no en arrastrar nodos.

El workflow materializa el mismo agente ReAct con memoria de las Partes 1a/1b, en
forma visual. Misma base, misma conversación insignia, mismo proveedor.

## Archivo

```
clase2-como-construir-agente/
└── n8n/
    └── plantilla-agente-bios-react.json   ← export del workflow, listo para importar
```

El JSON es el export estándar de n8n (`File > Download` en el canvas). Contiene los
nodos, sus configuraciones, las conexiones y las expresiones —**no** las
credenciales (n8n las exporta como referencias, no como secrets). Importarlo en otra
instancia pide reconfigurar la credencial.

## Estructura del workflow

```
┌───────────────────┐
│  Chat Trigger      │   ←  entrada de mensaje del usuario
│  (manual / webhook)│
└─────────┬─────────┘
          │
          ▼
┌────────────────────────────────────────────┐
│  AI Agent                                  │
│  ├─ Memory: Window Buffer Memory           │   ←  ventana de turnos, por sessionId
│  ├─ Tools:                                 │
│  │    • consultar_inventario              │
│  │    • consultar_demanda                 │
│  │    • estado_pedido                     │
│  │    • historial_fallas                  │
│  └─ LLM: Azure OpenAI Model              │   ←  credencial ya registrada
└─────────┬──────────────────────────────────┘
          │
          ▼
┌───────────────────┐
│  Set / Respond     │   ←  respuesta visible en el canvas
└───────────────────┘
```

## Configuración de cada nodo

### AI Agent

| Campo | Valor | Notas |
|---|---|---|
| **Agent type** | `ReAct` o `Conversational Agent` | ReAct es el patrón de la clase; Conversational si solo está disponible. |
| **System Message** | El system prompt del agente (idéntico al de la Parte 1a). | Es lo que en Python era `prompt` en `agente.py`. La equivalencia se explicita al proyectar. |
| **Memory** | `Window Buffer Memory`, sessionId=`bios-clase2`, window size=10 turnos | Equivalente a `memoria.py`. |
| **Tools** | Los cuatro nodos Tool conectados. | Equivalente al `TOOLS` de `tools.py`. |

### Azure OpenAI Model (nodo de credencial)

| Campo | Valor |
|---|---|
| **Credential** | `Azure OpenAI API` (registrada en n8n por TI de Bios, no se exporta) |
| **Resource name** | El del deployment de Bios |
| **Deployment name** | `gpt-4o-mini` (verificar con TI antes de la clase) |
| **API version** | `2024-10-21` |

> **No se configura en clase.** La credencial ya está registrada. El facilitador
> solo la señala y dice *"esto es el .env de Python"*.

### Cada nodo Tool

Para cada tool se crea un nodo de tipo **Tool** dentro del AI Agent. La configuración
es la misma por las cuatro:

| Campo | Valor | Notas |
|---|---|---|
| **Name** | `consultar_inventario` / `consultar_demanda` / `estado_pedido` / `historial_fallas` | Idénticos a los nombres de Python. |
| **Description** | La docstring de la función Python correspondiente. | **Es el prompt que ve el modelo** — lección pedagógica. |
| **Parameters schema** | El esquema JSON de la spec 04. | Idéntico a la Parte 1a. |
| **Action** | HTTP Request a un endpoint que ejecuta la consulta SQL sobre `bios_ops.db`, o nodo Code con el SQL inline. | El endpoint puede ser un servicio liviano que expone las 4 tools (recomendado), o queries directas con el nodo SQLite de n8n (más simple, menos portable). |

#### Decisión: cómo se conectan las tools a los datos

Dos opciones, en orden de preferencia:

1. **(Recomendado) Servicio liviano de tools.** Un pequeño endpoint HTTP en Python
   que expone las cuatro tools y consulta `bios_ops.db` local. Las herramientas de
   n8n apuntan ahí. Ventajas: las tools son las **mismas funciones** que corren en
   la Parte 1a — sin duplicar lógica. Si el núcleo técnico de Bios lo puede alojar,
   es el camino.
2. **SQLite directo en n8n.** Cada tool es un nodo Code que ejecuta SQL contra una
   copia de `bios_ops.db` cargada en n8n. Simple, pero **duplica la lógica** de
   `tools.py` (whitelisting, manejo de "no encontré", truncado).

La decisión se toma al construir la plantilla (fase de implementación). Si la
opción 1 es viable, se reduce el riesgo de inconsistencia entre las Partes 1 y 2.

### Window Buffer Memory

| Campo | Valor |
|---|---|
| **Session ID** | `bios-clase2` (fijo para la demo) |
| **Context window length** | 10 turnos |

Equivalente directo de `memoria.py`. No requiere persistencia entre sesiones de
n8n — la memoria vive mientras el workflow está activo.

## Importación (antes de la clase)

**Bloqueante.** Se resuelve con TI de Bios 24-48 h antes (spec 09 checklist):

1. Verificar acceso a la instancia n8n de Bios con un usuario que pueda importar
   workflows.
2. `Import from File` → seleccionar `n8n/plantilla-agente-bios-react.json`.
3. Abrir el nodo **Azure OpenAI Model** y seleccionar la credencial ya registrada.
   Si no existe, pedirla a TI (no se crea en clase).
4. Guardar el workflow.
5. Ejecutar el turno 1 de la conversación insignia y verificar la respuesta.

Si la importación falla o la credencial no está, **la Parte 2 no es viable** —se
plantea un plan C (transcripción del flujo + capturas), pero no se improvisa en
clase.

## Equivalencias pedagógicas (la tabla que se proyecta)

La lección de la Parte 2 es la equivalencia con las Partes 1a/1b. Esta tabla está
en `COMO-MONTARLO.md` y se proyecta al cierre de la Parte 2:

| Concepto | Python (Parte 1a/1b) | n8n (Parte 2) |
|---|---|---|
| Cerebro (LLM) | `AzureChatOpenAI` en `cliente.py` | Nodo *Azure OpenAI Model* |
| Herramientas | funciones en `tools.py` + `TOOLS` | Nodos *Tool* conectados al *AI Agent* |
| Prompt de cada tool | la docstring de la función | campo *Description* del nodo Tool |
| Schema de parámetros | JSON en `SCHEMAS` | campos *Parameters* del nodo Tool |
| Memoria | `Memoria` (lista de mensajes) | Nodo *Window Buffer Memory* |
| Loop ReAct | `loop.py` (Parte 1a) / `create_react_agent` (Parte 1b) | El nodo *AI Agent* lo hace internamente |
| Interfaz | `chat.py` (bucle de `input()`) | El *Chat Trigger* es la interfaz |

Al cierre: *"El agente es el mismo. Lo que cambia es el medio. Si lo entienden en
uno, lo entienden en el otro."*

## Fuera de alcance

- **Persistencia de la memoria** entre sesiones de n8n → acompañamiento.
- **Autenticación de usuarios en el Chat Trigger** → acompañamiento.
- **Webhooks salientes** (notificar a otro sistema) → fuera del scope de la clase.
- **Encadenamiento con otros workflows de Bios** → acompañamiento, en función del
  proyecto de cada Champion.