# 01 · Visión y alcance — Clase 2

## El problema pedagógico

La Sesión 1 dejó al grupo con un vocabulario claro sobre **qué** es un agente de IA y
cuáles son sus niveles de agencia — pero lo vieron **solo en teoría**. No han
construido uno, no han leído el código de uno, no han conversado con uno desde la
terminal. El riesgo es que salgan del programa sabiendo *describir* un agente sin
saber *cómo se construye* — que es justo lo que necesitarán para los proyectos reales
que defienden en las sesiones de acompañamiento (S5–S7).

La Sesión 2 existe para cerrar esa brecha. El arco narrativo es explícito:

> **S1: «¿Qué es un agente de IA?». S2: «¿Cómo se construye un agente de IA?».**

Y lo cierra con **memoria**: el agente no solo actúa, también recuerda. Ese es el
tema que el plan original ponía en S2 y que acá se incorpora de forma natural, porque
un agente sin memoria a penas es un agente.

## Objetivo medible

Al terminar la sesión, cada participante DEBE poder:

- **Señalar en el código modular** dónde está cada componente del agente (cerebro,
  herramientas, memoria, loop) y explicar qué hace.
- **Identificar el loop ReAct** (Thought → Action → Observation) en el código
  transparente y en el equivalente visual de n8n.
- **Reconocer la memoria** en acción: el agente usa lo dicho en turnos previos para
  responder, sin que se le repita.
- **Explicar qué abstrae un framework** (`create_react_agent` de LangGraph) frente al
  loop escrito a mano, comparando los dos `agente.py` lado a lado, y argumentar cuándo
  conviene uno u otro.
- **Relacionar el caso demostrado** (operaciones de planta sobre `bios_ops.db`) con su
  propio reto de Champion (Mantenimiento, Compras, Logística, Producción/TD).

## Audiencia y sus consecuencias de diseño

15 personas, dos poblaciones. Esta sesión es **demo guiada**, no taller de escritura:
el facilitador construye y explica en pantalla; los participantes consumen el código,
pueden montarlo a la par si quieren (tienen acceso al repo) y cuentan con un `.md` de
instrucciones para replicarlo después. La razón de ese formato son las restricciones
reales del grupo:

| Restricción observada | Consecuencia de diseño |
|---|---|
| No todos pueden correr nuestro repo por seguridad de Bios | Sesión demo: ellos **ven** el agente construirse, no se exige que lo corran en clase |
| Los no-software no saben n8n | Parte 2 muestra **el mismo caso** en n8n, sin pedirles que lo armen solos |
| Tiempo limitado (90 min con gap) | Concepto por archivo, no de cero con verbose; cada pieza se lee en 5-6 líneas clave |
| Solo 3 sesiones formativas antes del acompañamiento | El entregable intelectual es «cómo se construye», no un agente terminado propio — eso llega en S3/S4 y el acompañamiento |

### El rol de las dos poblaciones

- **Núcleo (~4 personas, dev avanzado):** pueden montar el repo a la par, ejecutarlo y
  tocar. Su rol: desbloquear a su mesa si alguien quiere intentar correrlo. En el
  cierre pueden extender (cambiar el prompt, agregar una tool).
- **Champions no-software (~11):** siguen la demo, leen el `.md` después y ven la
  parte de n8n como su vía de entrada. No se les pide escribir Python.

## La sesión en dos partes

La clase se divide en **dos demos consecutivas del mismo caso**, para que los conceptos
se refuercen entre medios y no se sientan como dos clases separadas:

| Parte | Medio | Audiencia principal | Qué se ve |
|---|---|---|---|
| **1a** | Python con loop ReAct **escrito a mano** sobre `bios_ops.db`, conversación por terminal | Técnicos (y todos miran) | El agente construido pieza por pieza, **código transparente**, con el ciclo Thought → Action → Observation a mano y memoria. |
| **1b** | Python con **LangGraph** (`create_react_agent`), el **mismo agente** en 3 líneas, sobre el mismo dataset | Técnicos (y todos miran) | El mismo agente con framework. Comparación directa: `cliente` / `tools` / `memoria` son idénticos; solo cambia `agente.py`. **El framework no es magia: es lo que escribimos a mano, empaquetado.** |
| **2** | El mismo caso en n8n cloud de Bios | No-software (y todos miran) | El **mismo agente** como nodos: *AI Agent* = cerebro, *Tools* = brazos, *Window Buffer Memory* = memoria. Conceptos idénticos, forma visual. |

**El hilo que las une:** no son ejemplos paralelos —es el **mismo agente**, con el
mismo dataset y las mismas preguntas, en tres implementaciones (transparente,
framework, visual). La comparación es la lección: el concepto vive independiente del
medio.

## El agente de código — estrutura modular: dos carpetas

Cada archivo es un concepto. No se elige un framework como protagonista: en la Parte 1a
el loop ReAct se escribe a mano para que **se vea**; en la Parte 1b el mismo agente se
construye con framework para mostrar **qué abstrae** y qué no.

```
clase2-como-construir-agente/
├── agente-transparente/          ← Parte 1a · loop ReAct a mano (concepto visible)
│   ├── cliente.py                 ← el cerebro: AzureChatOpenAI (~10 líneas)
│   ├── tools.py                   ← los brazos: 4-5 funciones + schemas JSON (~30 líneas)
│   ├── memoria.py                 ← la memoria: buffer de conversación (~15 líneas)
│   ├── loop.py                    ← el ciclo ReAct, escrito a mano (~35 líneas)
│   ├── agente.py                   ← ensambla todo en una clase AgenteReAct (~8 líneas)
│   └── chat.py                    ← interfaz de terminal, conversación con el usuario (~15 líneas)
└── agente-framework/             ← Parte 1b · mismo agente con LangGraph
    ├── cliente.py                 ← IDÉNTICO a agente-transparente/cliente.py
    ├── tools.py                   ← IDÉNTICAS a agente-transparente/tools.py
    ├── memoria.py                 ← IDÉNTICA a agente-transparente/memoria.py
    └── agente.py                   ← las ~3 líneas: create_react_agent + conversación
```

**El punto clave:** `cliente`, `tools` y `memoria` se **reutilizan textualmente** entre
las dos carpetas. Lo único que cambia entre `agente-transparente` y `agente-framework`
es `agente.py` — el loop a mano (Parte 1a) vs `create_react_agent(...)` (Parte 1b).
Al proyectar los dos `agente.py` lado a lado, la lección es inevitable: **el framework
no es magia, es lo que escribimos a mano, empaquetado**.

**Totales: ~115 líneas en la carpeta transparente (6 archivos) + ~3 líneas nuevas en
`agente-framework/agente.py`** (el resto se reutiliza). El presupuesto para explicar la
Parte 1a es ~7-8 min por archivo; la Parte 1b es un bloque corto (~5-7 min) porque solo
se lee el `agente.py` nuevo y se ejecuta la misma conversación.

### Dinámica del cierre de código (Parte 1b, ~5-7 min)

1. Abrir `agente-framework/agente.py` proyectado al lado del `agente.py` +
   `loop.py` de la carpeta transparente.
2. Señalar: *«cliente, tools y memoria son los mismos archivos. Lo que cambió es esto»*.
3. Ejecutar la **misma pregunta** de Bios por terminal y comparar trazas.
4. Cierre verbal: *«El framework no es magia: es lo que escribimos a mano,
   empaquetado. En sus proyectos, eligen según cuánto control quieran sobre el loop»*.

## Presupuesto de tiempo (90 min con gap)

Diseñado para 90 min reservados, ~80 min de ejecución real para dejar gap.

| Bloque | Min | Qué pasa |
|---|---|---|
| Recap + mapa "de menos a más" | 0–8 | Dudas de S1. Marcar "hoy: cómo se construye". |
| **Parte 1a — código transparente: el agente pieza por pieza a mano** | 8–46 | ~7-8 min por archivo: `cliente` → `tools` → `memoria` → `loop` → `agente` → `chat`. Cada pieza se proyecta, se lee la idea, se ejecuta. Al final: conversación por terminal con una pregunta de Bios. |
| **Parte 1b — mismo agente con framework** | 46–53 | Proyectar `agente-framework/agente.py` junto a `agente-transparente/agente.py` + `loop.py`. Cliente/tools/memoria idénticos — solo cambia `agente.py`. Ejecutar la misma pregunta, comparar trazas. Lección: el framework no es magia. |
| **Parte 2 — n8n: el mismo agente como nodos** | 53–78 | Abrir n8n cloud de Bios. Mostrar el workflow plantilla: nodo *AI Agent* + tools + *Window Buffer Memory*. Ejecutar la misma pregunta de Bios. Comparar con la Parte 1: mismo concepto, forma visual. |
| Puesta en común + puente a S3 | 78–90 | Conceptos recapitulados (cerebro, tools, memoria, loop, framework). "La próxima, su agente lee documentos." |

### Condiciones duras

1. **El repo de la clase 2 está en estado funcional antes de la sesión.** La demo va
   de leer y ejecutar archivos que ya corren —no de escribirlos en vivo— para no
   depender de la velocidad de tipeo del facilitador ni de la red. Si algo falla en
   vivo, el archivo de rescate es "último estado funcional" y se ejecuta.
2. **La plantilla n8n está subida a la instancia n8n de Bios antes de la sesión.** No
   se arma en vivo: se abre y se explain. Sin esto, la Parte 2 no es viable.
3. **Credenciales Azure OpenAI ya configuradas** en el `.env` del repo y en el nodo de
   credencial de n8n. No se configuran en clase.
4. **El `.md` de "cómo montarlo tú mismo"** queda en el repo, con screenshots de
   n8n y los comandos de Python paso a paso, para quienes quieran reproducirlo después.

## Entregable

- **En el repo:** `clase2-como-construir-agente/agente/` con los 6 archivos modulares,
  `bios_ops.db` reutilizada, `.env.example` con vars de Azure, y un `COMO-MONTARLO.md`.
- **En la instancia n8n de Bios:** workflow plantilla "Agente Bios ReAct" con un *AI
  Agent*, dos tools de ejemplo, y memoria configurada.
- **Intelectual:** cada participante sale con la capacidad de señalar dónde está cada
  componente de un agente en código y en n8n, y explicar el loop de ReAct.

## Fuera de alcance (Sesión 2)

Se declara explícitamente para evitar que la sesión crezca:

- **RAG sobre documentos** → S3. Aquí la memoria es conversacional (corto plazo),
  no recuperación semántica de documentos.
- **Multiagente (supervisor, swarm)** → S4. La Sesión 2 construye un solo agente.
- **Que cada Champion construya su propio agente en clase** → no es viable por
  restricciones de setup y tiempo. El entregable es verlo construirse y tener el repo
  + `.md` para replicarlo después.
- **Harness (tests, evals, CI/CD, costos)** → acompañamiento S5–S7, puntual.
- **Datos reales de Grupo Bios** → mismo candado de S1: todo lo que una tool devuelve
  se envía al proveedor del modelo. Aquí se mantiene `bios_ops.db` sintética.
- **Despliegue a producción / observabilidad** → S5–S7.

## Bloqueantes a resolver con Bios antes de la fecha

1. **Acceso al repo de la clase 2 para todos los técnicos** (gestionar con José /
   líder del equipo). Alternativa: entrega vía canal interno de Bios.
2. **Acceso a la instancia n8n de Bios** para subir la plantilla + credenciales
   Azure OpenAI ya configuradas (pedir a TI de Bios).
3. **Confirmar Python ≥3.10** en las máquinas de los técnicos que quieran correr la
   Parte 1 a la par.