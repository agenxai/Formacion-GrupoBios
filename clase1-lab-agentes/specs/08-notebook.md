# 08 · Notebooks

**Dos**, y la distinción decide todo lo demás.

| Notebook | Importa del repo | Para qué |
|---|---|---|
| `1-los-cinco-niveles-explicado.ipynb` | **nada** | Explicar el código en clase |
| `2-los-cinco-niveles-taller.ipynb` | `backend/*` | Que el participante lo construya |

## Por qué hay dos

El taller usa `NivelBase`, `stream_react` y el contrato de eventos porque su código es
**el mismo que corre detrás del tablero**: así lo que el participante construye es lo
que después ve dibujado. Esa decisión es correcta para construir y equivocada para
explicar — al proyectar el taller, la primera pregunta del facilitador fue por qué el
código era tan complejo, y tenía razón: la plomería que hace posible el tablero es
ruido cuando lo que se explica es qué ES un llamador de herramientas.

El notebook explicado no arregla al taller: cubre otro momento de la clase.

### Requisitos del notebook explicado

- **NO DEBE importar nada de `backend/`.** Es lo que lo hace legible y lo que permite
  correrlo en Colab con un `pip install openai` — el plan C de quien no logre levantar
  Docker. Hay una comprobación en el generador que falla si alguna celda lo intenta.
- **Llamadas síncronas.** `async`/`await` en una celda que se proyecta es un impuesto
  sin contrapartida.
- **La fuente de datos DEBE ser un diccionario que quepa en pantalla.** Con quince
  líneas de datos, nadie confunde el mérito del agente con el mérito del SQL.
- **Los esquemas de herramientas se escriben a mano.** Generarlos desde la firma es lo
  correcto en producción y esconde justo lo que hay que ver: el JSON que viaja.
- **N4 DEBE ser N3 dentro de un `while`**, y verse. La distancia entre ★★☆ y ★★★ son
  tres líneas; si el código no lo muestra, hay que explicarlo con palabras y se pierde.
- **N5 DEBE construirse llamando a `n4()`**, para que la función `n5()` quepa en una
  línea y la revelación —«no es una arquitectura nueva»— sea visible en el código.
- Cada nivel cierra con **👀 Qué acaba de pasar** y **🔬 Tu turno**, un experimento de
  una línea. `max_vueltas=1` convierte N4 en N3; quitar la planta de la pregunta de N5
  reproduce el modo de falla del multiagente.

### Verificación

El notebook explicado DEBE ejecutarse completo con
`jupyter nbconvert --execute` contra la API real antes de cada clase. No es
opcional: la primera versión tenía todas las líneas de cada celda concatenadas en una
—un defecto del formato `.ipynb`, invisible al leer el JSON— y solo apareció al
ejecutarlo.

---

## El taller

`notebook/2-los-cinco-niveles-taller.ipynb` — el artefacto que construye cada
participante.

## Relación con el tablero

El tablero **muestra**; el notebook **construye**. Reconstruyen los mismos cinco
niveles importando las mismas tools y el mismo cliente de modelo desde `backend/`.

Lo que el notebook NO hace: reimplementar las tools ni el cliente. Importa
`backend.tools.operaciones` y `backend.llm`. El participante escribe **agentes**, no
plomería. En 55 minutos no hay tiempo para plomería, y además la plomería no es el
tema de la sesión.

## Estructura de celdas

Siete secciones. Cada nivel sigue el mismo ritmo de cinco celdas, porque la
repetición del formato libera atención para el contenido:

```
0 · Preparación
1 · N1 · Procesador simple        ☆☆☆
2 · N2 · Enrutador                ★☆☆
3 · N3 · Llamador de herramientas ★★☆
4 · N4 · Agente multipasos        ★★★
5 · N5 · Supervisor multiagente   ★★★★
6 · Cierre: tu propia tool
```

### Ritmo de cada nivel

Cinco celdas, no seis. Con los cinco niveles dentro de 55 minutos (spec 01), cada
celda extra por nivel cuesta cinco veces su tiempo:

| Celda | Tipo | Contenido | Presupuesto |
|---|---|---|---|
| **Explico** | Markdown | Qué es este nivel, el diagrama del ebook, el patrón de código. **≤ 120 palabras** — se lee en 40 segundos. | — |
| **Construyo** | Código | Andamiaje completo con `# TODO` en las **2–4 líneas clave** y nada más. | el grueso del tiempo |
| **Corro y verifico** | Código | Ejecuta, imprime la traza y corre los `assert`. **Fusionadas**: nadie ejecuta dos celdas seguidas cuando una basta. | ~1 min |
| **Observo** | Markdown | **Dos** preguntas dirigidas (no tres). Se responden en voz alta, colectivamente, mirando el tablero proyectado. | ~1 min |
| **Reto** | Código | Ejercicio abierto + `[NÚCLEO]` aparte. **Explícitamente opcional en clase**, marcado *«para después de la sesión»*. | 0 min en clase |

### Presupuesto de líneas por nivel

Requisito verificable, no una aspiración. Los `# TODO` de cada nivel DEBEN sumar como
máximo:

| Nivel | `# TODO` | Qué queda al descubierto |
|---|---|---|
| N1 | **0** | Nada. Se ejecuta y se observa la cifra inventada. |
| N2 | **2** | El modelo Pydantic de salida estructurada |
| N3 | **4** | El bloque que ejecuta la tool call y la reinyecta al historial |
| N4 | **3** | `create_react_agent`, lista de tools, system prompt |
| N5 | **4** | Los dos sub-agentes como tools + el supervisor |

Todo lo demás —imports, cliente del modelo, impresión de trazas, `assert`— viene
escrito. Si al construir el notebook un nivel excede su presupuesto, se mueve código
a `backend/`, no se amplía el presupuesto.

### Checkpoints de tiempo

Cada sección DEBE abrir con una marca visible de reloj:

> ⏱ **Minuto 25 de 55.** Si tu N3 no corre, ejecuta la celda de rescate y sigue a N4.

Es lo que le permite al facilitador cortar sin negociar caso por caso: el reloj está
impreso en el notebook y no es una opinión suya.

### Regla de independencia entre secciones

**Cada sección DEBE poder ejecutarse sin haber completado las anteriores.** Es el
requisito que sostiene todo el diseño para un grupo heterogéneo (spec 01).

Mecanismo: al inicio de cada sección, una celda plegada con la implementación de
referencia del nivel anterior, y la instrucción visible:

> *Si tu N3 no quedó funcionando, ejecuta la celda de abajo y sigue. No te quedes
> atrás por esto — el nivel 4 es lo importante.*

Sin esto, un Champion trabado a los 20 minutos pierde los 35 restantes. Con esto,
pierde cinco.

### Las celdas de verificación

Los `assert` no son adorno. Convierten los criterios de aceptación de la spec 05 en
código ejecutable:

```python
# 3 · Verifico
traza = ultima_traza()
assert traza.llamadas_llm == 2, f"N3 hace exactamente 2 llamadas, hizo {traza.llamadas_llm}"
assert traza.llamadas_tools == 1
assert traza.tool_calls[0].crudo, "Falta el JSON crudo de la tool call"
assert "320" in traza.respuesta_final, "La respuesta debe traer el valor real de la base"
print("✓ N3 correcto")
```

Cumplen dos funciones. Inmediata: el participante sabe si terminó, sin preguntarle al
facilitador — quince personas preguntando "¿así está bien?" es lo que hace fracasar un
hands-on. Diferida: es su primer contacto con testing de agentes, y en la Sesión 5 se
retoma explícitamente («esto que hicieron a mano en la sesión 1 es un eval»).

## Sección 0 · Preparación

Debe correr en menos de 10 segundos y dejar todo listo:

```python
# Aviso de datos sintéticos (spec 03) — celda markdown, la primera del notebook
```

```python
from backend.llm import cliente, estado
from backend.tools.operaciones import TODAS as TOOLS
from backend.db import consulta_directa

estado()          # modo, modelo, key presente, gasto acumulado
len(TOOLS)        # 7
```

Y una celda de **verificación de entorno** que falle con mensaje accionable:

```python
verificar_entorno()
# ✓ Python 3.12.x
# ✓ langgraph 0.x.y
# ✓ bios_ops.db  (11 tablas, 12.5k filas)
# ✓ OPENAI_API_KEY presente
# ✓ Conectividad con la API: 240 ms
# → Todo listo. Puedes empezar por la sección 1.
```

Si algo falla, el mensaje DEBE decir qué hacer, no solo qué pasó. `verificar_entorno()`
es lo que se pide correr en el preflight de 24 h antes de la clase (spec 09).

## Sección 6 · Cierre: tu propia tool

**Ejercicio post-sesión.** Con los cinco niveles dentro de los 55 minutos (spec 01),
esta sección no se trabaja en clase: se presenta en el minuto 54, en 60 segundos, como
el entregable que cada Champion trae al recap de la Sesión 2.

Es el ejercicio más valioso del notebook y por eso no se sacrifica: se mueve. Mismo
enunciado para los cuatro dominios:

> **Escribe la tool que tu proyecto necesita** y conéctala al agente de N4.
>
> 1. Elige una pregunta real de tu proyecto que hoy nadie puede responder rápido.
> 2. Escribe la función Python que la responde consultando `bios_ops.db`.
> 3. Escribe su docstring **pensando en el modelo**, no en un desarrollador.
> 4. Agrégala a la lista de tools de tu N4 y pregúntale al agente.
> 5. ¿La usó? Si no la usó, la docstring es la sospechosa. Reescríbela.

El paso 5 es el que enseña. Que un agente ignore una tool porque su descripción es
mala es la lección más transferible de la sesión, y hay que provocarla.

Con andamiaje por dominio: cuatro celdas plegadas con el esqueleto de una tool
sugerida para mantenimiento, compras, logística y demanda respectivamente.

## Retos `[NÚCLEO]`

Uno por nivel, para los cuatro avanzados. Diseñados para producir algo que se pueda
mostrar a la mesa, no para adelantarse en solitario:

| Nivel | Reto `[NÚCLEO]` |
|---|---|
| N1 | Escribe un system prompt que impida inventar cifras. Mide cuántas veces de 10 falla igual. |
| N2 | Agrega un quinto dominio y un caso ambiguo. ¿Qué hace el router? |
| N3 | Haz que el modelo pida dos tools en la misma respuesta. ¿Las ejecuta el loop en paralelo? |
| N4 | Provoca que una tool falle y observa la recuperación. Luego haz que falle siempre: ¿corta el tope de iteraciones? |
| N5 | Agrega un tercer sub-agente. Mide el costo antes y después. |

Cada reto `[NÚCLEO]` termina con: *«Muéstralo a tu mesa.»*

## Requisitos técnicos

- Se ejecuta en el servicio `notebook` del compose, en `http://localhost:8888`. Sin
  token de Jupyter (red local de sesión) y documentado como tal.
- El notebook se versiona **con las salidas limpias** (`nbstripout` o equivalente en
  el flujo de commit). Un notebook con salidas de otra corrida confunde.
- Toda celda de código DEBE ser ejecutable de forma independiente tras la sección 0.
  Sin dependencias ocultas de estado entre celdas distantes.
- El notebook DEBE funcionar en `MODO=replay`, para que quien se quede sin key pueda
  recorrer las trazas. Los `assert` de verificación DEBEN pasar también en replay.
