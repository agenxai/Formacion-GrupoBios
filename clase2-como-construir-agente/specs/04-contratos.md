# 04 · Contratos — Clase 2

El contrato más simple de toda la formación. No hay eventos SSE, no hay API HTTP, no
hay frontend — la clase 2 es un script de terminal. Hay **dos contratos**:

1. **Tools**: las cuatro funciones + sus schemas JSON (lo que ve el modelo).
2. **Mensajes**: el formato interno del buffer de memoria (lo que pasa el agente al
   LLM en cada llamada).

El contrato de tools es el que se proyecta y se lee en la Parte 1a; en la Parte 2
(n8n) corresponde a la configuración de cada nodo Tool. Son el mismo concepto en dos
medios — esa es la lección.

---

## 1. Contrato de tools

### Por qué importa

El modelo **no ve código Python**. Ve un schema JSON que describe el nombre, los
parámetros y —críticamente— **la docstring**. Si la docstring es vaga, el agente
ignora la tool o la llama con argumentos incorrectos. Esta es la lección práctica de
la clase 1 que la clase 2 reafirma al construir el agente pieza por pieza.

> **Regla recordada de la clase 1 (spec 04): la docstring es el prompt que ve el
> modelo.** Se escribe para el modelo, no para el desarrollador.

### Las cuatro tools

Cada función DEBE cumplir las reglas heredadas: síncrona, anotada, devuelve `dict`
serializable, "sin resultados" devuelve estructura con `mensaje` (no excepción),
máximo `LIMITE_FILAS`, conexión de solo lectura.

#### `consultar_inventario`

```python
def consultar_inventario(planta: str, materia_prima: str | None = None) -> dict:
    """Consulta el inventario de materias primas de una planta al último corte.

    Devuelve, por cada materia prima, la cantidad disponible en toneladas, el
    stock mínimo definido para esa planta y si está por debajo de ese mínimo.

    Usa esta herramienta para saber CUÁNTO HAY de una materia prima. Para saber
    cuánto se NECESITA en un período, usa `consultar_demanda` indicando la misma
    materia prima.

    Args:
        planta: Nombre, municipio o código de la planta. Acepta 'Itagüí',
            'Planta Itagüí' o 'PL-ITG'.
        materia_prima: Opcional. Nombre o código de una materia prima concreta,
            por ejemplo 'maíz' o 'MP-MAIZ'. Si se omite, devuelve todas.
    """
```

**Schema JSON expuesto al modelo** (lo que el agente realmente ve):

```json
{
  "type": "function",
  "function": {
    "name": "consultar_inventario",
    "description": "Consulta el inventario de materias primas de una planta al último corte...",
    "parameters": {
      "type": "object",
      "properties": {
        "planta":       {"type": "string", "description": "Nombre, municipio o código de la planta."},
        "materia_prima": {"type": "string", "description": "Opcional. Nombre o código de la materia prima."}
      },
      "required": ["planta"]
    }
  }
}
```

**Salida** (dict, jamás excepción):

```json
{
  "planta": "Planta Itagüí",
  "fecha_corte": "2026-07-31",
  "items": [
    {"materia_prima": "Maíz amarillo", "cantidad_ton": 318.0,
     "stock_minimo_ton": 1190.0, "bajo_minimo": true}
  ],
  "truncado": false
}
```

Ejemplo sin resultados: `{"encontrado": false, "mensaje": "No encontré ..."}`.

#### `consultar_demanda`

```python
def consultar_demanda(planta: str, materia_prima: str | None = None, dias: int = 7) -> dict:
    """Consulta la demanda histórica o proyectada de una planta en un período.

    Devuelve la suma de toneladas demandadas por día en los últimos `dias` días,
    opcionalmente filtrada por materia prima. Úsala para saber CUÁNTO SE NECESITA.

    Args:
        planta: Nombre, municipio o código de la planta.
        materia_prima: Opcional. Filtra por materia prima concreta.
        dias: Período hacia atrás en días. Por defecto 7 (semana).
    """
```

**Salida**:

```json
{
  "planta": "Planta Itagüí",
  "materia_prima": "Maíz amarillo",
  "dias": 7,
  "total_ton": 1651.9,
  "por_dia": [
    {"fecha": "2026-07-25", "toneladas": 236.0}, ...
  ]
}
```

#### `estado_pedido`

```python
def estado_pedido(pedido_id: str) -> dict:
    """Consulta el estado y avance de un pedido por su número.

    Devuelve el estado actual, cuántos pasos le faltan hasta 'entregado' y, si
    está en muelle, qué turno de cargue tiene asignado. Es la base de la interfaz
    tipo aeropuerto: el cliente pregunta y obtiene dónde está su pedido.

    Args:
        pedido_id: Número del pedido. Formato 'PD-24-XXXXX'.
    """
```

**Salida** (incluye `pasos_faltantes` y `turno_muelle` — el "su vuelo aborda por la
puerta 12" del caso de Logística):

```json
{
  "pedido": "PD-24-00871",
  "cliente": "Avícola El Roble",
  "producto": "Concentrado avícola",
  "toneladas": 42.0,
  "estado": "en_muelle",
  "pasos_faltantes": 3,
  "turno_muelle": 6,
  "mensaje": "El pedido está en muelle, en cola turno 6 de 8."
}
```

#### `historial_fallas`

```python
def historial_fallas(planta: str, dias: int = 30) -> dict:
    """Consulta el historial de fallas y el estado de los equipos de una planta.

    Devuelve las órdenes de mantenimiento del período, con causa, horas de paro y
    costo, y una tendencia de las lecturas del sensor (vibración, temperatura,
    amperaje) del último equipo con fallas. Úsala para diagnosticar riesgo.

    Args:
        planta: Nombre, municipio o código de la planta.
        dias: Período hacia atrás en días. Por defecto 30.
    """
```

**Salida**:

```json
{
  "planta": "Planta Itagüí",
  "ordenes": [
    {"id": "OM-000123", "equipo": "EQ-ITG-MOL-01", "tipo": "correctivo",
     "causa": "vibración alta", "horas_paro": 5.5, "costo_cop": 2_300_000}
  ],
  "tendencia_sensor": {
    "equipo": "EQ-ITG-MOL-01",
    "variable": "vibracion_mm_s",
    "pendiente": 0.42,
    "mensaje": "Vibración creciente, +0.42 mm/s por día."
  }
}
```

### Exportación de schemas para el agente

`tools.py` DEBE exponer dos cosas que `loop.py` y `agente.py` consumen:

```python
# agente-transparente/tools.py

TOOLS: list            # las cuatro funciones, listas para pasárselas al LLM
SCHEMAS: list[dict]    # los cuatro schemas JSON, listos para la API
                       # (langchain nos da @tool, pero acá se escriben a mano
                       #  para que se VEAN en clase — ADR-002)

def dispatch(name: str, args: dict) -> dict:
    """Ejecuta la tool por nombre. Es lo que loop.py llama tras la tool_call."""
```

> **Por qué `dispatch` a mano:** en la Parte 1a se escribe el loop a mano (ADR-002);
> el loop recibe el nombre de la tool como string y sus argumentos como dict, y tiene
; que llamar la función. Un `dispatch` explícito lo hace visible. En la Parte 1b,
> `create_react_agent` recibe las tools con `@tool` y hace el dispatch internamente —
> ahí se ve qué abstrae el framework.

### Equivalencia con n8n (Parte 2)

Cada tool de la Parte 1a se materializa en la Parte 2 como un nodo **Tool** dentro del
nodo **AI Agent** de n8n:

| Python (Parte 1a/1b) | n8n (Parte 2) |
|---|---|
| Función `consultar_inventario` | Nodo Tool, tipo "HTTP Request" o "Code", apuntando a la misma consulta SQL |
| Docstring | Campo `Description` del nodo Tool (es lo que ve el modelo) |
| Schema JSON de parámetros | Campos `Parameters` del nodo Tool |
| Límite de filas, `truncado` | Lógica interna del nodo Tool |
| `dispatch` | El nodo AI Agent de n8n lo hace internamente |

Esa tabla es la lección: **mismo concepto, dos medios**. No se enseña dos veces —se
proyecta una vez y la equivalencia se hace evidente.

---

## 2. Contrato de mensajes (memoria)

El buffer de memoria DEBE usar el formato OpenAI de mensajes, que es el que la API
de Azure OpenAI espera en cada llamada:

```python
# agente-transparente/memoria.py

class Memoria:
    def agregar(self, rol: str, contenido: str) -> None:
        """rol: 'system' | 'user' | 'assistant' | 'tool'."""

    def mensajes(self) -> list[dict]:
        """Devuelve la lista, formato OpenAI:
        [{"role": "system", "content": "..."},
         {"role": "user",   "content": "..."},
         {"role": "assistant", "content": "..."},
         {"role": "tool", "tool_call_id": "...", "content": "..."}]
        """
```

### Por qué una clase y no una lista libre

Para que `agente.py` sea legible: `memoria.agregar("user", pregunta)` se lee como
prosa. Una lista de dicts suelta metería ruido visual en el `agente.py` proyectado.
El punto pedagógico no es la clase —es que la memoria **es** esa lista, y la clase
solo la envuelve para que se lea bien. Eso se dice en voz alta al explicar.

### Lo que NO hace la memoria (fuera de alcance, spec 01)

- **No persiste entre ejecuciones.** Al cerrar el script, el buffer se pierde. La
  persistencia es tema de producción (acompañamiento S5–S7).
- **No recorta ventanas.** Si la conversación crece, los mensajes se pasan completos.
  La compresión de contexto es tema de S3 (RAG / context engineering). El sistema de
  la clase 2 es deliberadamente simple para que el concepto de memoria sea visible.

### Equivalencia con n8n (Parte 2)

En n8n, la memoria se materializa como un nodo **Window Buffer Memory** configurado
con `sessionId` (un identificador de conversación) y un tamaño de ventana. El
concepto es idéntico: acumular los mensajes previos y pasarlos en la próxima llamada.
La diferencia es que n8n lo configura uno en un formulario; en Python lo vemos como
una lista.

---

## 3. Contrato del loop ReAct (Parte 1a)

`loop.py` implementa el ciclo Thought → Action → Observation a mano. Su contrato es
el patrón que el participante debe reconocer en el cierre de la Parte 1b como lo que
`create_react_agent` abstrae.

```python
# agente-transparente/loop.py

def react(cliente, tools, memoria, pregunta) -> str:
    """Ejecuta el ciclo ReAct sobre una pregunta.

    Pasos:
    1. Agrega la pregunta del usuario a la memoria.
    2. Llama al LLM con la lista de mensajes + los schemas de tools.
    3. Si la respuesta contiene tool_calls:
         a. Para cada tool_call: ejecuta la tool vía `dispatch`.
         b. Agrega cada resultado a la memoria como mensaje 'tool'.
         c. Vuelve al paso 2 (siguiente iteración del ciclo).
    4. Si no hay tool_calls: es la respuesta final.
         a. Agrega la respuesta a la memoria como mensaje 'assistant'.
         b. Devuelve el texto.
    """
```

**Salida impresa por el loop** (para que se vea en terminal mientras se proyecta):

```
[Thought]  El usuario pregunta por el inventario de maíz en Itagüí. Necesito
           consultar la base de operaciones.
[Action]   consultar_inventario(planta="Itagüí", materia_prima="maíz")
[Observation] {"planta": "Planta Itagüí", "items": [{"materia_prima": "Maíz
               amarillo", "cantidad_ton": 318.0, "bajo_minimo": true}], ...}
[Thought]  El inventario reporta 318 t, bajo el mínimo de 1190 t. El usuario
           no preguntó sobre la demanda todavía; termino y respondo.
[Respuesta] En Itagüí quedan 318 toneladas de maíz amarillo...
```

Esa salida impresa es **el contrato pedagógico**: lo que ven en pantalla es la
definición de ReAct del ebook de la clase 1, encarnado. El teach moment es cuando
alguien del grupo dice "eso es el loop del ebook" — y ahí se conecta S1 con S2.

### Límites duros del loop

- `MAX_ITERACIONES = 5` — si el agente no resuelve en 5 vueltas, se corta con un
  mensaje y se reporta en la traza. Evita ciclos infinitos y deterioro del contexto.
- Toda llamada al LLM envuelta en `try/except`; fallo de API se reporta y no se
  propaga como stack trace. Misma regla que las tools: el agente se recupera de
  errores, no se cae.

### Equivalencia con el framework (Parte 1b)

```python
# agente-framework/agente.py — la pieza que cambia
from langgraph.prebuilt import create_react_agent

agente = create_react_agent(cliente, TOOLS, prompt=SYSTEM_PROMPT)
```

`create_react_agent` encapsula: el ciclo, el dispatch, el manejo de errores, el
rekacionamiento de tool_calls, y el agregado de mensajes a la memoria. Al proyectar
este `agente.py` junto al `loop.py` + `agente.py` de la carpeta transparente, **la
diferencia visual es la lección**.

---

## Diferencias estructurales con la clase 1 (spec 04)

| | Clase 1 | Clase 2 |
|---|---|---|
| Eventos SSE tipados | Sí (10 tipos) | No hay —no hay frontend |
| API HTTP | Sí (POST/GET/stream) | No —script de terminal |
| Contract de herramientas | 7 tools + `ejecutar_sql` con 6 restricciones | 4 tools, sin `ejecutar_sql` (no se enseña SQL abierto en S2) |
| Formato de mensajes | LangChain BaseMessage | Dicts OpenAI puros —para que se vean en pantalla |
| Métricas y costo | Evento `metricas` por run | No se reporta —tema de S5 en acompañamiento |