# 05 · Las tres implementaciones — Clase 2

La clase 1 tenía una sola pregunta y cinco niveles de agencia. La clase 2 tiene **una
sola arquitectura** (ReAct con memoria) y **tres implementaciones** que se proyectan
en secuencia para que el concepto quede independiente del medio.

```
                   una arquitectura: ReAct + memoria
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   Parte 1a                 Parte 1b                  Parte 2
   transparente             framework                n8n
   (loop a mano)             (create_react_agent)     (nodos visuales)
```

Esta spec define cada implementación y sus **criterios de aceptación**: lo que DEBE
pasar para que la implementación sirva en la clase. Si alguno no se cumple, el
facilitador no debe arrancar la parte correspondiente —se descubre antes, en el
checklist de la spec 09.

---

## Parte 1a — Implementación transparente (loop a mano)

**Carpeta:** `agente-transparente/`
**Audiencia:** técnicos (todos miran, algunos montan a la par)
**Tiempo:** ~38 min (min 8–46 del guion)

### Qué se construye en vivo (en realidad, se proyecta)

No se escribe código en vivo — el repo ya tiene los seis archivos funcionando. El
facilitador los abre uno por uno, lee las 5-6 líneas que encarnan el concepto y los
ejecuta. El orden de explicación es deliberado:

| Orden | Archivo | Min | Concepto que encarna |
|---|---|---|---|
| 1 | `cliente.py` | 8-13 | **El cerebro**: instancia `AzureChatOpenAI` con credenciales del `.env`. Lección: el proveedor es configurable y reemplazable. |
| 2 | `tools.py` | 13-21 | **Los brazos**: las 4 funciones + schemas. Lección: la docstring es el prompt; el modelo ve el schema, no el código. |
| 3 | `memoria.py` | 21-26 | **La memoria**: una lista de mensajes. Lección: la memoria no es magia, es acumular mensajes y pasarlos. |
| 4 | `loop.py` | 26-35 | **El ciclo ReAct** a mano: `chat.completions.create` → detectar `tool_calls` → `dispatch` → agregar resultado → repetir. Lección: **esto es lo que un agente hace**, sin abstracción. |
| 5 | `agente.py` | 35-40 | **Ensamblar**: una clase `AgenteReAct` que junta cliente + tools + memoria + loop. Lección: el agente es la composición de las piezas anteriores. |
| 6 | `chat.py` | 40-46 | **La interfaz**: bucle `while` que lee `input()` y llama `agente.preguntar()`. Lección: cualquier interfaz (terminal, web, API) es lo mismo al final. |

### Criterios de aceptación de la Parte 1a

La implementación透明ente sirve para la clase si, al ejecutar:

```bash
cd agente-transparente
python -m chat
```

se cumplen TODOS:

- [ ] **CA-1.1 Arranque limpio.** El script arranca sin errores. La primera línea
  impresa es el system prompt del agente y la lista de tools disponibles.
- [ ] **CA-1.2 Tool única (turno 1).** Ante la pregunta "¿cuánto maíz le queda a la
  planta de Itagüí?", el loop imprime `[Action] consultar_inventario(...)` y
  devuelve la cifra correcta (320 toneladas, bajo mínimo de 1.190).
- [ ] **CA-1.3 Encadenamiento (turno 2).** Ante "¿y me alcanza para la demanda
  proyectada de esta semana?", el loop imprime `[Action] consultar_demanda(...)`
  basándose en el contexto de memoria ("esa planta, maíz"), compara y concluye que
  **no alcanza, faltan ~1.331 toneladas**.
- [ ] **CA-1.4 Cambio de dominio (turno 3).** Ante "¿hay algún equipo de esa misma
  planta en riesgo de falla?", el loop escoge `historial_fallas(Itagüí)` —no
  `consultar_inventario`— y reporta el equipo `EQ-ITG-MOL-01` con tendencia de
  vibración.
- [ ] **CA-1.5 Memoria visible.** Entre dos turnos del mismo dominio, el agente no
  exige que se repita "Itagüí" ni "maíz" — los saca de memoria. La salida impresa del
  loop muestra los mensajes del historial en cada iteración.
- [ ] **CA-1.6 Traza legible.** La salida de terminal etiqueta cada paso como
  `[Thought]`, `[Action]`, `[Observation]`, `[Respuesta]`. Es lo que el ebook de la
  clase 1 describe; al verlo en pantalla alguien del grupo debe poder decir "eso es
  ReAct".
- [ ] **CA-1.7 Manejo de errores.** Si se para el servicio de Azure, el script no
  muere con un stack trace: imprime un mensaje legible y continúa. El bloque
  `try/except` alrededor de la llamada al LLM está visible al proyectar `loop.py`.

Si todos pasan, la Parte 1a está lista para proyectarse. Si CA-1.1 falla, las demš
tampoco van a pasar —revisar `.env` y conectividad con Azure antes de la clase.

---

## Parte 1b — Implementación con framework (LangGraph)

**Carpeta:** `agente-framework/`
**Audiencia:** técnicos
**Tiempo:** ~7 min (min 46–53 del guion)

### Qué se proyecta

Solo `agente.py`. `cliente.py`, `tools.py`, `memoria.py` son **los mismos archivos**
de la carpeta transparente (se duplican literalmente para que el diff sea trivial —
ADR-002). La pieza que cambia es:

```python
# agente-framework/agente.py
from langgraph.prebuilt import create_react_agent

def construir_agente(cliente, tools, system_prompt):
    return create_react_agent(cliente, tools, prompt=system_prompt)

def conversar(agente):
    while True:
        pregunta = input("tú › ")
        if pregunta.lower() in {"salir", "exit"}:
            break
        resultado = agente.invoke({"messages": [{"role": "user", "content": pregunta}]})
        print(f"agente › {resultado['messages'][-1].content}")
```

> **El teach moment:** se proyecta `agente-framework/agente.py` **al lado** de
> `agente-transparente/loop.py` + `agente-transparente/agente.py`. El facilitador
> señala: *"cliente, tools y memoria son los mismos archivos. Lo que cambió es
> esto"*. La diferencia visual es ~45 líneas a mano vs 3 líneas de framework. Esa es
> la lección.

### Criterios de aceptación de la Parte 1b

- [ ] **CA-2.1 Diferencia visual.** El diff entre `agente-framework/agente.py` y
  `agente-transparente/agente.py + loop.py` se reduce a: el framework encapsula el
  loop, el dispatch y el manejo de errores. No hay otra diferencia.
- [ ] **CA-2.2 Misma conversación.** Ejecutar `python -m agente_framework.chat` y
  recorrer los mismos 4 turnos de la Parte 1a. Las respuestas deben ser
  esencialmente las mismas (puede variar la redacción, no la conclusión).
- [ ] **CA-2.3 Trazas equivalentes.** La traza de LangGraph (si se imprime) muestra
  los mismos pasos: decisión de tool, ejecución, observación, siguiente iteración.
  La lección: el framework hace lo mismo, pero uno no lo ve a menos que lo busque.

---

## Parte 2 — Implementación visual en n8n

**Ubicación:** workflow importado en la instancia n8n cloud de Bios
**Archivo fuente:** `n8n/plantilla-agente-bios-react.json`
**Audiencia:** no-software (todos miran)
**Tiempo:** ~25 min (min 53–78 del guion)

### Qué se proyecta

El facilitador abre el workflow ya importado en el navegador de n8n de Bios. No
arma nada —ADR-006. Recorre nodo por nodo y ejecuta la misma conversación insignia.

Estructura del workflow:

```
┌─────────────┐     ┌───────────────────────────┐     ┌──────────┐
│  Trigger    │────▶│  AI Agent                 │────▶│  Output  │
│  (chat      │     │  ┌─────────────────────┐ │     │  (texto  │
│   input)    │     │  │  Window Buffer       │ │     │   en     │
└─────────────┘     │  │  Memory              │ │     │  canvas) │
                     │  └─────────────────────┘ │     └──────────┘
                     │  ┌─────────────────────┐ │
                     │  │  Tools:             │ │
                     │  │   • consultar_inv.  │ │
                     │  │   • consultar_dem.  │ │
                     │  │   • estado_pedido   │ │
                     │  │   • historial_fallas│ │
                     │  └─────────────────────┘ │
                     └───────────────────────────┘
                                │
                                ▼
                     ┌──────────────────┐
                     │  Azure OpenAI     │  ← credencial ya configurada
                     │  (LM creds node) │
                     └──────────────────┘
```

### Recorrido del facilitador

| Nodo | Min | Qué decir |
|---|---|---|
| Trigger | 53–55 | "Esto es el input: un mensaje de chat. En Python era `input()` en `chat.py`. Acá es un nodo." |
| AI Agent | 55–60 | "El cerebro. Igual que `cliente.py` instanciaba AzureChatOpenAI, este nodo llama al modelo. Tiene dos cosas pegadas: memoria y tools." |
| Window Buffer Memory | 60–64 | "La memoria. Igual que `memoria.py` era una lista de mensajes, este nodo mantiene la ventana. Configuramos un sessionId y guarda los turnos." |
| Cada nodo Tool | 64–72 | "Un brazo. Configurado con una descripción —que es el prompt que ve el modelo— y unos parámetros. Fíjense: mismito lo que vimos en `tools.py`." |
| Azure OpenAI cred | 72–74 | "El proveedor. Mismo .env que en Python, acá es una credencial de n8n." |
| Ejecución | 74–78 | Ejecutar el turno 1 de la conversación insignia y comparar la salida con la Parte 1. Misma respuesta, distinta forma. |

### Criterios de aceptación de la Parte 2

- [ ] **CA-3.1 Importación.** El workflow `plantilla-agente-bios-react.json` se
  importa en la instancia n8n de Bios sin errores, 24-48 h antes de la clase.
- [ ] **CA-3.2 Credencial configurada.** La credencial Azure OpenAI está registrada
  en n8n y seleccionada en el nodo AI Agent. No se pide key en clase.
- [ ] **CA-3.4 Ejecución de la conversación.** Los 4 turnos de la conversación
  insignia se ejecutan en n8n y producen respuestas esencialmente iguales a las de
  las Partes 1a/1b (puede variar redacción, no conclusión).
- [ ] **CA-3.5 Memoria visible.** El nodo Window Buffer Memory mantiene el contexto
  entre turnos: el turno 2 no exige repetir "Itagüí" ni "maíz".
- [ ] **CA-3.6 Sin armado en vivo.** No se arrastra un nodo en clase — el tiempo
  se gasta en explicar, no en construir. ADR-006.

---

## Criterios transversales de las tres partes

Independientemente del medio, las tres implementaciones DEBEN cumplir:

- [ ] **CT-1 Misma conversación insignia.** Las tres ejecutan los 4 turnos
  definidos en la spec 03 (Itagüí → demanda → equipo → pedido atascado). La
  comparación entre las tres se hace sobre las mismas preguntas.
- [ ] **CT-2 Misma base.** Todas consultan el mismo `bios_ops.db`, copia idéntica
  de la clase 1. Las respuestas numéricas deben coincidir.
- [ ] **CT-3 Mismo proveedor.** Todas usan Azure OpenAI con la misma credencial y el
  mismo deployment. No se mezclan proveedores.
- [ ] **CT-4 Memoria visible en las tres.** El turno 2 de la conversación (encadname)
  demuestra que el agente recuerda el turno 1. Si el turno 2 exige que se repita
  "Itagüí", la memoriano está funcionando — revisar antes de clase.
- [ ] **CT-5 Equivalencia conceptual.** Al terminar las tres partes, el
  participante DEBE poder señalar dónde está cada componente (cerebro, tools,
  memoria, loop) en cada implementación. Esa es la verificación de la puesta en
  común (min 78-90).

---

## Lo que NO se coutWitnessa en esta spec (fuera de alcance)

- **Persistencia de la memoria.** Las tres implementaciones pierden la memoria al
  cerrar. Tema de producción → acompañamiento.
- **Observabilidad.** No hay LangFuse/LangSmith en ninguna parte. → acompañamiento
  cuando un proyecto lo necesite.
- **Métricas de costo/latencia.** No se reportan. → acompañamiento.
- **Evals o tests automatizados.** Las CA de esta spec son verificación manual del
  facilitador, no una suite de tests. → acompañamiento.
- **Multiagente.** Un solo agente. → S4.
- **RAG.** Memoria conversacional, no recuperación de documentos. → S3.

Estos límites se declaran explícitamente para que la implementación no crezca.