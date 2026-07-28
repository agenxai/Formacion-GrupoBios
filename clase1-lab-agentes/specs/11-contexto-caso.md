# 11 · Contexto del caso — la vista previa a los niveles

**Estado:** `v1.0` — especificada, **pendiente de implementar**. Es la primera spec
escrita después de la v1.0 del laboratorio, y sigue la misma regla del conjunto: se
escribe completa antes del código, y se corregirá donde la implementación demuestre
que está equivocada.

---

## El problema pedagógico

El tablero abre explicando los niveles de agencia, pero el **caso** es invisible. El
grupo ve al agente de N3 llamar `consultar_inventario` sin haber visto nunca la tabla
`inventario_planta`, sin saber qué devuelve esa herramienta, y sin entender por qué la
pregunta del maíz necesita cruzar dos tablas. La progresión N1→N5 enseña *cómo decide
el agente*; el caso enseña *con qué trabaja*. Sin lo segundo, lo primero es abstracto.

En la clase teórica el grupo vio los conceptos —bases de datos, herramientas, function
calling— y al llegar al tablero no los reconoce: los ve *en movimiento* antes de
haberlos visto *quietos*.

Tres síntomas concretos, observados al proyectar:

1. El evento `tool_call` aparece en pantalla y la pregunta del grupo es «¿eso qué
   es?», no «¿por qué el modelo la eligió?». La segunda pregunta es la de la clase;
   la primera es la que la vista actual no responde.
2. La respuesta «320 toneladas» no impresiona como dato real si nunca se vio de qué
   tabla salió. El contraste con la cifra inventada de N1 —el clímax de la demo—
   pierde fuerza.
3. Las cinco preguntas precargadas se sienten caídas del cielo. Nadie entiende aún
   por qué esas cinco y no otras.

## Qué es

Una **cuarta pestaña del tablero, «El caso»**, que se convierte en la **vista inicial
predeterminada**. Antes de cualquier nivel: el escenario, los datos, las herramientas
y las preguntas. Gráfica, proyectable y con **costo cero de API**: nada en esta vista
llama al modelo.

Responde, en orden, las cuatro preguntas que un alumno se hace al llegar:

| Bloque | Pregunta que responde |
|---|---|
| 1 · El escenario | ¿De qué empresa es esto y qué le duele? |
| 2 · Los datos | ¿Qué información hay y dónde vive? |
| 3 · Las herramientas | ¿Qué puede consultar el agente y qué devuelve? |
| 4 · Las preguntas | ¿Qué hay que responder y por qué es difícil? |

Y cierra con la transición: *«¿Cómo responde un LLM a esto? → Nivel 1»*.

## Decisiones cerradas

Tomadas con el dueño del producto antes de escribir esta spec. No se re-litigan
durante la construcción:

- **Pestaña propia, vista inicial.** Cuarta pestaña junto a Paso a paso / Comparación
  / Detalle. El tablero ABRE aquí. No es un paso 0 dentro de Paso a paso: el contexto
  y los niveles son dos momentos distintos y merecen vistas distintas.
- **Las herramientas se ejecutan en vivo.** Cada tool tiene un botón «Probar» que la
  corre contra `bios_ops.db` con argumentos curados y muestra el JSON real. Sin LLM,
  costo $0. El alumno ve el dato real ANTES de ver al agente pedirlo — y cuando N3 lo
  pida en clase, lo reconoce.
- **Las preguntas sí, las respuestas no.** La vista presenta el escenario y las cinco
  preguntas de negocio; las cuatro anomalías NO se revelan ni se interpretan. La
  clase las descubre con los niveles.
- **Diagrama gráfico de la base**, con una línea de texto por tabla que diga qué
  aporta. No tiene que ser un DER formal: tiene que ser entendible desde la última
  fila del salón.

---

## Bloque 1 · El escenario

Texto corto (≤ 120 palabras, la regla de legibilidad de la spec 08) más una franja
gráfica de las cinco plantas.

El texto presenta la ficción del laboratorio: Grupo Bios produce alimentos
balanceados; opera cinco plantas; el equipo de operaciones tiene preguntas que hoy
nadie responde rápido, y los datos existen pero viven en sistemas distintos. Cuatro
dominios —compras, mantenimiento, logística, producción— y cada uno con su pregunta
de trabajo.

La franja de plantas muestra las cinco como tarjetas: nombre, municipio y capacidad
en ton/día, leídas de la base, no escritas a mano. Itagüí va primera, sin destacarla:
no se avisa que es la protagonista de tres de las cinco preguntas.

**El aviso de datos sintéticos (spec 03) DEBE estar en este bloque**, además de la
franja permanente del tablero: es la primera pantalla que ve el grupo, y la regla de
la spec 03 es que el aviso aparezca donde empieza la experiencia. Incluye la nota de
que los municipios son reales y la asignación planta↔municipio es ficticia.

## Bloque 2 · Los datos — el mapa de la base

Un **mapa SVG de las once tablas**, agrupadas por dominio, con el mismo lenguaje
visual de los diagramas de nivel (spec 07): nodos redondeados, teal Bios, conectores
con flecha. Si un elemento no ayuda a entender qué información hay y cómo se
conecta, no va.

### Qué muestra

- **Cuatro grupos por dominio** — compras, mantenimiento, logística, producción —
  más `plantas` en el centro como nodo del que cuelga casi todo. El dominio se
  distingue por etiqueta de texto e icono ADEMÁS de color (spec 06: el color nunca
  es el único portador).
- **Cada tabla es un nodo** con tres datos: su nombre, su **conteo real de filas**
  (leído en vivo de la base) y una línea de **qué aporta**, escrita para un no
  técnico: *«cuánto hay de cada materia prima en cada planta, y el mínimo
  aceptable»*, no *«tabla de hechos de inventario»*.
- **Los conectores son las llaves foráneas**: `ordenes_mantenimiento → equipos`,
  `pedidos → plantas`, etc. Es lo que hace visible la frase de la clase teórica «los
  datos están relacionados»: se ve que el pedido cuelga de la planta y la orden de
  mantenimiento cuelga del equipo.

### De dónde sale — nada se escribe a mano dos veces

- Nombres de tabla, columnas y llaves foráneas se leen de la base misma
  (`PRAGMA table_info`, `PRAGMA foreign_key_list`). **Las relaciones NO se declaran
  en el frontend ni en un diccionario**: se extraen del esquema real. No pueden
  desincronizarse.
- El conteo de filas se calcula en vivo al servir el endpoint. Es la misma cifra de
  `GET /api/esquema`, así que las dos nunca se contradicen.
- Lo único redactado a mano es el `que_aporta` de cada tabla y su asignación de
  dominio, en `backend/db/descripciones.py`. La prueba de humo DEBE verificar que
  cada tabla descrita existe en la base: si alguien renombra una tabla, falla el
  chequeo, no la demo.

### Interacción

Clic en un nodo abre un panel lateral con las columnas (nombre y tipo) y **tres
filas de ejemplo reales**. Las filas de ejemplo se recortan a 80 caracteres por
campo — una celda con un texto largo no debe romper el panel.

El mapa DEBE caber en pantalla a zoom 150% con el panel cerrado. Con el panel
abierto, el mapa se corre, no se tapa ni se encoge por debajo de lo legible.

## Bloque 3 · Las herramientas — vivas, sin agente

Las siete tools de dominio como tarjetas, agrupadas por el mismo dominio del mapa de
datos (así se ve que `historial_fallas` lee las tablas de mantenimiento: la
conexión bloque 2 ↔ bloque 3 es el contenido, no una decoración).

Cada tarjeta muestra, en este orden:

1. **Nombre y firma** — `consultar_inventario(planta, materia_prima=None)`.
2. **La docstring tal como la ve el modelo** (reusa `firmas()` de spec 04). Con la
   nota de una línea: *«este texto es lo que el modelo leerá para decidir si la
   usa — la docstring es el prompt»*. Es la primera siembra de la lección de N3,
   antes de que N3 exista en pantalla.
3. **Un botón «Probar»** por ejemplo curado (uno o dos por tool), con los argumentos
   visibles al lado.

### El botón «Probar»

Ejecuta la tool de verdad contra `bios_ops.db` y muestra debajo de la tarjeta:

- El **JSON real de salida**, con el mismo componente visual que el `tool_result`
  de las trazas (mismo plegado, mismo resaltado).
- Las filas devueltas y los milisegundos que tardó.

Y un rótulo permanente sobre el bloque:

> **Aquí no hay ningún agente corriendo.** Esto es lo que cada herramienta sabe
> devolver. En los niveles vas a ver cómo el agente aprende a pedirlas.

Ese rótulo es contenido: distingue *la capacidad* (la tool) de *la decisión* (el
agente), que es exactamente el salto de N2 a N3.

### Los argumentos son curados y viven en el backend

El frontend NO envía argumentos arbitrarios. Cada ejemplo curado —nombre, argumentos
y una línea de `por_que`— se define en `backend/tools/ejemplos.py`, y el botón pide
«el ejemplo 0 de `consultar_inventario`», no una consulta libre.

Razón: el endpoint no tiene autenticación (spec 09, Riesgo 5). Las tools son de solo
lectura, así que el riesgo real no es de datos sino de **determinismo de la demo**:
argumentos libres producen salidas que nadie revisó, en pantalla, delante del grupo.
La lista blanca de ejemplos es la misma filosofía que la lista blanca de campos del
contrato de eventos: lo que no se previó, no pasa.

Los ejemplos curados usan los identificadores de `db/constantes.py` (la planta de
Itagüí, `PEDIDO_ATASCADO`, `EQUIPO_EN_RIESGO`), así que si el generador cambia,
cambian con él — la misma regla que el catálogo de preguntas.

### Sobre los spoilers en las salidas

Una decisión honesta: si alguien prueba `consultar_inventario` con maíz en Itagüí,
verá «320 t, bajo mínimo». Eso no viola «las respuestas no», por dos razones:

- La tarjeta **no interpreta**: muestra el dato, nunca dice «no alcanza» ni «este
  equipo está fallando». La conclusión es el trabajo de la clase.
- El facilitador elige qué proyectar. La exploración libre la hace cada participante
  en su máquina, y encontrar el dato por uno mismo antes de la demo es preparación,
  no spoiler — es lo que haría un analista nuevo el primer día.

La regla escrita: **la vista muestra datos, nunca conclusiones.**

## Bloque 4 · Las preguntas — sin las respuestas

Las cinco preguntas del catálogo (`backend/preguntas.py`) como tarjetas: el texto de
la pregunta, su dominio, y **qué hay que cruzar para responderla** — «inventario
contra demanda, convirtiendo unidades», «correctivos contra tendencia del sensor».

Dos cosas NO aparecen aquí, a propósito:

- **Las respuestas.** Es la regla de arriba llevada a su fin.
- **El `nivel_que_la_resuelve`.** En las vistas de ejecución ese dato es contenido
  (spec 07); acá sería responder antes de tiempo la pregunta que la clase entera
  existe para formular. En su lugar, cada tarjeta cierra con la misma línea:
  *«¿qué nivel de agente hace falta para responderla? Eso lo decide la clase.»*

El catálogo DEBE ganar un campo `cruza` por pregunta (las tablas o tools que hay que
combinar), redactado a mano en `preguntas.py`. Es lo que conecta este bloque con los
bloques 2 y 3: cada pregunta se puede señalar de vuelta a las tablas y herramientas
que toca.

La pregunta insignia va primera y destacada con la marca «la pregunta de la clase».
Las cinco tarjetas NO ejecutan nada: el botón de ejecutar vive en las vistas de
niveles. Mezclar ejecución en la vista de contexto la convertiría en otro Paso a
paso y diluiría su función.

### La transición

Al pie del bloque, un botón del ancho del contenido:

> **¿Cómo responde un LLM a esto? → Nivel 1: el procesador simple**

Lleva a la vista Paso a paso con N1 seleccionado y la pregunta insignia cargada en
la entrada. Es el puente: del contexto a la demo.

---

## Contrato de API — dos endpoints nuevos

### `GET /api/caso`

Agregado único que la vista pide una sola vez al cargar. Todo lo que muestra el
tablero viene de aquí; el frontend no consulta otra cosa para esta vista.

```json
{
  "aviso_datos": "…",
  "escenario": {
    "titulo": "…",
    "texto": "…",
    "plantas": [{"id": "PL-ITG", "nombre": "Planta Itagüí", "municipio": "Itagüí",
                 "capacidad_ton_dia": 620.0}]
  },
  "tablas": [{
    "id": "inventario_planta",
    "dominio": "compras",
    "que_aporta": "Cuánto hay de cada materia prima en cada planta, y el mínimo aceptable.",
    "conteo": 1200,
    "columnas": [{"nombre": "planta_id", "tipo": "TEXT"}],
    "muestra": [{"planta_id": "PL-ITG", "…": "…"}],
    "referencias": [{"hacia": "plantas", "desde": "planta_id", "campo": "id"}]
  }],
  "herramientas": [{
    "nombre": "consultar_inventario",
    "firma": "consultar_inventario(planta: str, materia_prima: str | None = None) -> dict",
    "docstring": "… tal como la ve el modelo …",
    "dominio": "compras",
    "ejemplos": [{"argumentos": {"planta": "Itagüí", "materia_prima": "maíz"},
                  "por_que": "El dato detrás de la pregunta de la clase, sin agente."}]
  }],
  "preguntas": [{"chip": "Inventario vs demanda", "texto": "…", "dominio": "compras",
                 "cruza": ["inventario_planta", "demanda_historica", "formulas"]}]
}
```

Reglas:

- El agregado se construye en un módulo nuevo, `backend/caso.py`, reusando lo que ya
  existe: `db.conteo_por_tabla`, `tools.operaciones.firmas`, `preguntas.PREGUNTAS`,
  `db.constantes`. **Ningún dato se duplica escribiéndolo a mano en dos sitios.**
- `GET /api/esquema` NO cambia: está documentado en el README y lo usa la sección de
  diagnóstico. `/api/caso` es aditivo.
- La respuesta DEBE servir en menos de 200 ms: es una lectura de SQLite local más
  una introspección de esquema. Si alguna vez pesa, el cuello de botella es el
  diseño, no la red.

### `POST /api/tools/probar`

```json
// Petición
{"herramienta": "consultar_inventario", "ejemplo": 0}
// Respuesta
{"herramienta": "consultar_inventario",
 "argumentos": {"planta": "Itagüí", "materia_prima": "maíz"},
 "resultado": {…},
 "filas": 1,
 "ms": 3}
```

Invariantes — los tres son criterios de aceptación verificables:

1. **Nunca llama al modelo.** No emite eventos, no pasa por `llm.py`, y
   `GET /api/gasto` antes y después de la llamada DEBE ser idéntico.
2. **Nunca escribe en la base.** Usa la misma conexión de solo lectura de las tools
   (spec 04). La hereda, no la redeclara.
3. **Solo ejecuta ejemplos curados.** `herramienta` desconocida → 404; `ejemplo`
   fuera de rango → 404. No existe forma de pasar argumentos arbitrarios.

La tool puede devolver su estructura de «sin resultados» con `mensaje` (spec 04) —
es una salida legítima y se muestra igual. Si la propia tool fallara, el endpoint
responde 500 con el mensaje de la excepción y la tarjeta lo muestra sin romper la
vista. Un fallo aquí se descubre en la prueba de humo, no en clase.

---

## Requisitos visuales

- Todo lo de la spec 06 aplica sin excepción: paleta exacta, contraste validado por
  `scripts/validar_contraste.py`, mínimo 14 px, el color nunca como único portador
  de significado, `prefers-reduced-motion` respetado.
- **Mismo lenguaje visual que los diagramas de nivel.** El mapa de la base y los
  diagramas de N1–N5 son primos: mismos nodos, mismos conectores, misma paleta.
  Cuando en Paso a paso aparezca el diagrama de N3, el grupo debe sentir que el
  modelo y la herramienta del dibujo son los mismos que acaba de ver en El caso.
- **Zoom 150 % sin romper** — la regla del salón (spec 07).
- La lógica de la vista va en un archivo nuevo, `frontend/caso.js`, y sus estilos en
  `frontend/caso.css`. `app.js` ya pasó su presupuesto de ~400 líneas (spec 07); la
  vista nueva no engorda el archivo viejo. El componente de JSON plegado de
  `tool_result` se extrae para reusarlo en ambos — un solo componente, no dos
  copias que se desincronicen.
- Sin dependencias nuevas: mismo Alpine vendorizado, sin build step (ADR-004).

## Momento de uso — dónde entra en la clase

Tres momentos, ninguno consume el presupuesto de 55 minutos de hands-on (spec 01):

1. **El facilitador, al abrir el bloque práctico** (3–5 min proyectados): recorre el
   escenario, el mapa («aquí vive todo lo que van a preguntar»), prueba UNA tool en
   vivo —`consultar_inventario` con maíz en Itagüí— y lee las cinco preguntas en voz
   alta. Después hace clic en la transición a N1 y empieza el guion de la spec 10.
2. **El participante, en el preflight** (spec 09): el checklist gana un ítem —
   «recorrí la pestaña El caso y probé una herramienta». Llegar a clase sabiendo
   qué es `inventario_planta` es la diferencia entre seguir N3 y mirarlo pasar.
3. **Referencia durante la clase**: cuando alguien pregunte «¿y esa tool de dónde
   saca eso?», la respuesta es volver a El caso, no explicarlo de memoria.

### Cambio formal sobre las specs 07 y 10

Hasta hoy el tablero abría en Paso a paso. **Con esta spec, abre en El caso**, y el
montaje del facilitador (spec 10) cambia en una línea: tablero abierto en El caso,
listo para hacer la transición a N1 en el minuto 0. Las specs 07 («tres vistas») y
10 (checklist de montaje) DEBEN recibir su nota de corrección al implementar esta,
con el motivo — la misma honestidad de corrección que el resto del conjunto.

## Criterios de aceptación

Verificables, como manda la costumbre del conjunto:

1. El tablero abre en «El caso» sin ningún clic ni configuración.
2. El mapa muestra las **once** tablas, y cada conteo coincide con
   `GET /api/esquema` en la misma corrida.
3. Cada conector del mapa corresponde a una llave foránea real de la base
   (extraída por `PRAGMA`, no declarada).
4. Las siete tools tienen tarjeta, docstring y al menos un «Probar» funcional.
5. Probar cualquier tool deja `GET /api/gasto` **idéntico** (sin llamadas al
   modelo) y no emite ningún evento del contrato.
6. Probar `consultar_inventario` con el ejemplo curado devuelve la cifra con
   contrato del generador (spec 03: 320 t de maíz en Itagüí).
7. Ninguna tarjeta de pregunta muestra `nivel_que_la_resuelve` ni conclusión
   alguna sobre los datos.
8. El aviso de datos sintéticos es visible sin hacer scroll.
9. `scripts/validar_contraste.py` en verde incluyendo los componentes nuevos.
10. `scripts/prueba_humo.py` ejercita `GET /api/caso` y los siete «Probar», y
    verifica que cada tabla descrita en `descripciones.py` existe en la base.
11. Zoom 150 %: el mapa cabe y la vista no se rompe.

## Fuera de alcance

Se declara para que la vista no crezca:

- **SQL libre o edición de argumentos** en los «Probar». Los ejemplos son curados;
  `ejecutar_sql` sigue siendo territorio del reto `[NÚCLEO]` (spec 04).
- **Ejecutar niveles desde El caso.** La ejecución vive en Paso a paso y
  Comparación.
- **Explicar los niveles.** De eso se encarga Paso a paso; El caso termina en la
  pregunta, no en la respuesta.
- **Edición de datos** de ningún tipo. La base es de solo lectura aquí como en
  todas partes (spec 03).
- **Internacionalización.** Español, como todo el laboratorio.

## Riesgos de esta vista, con su mitigación

| Riesgo | Mitigación |
|---|---|
| Que el contexto se coma la clase | 3–5 minutos proyectados, guionados; el resto es exploración del participante fuera del bloque. Si el tiempo aprieta, el facilitador hace solo la transición y señala la pestaña. |
| Que «Probar» se use de formas no previstas | Solo ejemplos curados del backend. No hay entrada libre. |
| Que las descripciones se desincronicen de la base | Conteos, columnas y relaciones se leen de la base en vivo; lo redactado a mano (un `que_aporta` por tabla) lo valida la prueba de humo. |
| Que la vista revele las anomalías | Muestra datos, nunca conclusiones. Regla escrita en el bloque 3 y criterio 7. |
