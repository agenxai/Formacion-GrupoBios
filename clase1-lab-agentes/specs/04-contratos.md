# 04 · Contratos

El documento más importante del conjunto. Tres contratos: **eventos**, **tools** y
**API HTTP**. El de eventos es el que hace posible todo lo demás.

---

## 1. Contrato de eventos

### Por qué existe

Los cinco niveles son arquitecturas distintas: uno solo llama al modelo, otro corre un
grafo de LangGraph, otro delega en sub-agentes. Si cada uno reportara su actividad a su
manera, el frontend tendría cinco lógicas de render y la comparación entre niveles
sería incomparable — estaríamos midiendo con cinco reglas distintas.

**Todos los niveles emiten el mismo stream de eventos tipados.** El frontend no sabe
qué nivel está renderizando. Y la tabla comparativa mide lo mismo en las cinco
columnas.

### Campos comunes

Todo evento DEBE incluir:

| Campo | Tipo | Descripción |
|---|---|---|
| `tipo` | `str` | Discriminador. Uno de los definidos abajo. |
| `nivel` | `str` | `"n1"`…`"n5"` |
| `run_id` | `str` | UUID de la ejecución |
| `seq` | `int` | Correlativo desde 0, por run. Permite detectar pérdidas. |
| `ts_ms` | `int` | Milisegundos desde el inicio del run. **Relativo, no epoch** — así las columnas del modo comparación se alinean en el mismo eje. |

### Tipos de evento

```python
# backend/eventos.py — modelos Pydantic, uno por tipo

"inicio"          pregunta: str
                  modelo: str
                  desde_cache: bool

"llm_request"     n_llamada: int          # 1-indexado dentro del run
                  mensajes: list[dict]    # rol + contenido, ya recortado a 2000 car.
                  tools_declaradas: list[str]   # [] en N1 y N2

"llm_response"    n_llamada: int
                  texto: str | None
                  hay_tool_calls: bool
                  tokens_in: int
                  tokens_out: int
                  ms: int

"pensamiento"     texto: str              # el "Thought" del ReAct
                  # Solo N4/N5. Ver nota sobre razonamiento explícito abajo.

"ruta"            dominio: str            # 'mantenimiento'|'compras'|'logistica'|'demanda'
                  motivo: str
                  # Exclusivo de N2.

"tool_call"       id_llamada: str         # el call_id del proveedor
                  nombre: str
                  argumentos: dict
                  crudo: str              # ← REQUISITO ADR-002: JSON tal cual
                                          #   lo devolvió el modelo, sin reformatear

"tool_result"     id_llamada: str
                  nombre: str
                  resultado: Any          # serializable
                  filas: int | None       # cuántos registros devolvió
                  ms: int
                  error: str | None

"delegacion"      agente: str             # 'agente_mantenimiento', ...
                  instruccion: str
                  # Exclusivo de N5. Abre un sub-run anidado.

"sub_evento"      agente: str
                  evento: Evento          # anidado, un nivel de profundidad
                  # Exclusivo de N5: la actividad interna del sub-agente.

"respuesta_final" texto: str
                  # Cerrado: exactamente uno por run exitoso.

"metricas"        llamadas_llm: int
                  llamadas_tools: int
                  tokens_in: int
                  tokens_out: int
                  costo_usd: float
                  ms_total: int
                  desde_cache: bool

"aviso"           mensaje: str
                  gravedad: str           # 'info' | 'alerta'
                  # Ej.: "El modelo afirmó una cifra que no consultó" en N1.

"error"           mensaje: str
                  recuperable: bool
                  reintento: int | None

"fin"             estado: str             # 'ok' | 'error' | 'cancelado' | 'tope_excedido'
```

### Invariantes

Verificables, y por lo tanto exigibles en los criterios de aceptación:

1. Todo run DEBE empezar con `inicio` y terminar con `fin`. Sin excepción, incluso al
   fallar.
2. `seq` DEBE ser estrictamente creciente y sin huecos dentro de un run.
3. Todo `tool_call` DEBE tener exactamente un `tool_result` con el mismo
   `id_llamada`, o un `error` que lo referencie.
4. `metricas` DEBE emitirse justo antes de `fin`, siempre — también en error, con lo
   consumido hasta ese punto.
5. `respuesta_final` aparece a lo sumo una vez por run.
6. `ts_ms` DEBE ser monótono no decreciente.
7. Ningún evento DEBE contener la API key, ni fragmentos de ella. `llm_request`
   incluye mensajes; la key nunca viaja en mensajes, pero la serialización DEBE
   filtrar por lista blanca de campos, no por lista negra.
8. **Los `sub_evento` de N5 llevan su propio `seq`, independiente del run padre.** El
   `Evento` anidado en el campo `evento` numera desde 0 dentro de su sub-run, y el
   `sub_evento` que lo envuelve consume un `seq` del run padre. Es decir: hay un
   contador por run y un contador por sub-run, y no se mezclan.
9. **Los invariantes 1 a 7 aplican por separado a cada sub-run.** Cada sub-agente
   produce su propia secuencia `inicio` … `fin` con sus propios pares
   `tool_call`/`tool_result` y sus propias `metricas`. Las `metricas` del run padre son
   la suma de las suyas más las de todos sus sub-runs.
10. La anidación es de **un solo nivel**: un `sub_evento` NO DEBE contener otro
    `sub_evento`. Un sub-agente no delega.

### Verificador del contrato

Los invariantes anteriores están escritos para ser comprobados por máquina, así que
DEBE existir `scripts/verificar_contrato.py` que reciba una traza (del stream, del
caché o de `replay/trazas.json`) y valide los diez, reportando el `seq` exacto donde
falla.

Se ejecuta sobre las trazas de replay antes de cada clase y sobre cualquier traza
sospechosa al depurar. Un contrato declarado verificable y no verificado es solo
prosa — y en la Sesión 6 estas specs se presentan como ejemplo de especificación
válida.

### Caché y fidelidad temporal

Requisito nacido de una contradicción real entre este contrato, la spec 07 y la spec 09:
el valor pedagógico del tablero está en que **N1 termina en un segundo y N5 sigue
trabajando diez segundos después**, mientras el caché —la mitigación principal de la
API key compartida— devuelve en 20 milisegundos y aplana esa asimetría.

Por lo tanto:

1. La entrada de caché DEBE almacenar **la secuencia completa de eventos** del run
   original, con sus `ts_ms` y sus `metricas`, no solo el texto de la respuesta final.
2. Al servir desde caché, los eventos se reemiten **respetando los `ts_ms`
   originales**: el run cacheado tarda en pantalla lo mismo que tardó el real.
3. `metricas` conserva `llamadas_llm`, `tokens_*` y `ms_total` del run original, y
   añade `costo_usd: 0.0` con `desde_cache: true`.
4. `inicio` y `metricas` llevan `desde_cache: true`, y el tablero lo declara con una
   marca visible.

Con esto, caché y demo dejan de estar enfrentados: una ejecución cacheada se ve
idéntica a una real —incluida la asimetría entre columnas—, no cuesta nada y se declara
como lo que es. Es la misma mecánica del modo replay, aplicada por pregunta.

`CACHE_ACTIVO=false` sigue existiendo para demostrar ejecución real, pero deja de ser
necesario para que la demo enseñe lo que debe enseñar.

### Nota sobre `pensamiento`

El campo `pensamiento` corresponde al *Thought* del patrón ReAct de la sección 6.1
del ebook. Con los modelos actuales de tool calling, el razonamiento previo a la
acción **no siempre viene como texto separado**: el modelo puede emitir directamente
la tool call sin verbalizar.

Implicación honesta para la clase: N4 DEBE pedir en su system prompt que el modelo
explicite una frase corta de razonamiento antes de actuar, y el tablero DEBE mostrar
`pensamiento` como *vacío* cuando no lo haya, en lugar de fabricarlo. Presentar un
"Thought" inventado por la UI sería enseñar mal el patrón. Si el modelo no razonó en
voz alta, se dice.

---

## 2. Contrato de tools

### Reglas generales

- Toda tool DEBE ser una función Python síncrona, con anotaciones de tipo completas y
  docstring en español. **La docstring es el prompt que ve el modelo** — se escribe
  para el modelo, no para el desarrollador. Esto se enuncia explícitamente en el
  notebook: es una de las lecciones prácticas del nivel 3.
- Toda tool DEBE devolver un `dict` serializable a JSON. Nunca un DataFrame, nunca un
  objeto.
- Toda tool DEBE manejar el caso "sin resultados" devolviendo estructura vacía con un
  campo `mensaje` explicativo, **nunca** lanzando excepción. Un agente sabe recuperarse
  de "no encontré datos"; no sabe recuperarse de un stack trace.
- Toda tool DEBE limitar su salida a un máximo de filas (`LIMITE_FILAS = 50`) e
  indicar `truncado: bool`. Volcar 2000 filas al contexto es el error clásico.
- Ninguna tool DEBE escribir en la base de datos.

### Catálogo

| Tool | Parámetros | Devuelve |
|---|---|---|
| `consultar_inventario` | `planta: str`, `materia_prima: str \| None` | `{planta, fecha_corte, items: [{materia_prima, cantidad_ton, stock_minimo_ton, bajo_minimo}], truncado}` |
| `consultar_demanda` | `planta: str`, `dias: int = 7`, `producto: str \| None`, `materia_prima: str \| None` | `{planta, periodo, total_ton, promedio_dia_ton, serie: [...], truncado, requerimiento_materia_prima?}` |
| `consultar_produccion` | `planta: str`, `dias: int = 7` | `{planta, periodo, total_ton, paradas_min, utilizacion_pct, serie, truncado}` |
| `estado_pedido` | `numero: str` | `{numero, cliente, planta, producto, toneladas, estado, pasos_restantes, turno_muelle, posicion_en_cola, fecha_promesa, eta_estimada}` |
| `turnos_muelle` | `planta: str`, `fecha: str \| None` | `{planta, fecha, cola: [{turno, pedido, placa, hora_asignada, estado}], en_cola, truncado}` |
| `historial_fallas` | `equipo_id: str \| None`, `planta: str \| None`, `dias: int = 90` | `{alcance, ordenes: [...], total, horas_paro_total, mtbf_dias, truncado}` |
| `lecturas_sensor` | `equipo_id: str`, `variable: str`, `horas: int = 168` | `{equipo_id, variable, n_lecturas, minimo, maximo, promedio, tendencia, serie, truncado}` |

`planta` DEBE aceptar tanto el id (`PL-ITG`) como el nombre o el municipio
(`Itagüí`), resolviendo de forma tolerante. Un agente escribe "Itagüí" porque así lo
dijo el usuario; una tool que exige el id exacto produce un ciclo de error inútil que
gasta tokens y confunde en la demo.

**Tolerante con la forma, estricta con la identidad.** La primera implementación
resolvía «la planta de Cali» —que no existe— a la primera planta del catálogo, porque
la palabra «planta» coincide con todas. Devolvía datos de otro sitio sin avisar, y de
paso rompía la demo de cierre de N4, que consiste precisamente en preguntar por una
planta inexistente y mostrar que el agente dice que no encontró nada. Si ninguna
palabra significativa coincide, la resolución DEBE devolver nada: inventar una
coincidencia es peor que no encontrarla.

### `materia_prima` en `consultar_demanda`

La demanda viene en toneladas de PRODUCTO TERMINADO; el inventario, en toneladas de
MATERIA PRIMA. Compararlas directamente es un error de unidades que además invierte la
conclusión. Con el parámetro `materia_prima`, la tool convierte usando la tabla
`formulas` y devuelve `requerimiento_materia_prima` con el detalle por producto.

La conversión la hace la tool, no el modelo, por la misma razón que `tendencia`: **la
tool calcula, el modelo razona.** Y la docstring DEBE decirle al modelo explícitamente
que no haga la conversión por su cuenta.

### `eta_estimada` en `estado_pedido`

**DEBE tener una fórmula explícita y determinista.** Una tool que devuelve una fecha
estimada inventada, dentro del laboratorio cuya tesis es que inventar datos operativos
es el problema, sería contradecir la clase con el propio código.

```
eta_estimada = max(fecha_promesa, ahora + posicion_en_cola × tiempo_medio_cargue)

donde tiempo_medio_cargue = mediana de (hora_cargue_real − hora_asignada)
                            sobre los despachos cerrados de esa planta
```

La tool DEBE devolver además `base_calculo` con los dos insumos
(`posicion_en_cola`, `tiempo_medio_cargue_min`), para que la estimación sea auditable
y el agente pueda explicarla. Si no hay despachos cerrados suficientes para la mediana
(< 5), `eta_estimada` es `null` y `base_calculo.motivo` lo explica. **Devolver `null` es
correcto; devolver una cifra sin sustento no.**

### `tendencia` en `lecturas_sensor`

DEBE calcularse con la pendiente de una regresión lineal simple y reportarse como
`{"pendiente": float, "unidad": str, "direccion": "creciente"|"estable"|"decreciente",
"n_puntos": int}`.

**Se calcula sobre la serie completa del período solicitado, no sobre las 50 filas
truncadas.** El truncado aplica únicamente a lo que viaja al contexto del modelo; el
cálculo usa todas las lecturas. Con 7.200 lecturas en la base, calcular la tendencia
sobre una muestra de 50 daría un resultado distinto y podría invertir la conclusión del
caso de mantenimiento.

`n_puntos` DEBE reportar cuántas lecturas entraron al cálculo, precisamente para que se
vea que fueron más que las devueltas. Es el ejemplo canónico de **la tool calcula, el
modelo razona**: el agente concluye sobre la falla del equipo sin hacer aritmética sobre
miles de puntos.

### `ejecutar_sql` (alcance ampliado, `PUEDE`)

Escape hatch para el reto `[NÚCLEO]`. Si se implementa, DEBE cumplir **todas**:

1. Solo sentencias que empiecen por `SELECT` o `WITH`, tras normalizar espacios.
2. Rechazo por lista negra de tokens: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
   `ATTACH`, `PRAGMA`, `CREATE`, `REPLACE`, `;` múltiple.
3. Conexión abierta en modo URI solo lectura (`file:...?mode=ro`).
4. `LIMIT 50` forzado si la consulta no trae uno.
5. Timeout de 5 segundos.
6. La consulta ejecutada DEBE quedar registrada en el evento `tool_result`.

Las capas 1–3 son redundantes a propósito: la validación por texto de SQL generado
por un LLM es frágil, y la garantía real es la conexión de solo lectura. Esto se
discute en clase — es el primer contacto del grupo con la idea de que **la tool es
la superficie de ataque del agente**, que se desarrolla en la Sesión 7.

---

## 3. Contrato de API HTTP

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/` | Frontend |
| `GET` | `/api/salud` | `{modo, modelo, key_presente, gasto_usd, tope_usd, cache_activo, version}` |
| `GET` | `/api/niveles` | Metadatos de los 5 niveles: `{id, nombre, estrellas, patron, descripcion, tools}` |
| `GET` | `/api/preguntas` | Catálogo de preguntas precargadas, agrupadas por dominio |
| `GET` | `/api/esquema` | Esquema de `bios_ops.db` con conteo de filas por tabla |
| `GET` | `/api/prompts` | System prompts vigentes de los 5 niveles |
| `PUT` | `/api/prompts/{nivel}` | Reemplaza el system prompt en runtime. Sin persistencia. |
| `POST` | `/api/prompts/reset` | Restaura los prompts originales |
| `POST` | `/api/ejecutar` | `{pregunta, niveles: [...]}` → `{run_id}`. No bloquea. |
| `GET` | `/api/stream/{run_id}` | SSE con el stream de eventos |
| `POST` | `/api/cancelar/{run_id}` | Cancelación cooperativa |
| `GET` | `/api/gasto` | `{gasto_usd, tope_usd, por_nivel: {...}, llamadas_totales}` |

### Detalles

- `POST /api/ejecutar` con varios niveles los ejecuta **concurrentemente**, respetando
  `MAX_CONCURRENCIA`. Los eventos de todos llegan intercalados por el mismo stream y
  se separan por el campo `nivel`.
- `GET /api/stream/{run_id}` DEBE emitir un comentario SSE de keep-alive (`: ping`)
  cada 15 segundos. Sin esto, un proxy corporativo puede cortar la conexión en medio
  de la demo.
- El endpoint de streaming DEBE tolerar la reconexión de `EventSource` reenviando
  desde `seq` si el cliente manda `Last-Event-ID`.
- `PUT /api/prompts/{nivel}` es deliberadamente sin autenticación y sin persistencia:
  es una herramienta de demo en una red de sala. Se documenta como tal en el README,
  con la advertencia de no exponer el puerto fuera de la red local.

### OpenAPI

FastAPI genera el esquema automáticamente en `/docs`. Los modelos Pydantic de
`eventos.py` DEBEN estar registrados como respuesta del stream para que el esquema
sirva de documentación real del contrato. En la Sesión 6 este OpenAPI se usa como
ejemplo de "especificación que un LLM puede implementar y validar".
