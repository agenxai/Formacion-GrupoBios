# 05 · Niveles de agencia N1–N5

Un nivel por sección. Cada uno declara: qué hace, qué NO hace, qué eventos emite, qué
debe entender el participante, y **criterios de aceptación verificables**.

La pregunta insignia, usada en las cinco demos:

> **«¿Cuánto maíz le queda a la planta de Itagüí y me alcanza para la demanda
> proyectada de esta semana?»**

Elegida porque requiere **dos consultas distintas y una comparación**. N1 la inventa,
N2 solo la clasifica, N3 la responde a medias, N4 la responde bien. La progresión se
ve con una sola pregunta.

---

## N1 · Procesador simple ☆☆☆

**Patrón:** `process_llm_output(llm_response)`

### Comportamiento
Una única llamada al modelo. Sin tools declaradas. Sin decisiones. El system prompt lo
presenta como asistente de operaciones de una planta, para que el modelo se sienta
autorizado a responder con cifras.

### Qué NO hace
No consulta la base. No tiene forma de saber nada real.

### El momento pedagógico
El modelo **producirá una cifra inventada** o se negará vagamente. Ambos resultados
sirven, y hay que estar preparado para los dos:

- Si inventa: se contrasta con el valor real de la base, proyectado al lado. Es la
  demostración más contundente de la clase.
- Si se niega ("no tengo acceso a esos datos"): la lección es igual de buena —
  *incluso portándose bien, es inútil para la operación*. El facilitador entonces
  presiona con "estima un valor típico" y normalmente sí produce una cifra.

El tablero DEBE emitir un evento `aviso` de gravedad `alerta` cuando detecte en la
respuesta de N1 un patrón numérico con unidad de masa (`\d+([.,]\d+)?\s*(ton|tonelada|kg)`),
con el texto: *«El modelo afirmó una cantidad sin haber consultado ninguna fuente.»*

Es una heurística, no un detector de alucinaciones, y DEBE describirse como tal en la
UI. No se le enseña al grupo que existe una forma barata de detectar alucinaciones.

**Y por eso mismo DEBE existir un respaldo manual.** El regex falla ante «alrededor de
media tonelada», «unas 450», «entre 400 y 500 t» o cualquier redacción que no previmos —
y esto ocurre en el clímax de la demo, con el grupo mirando. La columna de N1 DEBE
incluir un control del facilitador —*«marcar como afirmación sin fuente»*— que emite el
mismo evento `aviso` a mano.

Diseñar la demo para que dependa de un regex acertando en vivo es exactamente el tipo
de fragilidad que esta formación enseña a evitar. El botón es la implementación de ese
principio sobre nuestro propio producto.

### Eventos
`inicio` → `llm_request` → `llm_response` → [`aviso`] → `respuesta_final` →
`metricas` → `fin`

### Criterios de aceptación
- `llamadas_llm == 1`, `llamadas_tools == 0`.
- `tools_declaradas == []` en el `llm_request`.
- Con la pregunta insignia, la respuesta NO contiene el valor real de inventario de la
  base (verificado contra la consulta directa). Si alguna vez lo acertara, es
  coincidencia y el criterio se relaja a: no hubo ninguna tool call.

---

## N2 · Enrutador ★☆☆

**Patrón:** `if llm_decision(): path_a() else: path_b()`

### Comportamiento
El modelo clasifica la pregunta en uno de cuatro dominios —`mantenimiento`, `compras`,
`logistica`, `demanda`— y devuelve el motivo. El sistema **no ejecuta** la ruta: solo
la reporta.

Implementado con salida estructurada (`with_structured_output` sobre un modelo
Pydantic), no con parsing de texto libre. Es la ocasión para introducir salida
estructurada, que se usará todo el programa.

### Qué NO hace
No consulta datos. No responde la pregunta. Elige un camino y se detiene ahí.

### El momento pedagógico
Dos cosas. Primera: el LLM como **decisor**, no como generador de texto — el cambio
mental que abre la puerta a los agentes. Segunda: la frontera de este nivel es
visible. Ante «¿me alcanza el maíz?», enruta a `compras` y no sirve de nada. La
pregunta natural del grupo —"¿y ahora quién ejecuta?"— es la entrada a N3.

Vale mostrar en vivo una pregunta ambigua («el pedido de la avícola no llegó y creo
que el molino está parado») para que se vea que el router tiene que elegir uno y ya
pierde información. Eso siembra la arquitectura de supervisor de N5.

### Eventos
`inicio` → `llm_request` → `llm_response` → `ruta` → `respuesta_final` → `metricas` → `fin`

### Criterios de aceptación
- `llamadas_llm == 1`, `llamadas_tools == 0`.
- Emite exactamente un evento `ruta` con `dominio` dentro del enum de cuatro valores.
- Un set de 8 preguntas etiquetadas a mano DEBE clasificarse correctamente en al
  menos 7. Ese set es el primer *golden dataset* del programa y se referencia en la
  Sesión 5.

---

## N3 · Llamador de herramientas ★★☆

**Patrón:** `run_function(llm_chosen_tool, llm_chosen_args)`

### Comportamiento
Loop de function calling **escrito a mano** (ADR-003), sin `create_react_agent`:

1. Llamada al modelo con las tools declaradas.
2. Si la respuesta trae `tool_calls`: se ejecuta la función, se agrega el resultado al
   historial como mensaje de tool.
3. Segunda llamada al modelo, con el resultado en contexto.
4. Se responde. **Se detiene aquí, a propósito: máximo una ronda de tools.**

### Qué NO hace
No itera. Si tras la primera ronda hace falta otra consulta, no la hace: responde con
lo que tiene. Esa limitación es el contenido del nivel.

### El momento pedagógico
El más importante de la clase. Dos cosas se ven en pantalla:

1. **El JSON crudo de la tool call**, campo `crudo` del evento, idéntico en forma al
   de la sección 7.2 del ebook. Se proyecta y se compara con el documento.
2. **El límite de una sola ronda.** Con la pregunta insignia, el agente consulta
   inventario y responde «tiene 320 toneladas» — sin comparar contra la demanda,
   porque no le dieron un segundo turno. Está *correcto pero incompleto*. La pregunta
   "¿qué le falta?" tiene una respuesta de una palabra: **iterar**. Eso es N4.

Ese contraste correcto-pero-incompleto es más didáctico que un error, y por eso el
tope de una ronda es un requisito y no un descuido.

**Y por eso N3 DEBE pedir `parallel_tool_calls=False`.** Sin ese parámetro el modelo
pide inventario y demanda en la misma respuesta, resuelve todo en su única ronda y
responde igual de bien que N4 gastando menos — el nivel superior parece innecesario y
el contraste desaparece. Se descubrió en la primera corrida real contra la API: N3 y
N4 devolvieron la misma conclusión. Además rompe el criterio `llamadas_tools == 1` y
con él el `assert` del notebook, en las quince máquinas a la vez.

Con el parámetro, lo que ocurre en vivo es incluso mejor de lo previsto: N3 consulta
el inventario, ve que está bajo el mínimo y **afirma que no alcanzará para la demanda
sin haber consultado la demanda**. Una conclusión plausible y no verificada — que es
exactamente lo que N4 va a verificar con la cifra real. El facilitador tiene ahí un
segundo ejemplo, más sutil que el de N1, de afirmación sin fuente.

### Eventos
`inicio` → `llm_request` → `llm_response` → `tool_call` → `tool_result` →
`llm_request` → `llm_response` → `respuesta_final` → `metricas` → `fin`

### Criterios de aceptación
- `llamadas_llm == 2` cuando hubo tool call; `== 1` si el modelo respondió directo.
- `llamadas_tools <= len(tool_calls de la primera respuesta)`, y en ningún caso hay
  una segunda ronda.
- Todo evento `tool_call` DEBE traer `crudo` no vacío y parseable como JSON.
- Con la pregunta insignia: consulta `consultar_inventario` y su respuesta contiene el
  valor real de la base.

---

## N4 · Agente multipasos (ReAct) ★★★

**Patrón:** `while llm_should_continue(): execute_next_step()`

### Comportamiento
`create_react_agent` de LangGraph con las 7 tools. Ciclo Thought → Action →
Observation hasta responder o alcanzar el tope de iteraciones.

- `max_iteraciones = 8`. Al alcanzarlo, emite `aviso` y responde con lo acumulado.
  Nunca se cuelga en clase.
- El system prompt DEBE pedir una frase corta de razonamiento antes de cada acción
  (ver la nota sobre `pensamiento` en spec 04).

### El momento pedagógico
Tres:

1. **Encadenamiento autónomo.** Nadie le dijo que consultara dos tablas. Con la
   pregunta insignia hace `consultar_inventario` → `consultar_demanda` → compara →
   responde con un juicio: *«no alcanza»*, con la brecha concreta.

   Con los datos generados, la brecha real es de ~1.330 t: la planta tiene 320 t de
   maíz y la demanda de la semana requiere ~1.652 t. Las versiones anteriores de esta
   spec decían «faltan ~40 t», una cifra ilustrativa que el generador no podía
   producir manteniendo a la vez el inventario de 320 t —que sí es un número con
   contrato, verificado por un `assert` de la spec 08— y una utilización de planta
   creíble. El criterio de aceptación es que la respuesta CONCLUYA, no la magnitud.
2. **Cuánto abstrae el framework.** Se muestra el código de N3 (≈60 líneas) al lado
   del de N4 (≈15). La misma capacidad, más el loop. Se nombra explícitamente lo que
   `create_react_agent` hace por debajo, para que no quede como magia.
3. **El costo.** 5 llamadas al modelo contra 2 de N3. Se ve en la fila de métricas.

### Eventos
`inicio` → (`llm_request` → `llm_response` → [`pensamiento`] → `tool_call` →
`tool_result`)⁺ → `llm_request` → `llm_response` → `respuesta_final` → `metricas` → `fin`

### Criterios de aceptación
- Con la pregunta insignia: `llamadas_tools >= 2`, e incluye `consultar_inventario` y
  `consultar_demanda`.
- La respuesta final contiene una conclusión comparativa —una palabra del conjunto
  {alcanza, no alcanza, suficiente, insuficiente, faltan, déficit}—, no solo dos
  cifras sueltas.
- `llamadas_llm <= 9` (tope + cierre). Nunca desbordado.
- Ante una pregunta sin datos («inventario de la planta de Cali», que no existe), NO
  DEBE inventar: la tool devuelve vacío y el agente lo reporta. Este criterio cierra
  el arco que abrió N1 y DEBE demostrarse en clase.

---

## N5 · Sistema multiagente (supervisor) ★★★★

**Patrón:** `if llm_trigger(): execute_agent()`

### Comportamiento
Arquitectura **supervisor con agentes como tools** — la variante de la sección 8.1 del
ebook. Un supervisor con dos sub-agentes especializados, cada uno con su propio
system prompt y su propio subconjunto de tools:

| Sub-agente | Tools | Responde sobre |
|---|---|---|
| `agente_abastecimiento` | `consultar_inventario`, `consultar_demanda`, `consultar_produccion` | Compras, demanda, producción |
| `agente_operaciones` | `historial_fallas`, `lecturas_sensor`, `estado_pedido`, `turnos_muelle` | Mantenimiento y logística |

Cada sub-agente es un ReAct de N4. El supervisor los ve como dos tools, decide a
quién llamar (o a los dos) y sintetiza.

### Por qué cabe en 12 minutos de clase

N5 **se construye reutilizando N4**, y eso es precisamente lo que enseña la
arquitectura. El participante ya tiene un ReAct funcionando; N5 consiste en:

1. Instanciarlo dos veces, cada una con su system prompt y su subconjunto de tools.
2. Envolver cada instancia en una función con docstring — **un agente expuesto como
   tool es solo una función que por dentro llama a un agente**.
3. Pasar esas dos funciones como tools a un tercer ReAct.

Cuatro líneas de código, y la revelación de que la sección 8.1 del ebook —"supervisor
con llamada a herramientas"— no es una arquitectura nueva sino la misma de N4 aplicada
un nivel más arriba. Si N4 quedó funcionando, N5 es corto. Si N4 no quedó, la celda de
rescate lo provee (spec 08).

### El momento pedagógico
La pregunta de demo cambia, porque debe **cruzar los dos dominios**:

> «El pedido PD-24-00871 va retrasado. ¿Es por falta de materia prima o por un
> problema de equipos?»

El supervisor consulta a los dos sub-agentes y sintetiza un diagnóstico. Se ve un
agente delegando en otro agente, y en el tablero se ve la anidación (`sub_evento`).

**Lo que responde de verdad, medido:** delega en los dos agentes y concluye que **no
es ninguna de las dos cosas** — el pedido está esperando turno de muelle en la
posición 6 de la cola, sin fallas de equipos que lo afecten.

Es decir: la pregunta plantea un falso dilema y el agente no acepta la premisa. Esta
spec esperaba antes que concluyera «es por materia prima», y estaba equivocada: los
datos dicen que el pedido está detrás de cinco camiones. Se corrige la spec, no los
datos — doblar el dataset para que encaje con el guion sería fabricar la conclusión,
que es precisamente lo que este laboratorio enseña a no hacer.

Y el resultado es mejor guion: **un agente que rechaza la premisa de la pregunta, con
evidencia de dos dominios, es más impresionante que uno que confirma lo que ya
esperábamos.** Los criterios de aceptación no cambian: sigue habiendo dos
delegaciones y sigue costando más que N4.

Y —esto es lo que hay que decir en voz alta— se ve que **cuesta 11 llamadas al
modelo lo que N4 hacía en 5**. La conclusión de diseño de la sesión es que el
multiagente se justifica cuando hay separación real de dominios y contextos, no por
sofisticación. Es la misma advertencia de la sección 8 del ebook, ahora con la
factura al lado.

### Eventos
`inicio` → `llm_request`/`llm_response` (supervisor) → `delegacion` →
`sub_evento`⁺ (actividad interna del sub-agente) → [`delegacion` → `sub_evento`⁺] →
`llm_request`/`llm_response` (síntesis) → `respuesta_final` → `metricas` → `fin`

Los `sub_evento` anidan **un solo nivel**. Un sub-agente no delega.

### Criterios de aceptación
- Emite al menos un `delegacion`.
- Con la pregunta de demo: emite dos `delegacion`, una a cada sub-agente.
- `llamadas_llm` de N5 > `llamadas_llm` de N4 para la misma pregunta. La comparación
  de costo DEBE ser demostrable, no afirmada.
- Todo `sub_evento` DEBE cumplir el mismo contrato de eventos en su campo `evento`.
- Tope global de 20 llamadas al modelo por run. Al alcanzarlo, corta y responde.

---

## Tabla de cierre

Se proyecta al final del bloque. Los números se llenan **con la corrida real de la
clase**, no pregrabados:

| | N1 | N2 | N3 | N4 | N5 |
|---|---|---|---|---|---|
| Nivel de agencia | ☆☆☆ | ★☆☆ | ★★☆ | ★★★ | ★★★★ |
| Decide algo | no | qué ruta | qué tool | qué tools y cuántas veces | a qué agente |
| Consulta datos | no | no | 1 ronda | N rondas | vía sub-agentes |
| ¿Responde bien la insignia? | inventa | no responde | a medias | sí | sí |
| Llamadas al modelo | 1 | 1 | 2 | 2–3 | 5–6 |
| Costo relativo en tokens | 1× | ~1× | ~12× | ~30–60× | ~40–50× |

> **Estas cifras son medidas, no estimadas** (gpt-4o-mini, corridas reales contra la
> API). Las versiones anteriores de esta spec decían «~5 llamadas» para N4 y «~11»
> para N5. El número real es menor porque **los modelos actuales piden varias tools
> en paralelo en una misma respuesta**: N4 resuelve en dos llamadas lo que la spec
> suponía en cinco.
>
> Consecuencia para la clase, y no es menor: **la factura no se lee en el número de
> llamadas, se lee en tokens.** N3 y N4 pueden empatar en llamadas y diferir 3× en
> tokens, porque lo que crece es el contexto que se reenvía en cada vuelta. Por eso
> la tabla del tablero calcula el costo relativo sobre tokens y no sobre llamadas.
> Vale decirlo en voz alta en el minuto 50: contar llamadas es la intuición fácil y
> es la equivocada.
| Cuándo usarlo | clasificar texto | triage, routing | consulta puntual | análisis multi-fuente | dominios separados |

La última fila es el entregable intelectual: cada Champion DEBE poder señalar en qué
columna cae su proyecto y por qué.
