# 10 · Guion del facilitador

Guion minuto a minuto del bloque de hands-on de la Sesión 1: **55 minutos, cinco
niveles, 13 líneas de código escritas por el participante.**

## Cómo usar este documento

Cada bloque trae cuatro columnas de información:

| Marca | Significado |
|---|---|
| 🖥 **Proyectas** | Qué está en pantalla en ese momento |
| 🗣 **Dices** | Lo que hay que decir. Entre comillas va literal; el resto es intención. |
| 👀 **Vigilas** | Qué mirar en el grupo para saber si vas bien |
| ⏱ **Corte** | El minuto en que se avanza, terminado o no |

No es un libreto para leer. Son las anclas: si a los 25 minutos no estás donde dice el
guion, ya sabes que hay que aplicar un corte.

**La regla que hace funcionar todo esto:** el reloj decide, no el orgullo. Es más fácil
sostenerlo si lo anuncias al comienzo, y por eso el minuto 0 lo dice en voz alta.

---

## Montaje — 5 minutos antes de empezar

> **El tablero abre en modo «Paso a paso», y así debe quedarse hasta el cierre.** Un
> nivel a la vez, con su diagrama encendiéndose. La vista de comparación —las cinco
> columnas en paralelo— se guarda para el minuto 51: es excelente para cerrar y
> imposible de narrar mientras explicas.
>
> En cada nivel tienes tres cosas que señalar sin tener que recordarlas: el diagrama
> que avanza, la pareja «lo que pidió el modelo / lo que devolvió la herramienta», y el
> panel *qué observar* que aparece al terminar y está escrito para leerse en voz alta.


Antes de que el bloque arranque, con el grupo entrando:

- [ ] Tablero abierto en `localhost:8000`, **modo comparación**, indicador en `● vivo`
- [ ] Notebook abierto en otra pestaña, en la Sección 0 ya ejecutada
- [ ] Ebook de la clase abierto en la **sección 7.2** (el JSON de `get_weather`) — se
      usa en el minuto 18 y no quieres buscarlo en vivo
- [ ] Zoom del navegador al 125–150%, verificado desde el fondo del salón
- [ ] Barra de gasto visible y en cero
- [ ] Segunda pantalla o portátil con el `docker compose logs -f tablero` corriendo, por
      si hay que diagnosticar sin cambiar lo que proyectas

---

## Minuto 0–4 · N1 · El LLM inventa ☆☆☆

**Objetivo:** que el grupo vea con sus ojos que un LLM sin herramientas fabrica datos
operativos. Es el minuto que justifica los 51 restantes.

🖥 Tablero, modo comparación, solo la casilla **N1** marcada.

🗣 Abre con la regla del reloj, en 20 segundos:

> «Vamos a construir cinco agentes en 55 minutos. Cada uno más autónomo que el
> anterior. Escriben trece líneas de código en total: el resto está hecho, porque lo
> que quiero que se lleven es el criterio, no la mecanografía. Y una cosa: cada nivel
> tiene una celda de rescate. Si se traban, la ejecutan y siguen. Nadie se queda atrás
> por un error de sintaxis.»

Luego haz clic en el chip **Inventario vs demanda** y ejecuta solo N1. Mientras carga:

> «Este es el nivel cero de agencia. Un LLM, sin herramientas, sin acceso a nada.
> Le estoy preguntando por el inventario de maíz de una planta.»

Cuando responda, **no la leas tú.** Pregunta al grupo:

> «¿Alguien me lee la cifra que dio?»

Que la lea alguien en voz alta. Después abre en el tablero el valor real de la base
(vista Detalle o la consulta directa) y ponlos lado a lado.

> «El dato real es 318 toneladas. Él dijo 450. Y fíjense en cómo lo dijo: con
> seguridad, con unidades, con formato de reporte. Esto es lo que va a pasar cada vez
> que un modelo no tenga de dónde leer y alguien le haga una pregunta operativa.»

👀 **Vigilas:** que alguien se ría o levante las cejas. Si el grupo se queda plano, es
que no cayó el peso — insiste: *«esto es lo que hoy le estamos pidiendo a ChatGPT en
media empresa»*.

⏱ **Corte: minuto 4.** No debates aquí. La conversación sobre alucinaciones vuelve en el
cierre, cuando ya tengan con qué compararla.

### Si el modelo NO inventa

Ocurre, y hay que estar listo. Dos caminos, los dos sirven:

**Camino A — se niega** («no tengo acceso a los datos de inventario»):

> «Miren, se portó bien. Y aun así, es inútil para la operación: no puede responder la
> pregunta más básica que le haría un jefe de planta. Un modelo honesto sin
> herramientas sigue siendo un modelo sin herramientas.»

Y entonces presiona:

> «Vamos a ver qué pasa si insisto un poco.»

Edita el prompt en la vista Detalle añadiendo *«estima un valor típico para una planta
de 620 toneladas por día»* y vuelve a ejecutar. Casi siempre produce la cifra. Si la
produce, tienes el momento original y además una lección extra sobre lo frágiles que
son las salvaguardas por prompt.

**Camino B — responde con un rango vago** («entre 300 y 600 toneladas»):

> «Dio un rango. ¿Alguien firmaría una orden de compra con esto?»

El regex del tablero puede no dispararse con estas redacciones. Usa el botón
**«marcar como afirmación sin fuente»** de la columna de N1 para emitir el aviso a mano.

---

## Minuto 4–11 · N2 · Enrutador ★☆☆

**Objetivo:** que vean el LLM como **decisor**, no como generador de texto. Es el cambio
mental que abre la puerta a los agentes.

🖥 Cambian al **notebook**, Sección 2.

🗣

> «Segundo nivel. Aquí el modelo ya decide algo: a qué dominio pertenece la pregunta.
> Mantenimiento, compras, logística o demanda. Pero no ejecuta nada. Solo elige un
> camino. Son dos líneas: el modelo Pydantic de la salida.»

Deja 4 minutos para que escriban las dos líneas. Cuando la mayoría haya corrido:

> «Fíjense en algo importante: no parseamos texto. Le pedimos al modelo que responda
> con una estructura. Eso se llama salida estructurada y lo vamos a usar todo el
> programa. Es la diferencia entre esperar que el modelo escriba bien y **obligarlo**.»

Luego el momento clave del nivel — la pregunta ambigua. Proyecta:

> «Ahora miren esto: le voy a preguntar *"el pedido de la avícola no llegó y creo que
> el molino está parado"*. ¿Qué debería contestar?»

Enruta a un solo dominio. Y ahí:

> «Tuvo que elegir uno, y perdió la mitad del problema. Guárdense esto: al final de la
> clase vamos a resolverlo con el nivel 5.»

👀 **Vigilas:** que nadie esté todavía peleando con la Sección 0. Si alguien lo está,
mándalo a la celda de rescate ahora, no en el minuto 25.

⏱ **Corte: minuto 11.** Anúncialo: *«voy a avanzar, el que no terminó ejecuta la celda de
rescate»*.

---

## Minuto 11–25 · N3 · Llamador de herramientas ★★☆

**El bloque más importante de la clase.** Dos momentos: el JSON crudo y el límite de una
sola ronda.

🖥 Notebook, Sección 3.

🗣

> «Tercer nivel: el cerebro con brazos. Le damos herramientas y él decide cuál usar. Y
> vamos a escribir el ciclo a mano, sin framework, porque quiero que vean exactamente
> qué pasa. Cuatro líneas: el bloque que ejecuta la herramienta y le devuelve el
> resultado al modelo.»

Deja 7–8 minutos. Circula por las mesas — este es el bloque donde los cuatro del núcleo
se ganan el sueldo desbloqueando a su mesa.

### Minuto ~18 · El JSON crudo

Cuando la mayoría tenga N3 corriendo, para todo y proyecta el tablero en vista Detalle,
nivel N3, con el evento `tool_call` expandido.

Al lado, el ebook abierto en la sección 7.2.

> «Miren la pantalla y miren el documento. Esto es lo mismo. Esto que ven acá —`name`,
> `arguments`— es literalmente lo único que el modelo produce. No ejecuta nada. Genera
> un texto que dice *"quiero llamar a esta función con estos parámetros"*, y nuestro
> código lo obedece. Function calling es esto y no es más que esto.»

Es el momento en que la teoría de la mañana se vuelve concreta. Dale 60 segundos de
silencio para que lo miren.

### Minuto ~22 · El límite

> «Ahora la parte interesante. ¿Qué preguntamos? *¿Cuánto maíz queda y me alcanza para
> la demanda?* ¿Qué contestó?»

Contestó el inventario. **No comparó contra la demanda.**

> «Está correcto. Y está incompleto. Consultó el inventario y respondió. ¿Por qué no
> consultó la demanda también?»

Deja que lo digan ellos. La respuesta que buscas es *«porque solo le dimos un turno»*.

> «Exacto. Nuestro código lo llama, ejecuta una herramienta, y responde. Punto. Le falta
> una sola cosa. ¿Cuál?»

Y que alguien diga **iterar**.

> «Eso es el nivel cuatro.»

👀 **Vigilas:** si a los 20 minutos menos de la mitad tiene N3 corriendo, tienes un
problema de ritmo. Salta directo al momento del JSON crudo con tu propia pantalla y
manda a todos a la celda de rescate.

⏱ **Corte: minuto 25.** Firme. Este es el checkpoint impreso en el notebook.

---

## Minuto 25–39 · N4 · ReAct ★★★

**Objetivo:** ver el encadenamiento autónomo y entender qué abstrae el framework.

🖥 Notebook, Sección 4.

🗣

> «Nivel cuatro: le agregamos un ciclo. Piensa, actúa, observa lo que pasó, y decide si
> sigue o responde. Ese patrón se llama ReAct y es el default para la mayoría de agentes
> que van a construir. Tres líneas, porque LangGraph nos da el ciclo hecho.»

Deja 7 minutos.

### Minuto ~33 · La comparación de código

Proyecta el código de N3 al lado del de N4.

> «Sesenta líneas contra quince. Misma capacidad, más el ciclo. ¿Qué se llevó
> `create_react_agent`? Exactamente lo que escribimos a mano hace diez minutos: llamar
> al modelo, ver si pidió herramientas, ejecutarlas, devolver el resultado, repetir. Por
> eso lo escribimos a mano primero. Si no, esto es magia.»

### Minuto ~36 · El encadenamiento

Vuelve al tablero, ejecuta N4 con la pregunta insignia.

> «Nadie le dijo que consultara dos tablas. Consultó inventario, consultó demanda,
> comparó, y concluyó que **no alcanza y faltan 40 toneladas**. Eso no es buscar un dato:
> es responder una pregunta.»

Y de inmediato el contrapeso:

> «Ahora miren el pie de la columna. Cinco llamadas al modelo. N3 hacía dos.»

### Minuto ~38 · Cierre del arco de N1

Treinta segundos, pero no los omitas: es el cierre del arco que abrió el minuto 0.

> «Una última cosa. Le voy a preguntar por el inventario de una planta que no existe.»

La herramienta devuelve vacío y el agente lo reporta.

> «No inventó. Dijo que no encontró datos. Compárenlo con el nivel uno. La diferencia
> entre inventar y decir "no sé" no la puso un prompt: la puso una herramienta.»

⏱ **Corte: minuto 39.**

### 🔴 Punto de decisión — minuto 35

Si a los 35 minutos **menos de la mitad del grupo tiene N4 corriendo**, aplica la
válvula de escape de la spec 01. En voz alta, sin drama:

> «Vamos a hacer un cambio. El nivel cinco lo voy a mostrar yo en el tablero, y ustedes
> se lo llevan como ejercicio para la próxima sesión. Prefiero que los cuatro que ya
> tienen queden sólidos que cinco a medias.»

Nadie lo vive como un fracaso si lo presentas como una decisión, no como una disculpa.

---

## Minuto 39–51 · N5 · Supervisor multiagente ★★★★

**Objetivo:** ver un agente delegando en otros, y entender cuándo eso se justifica.

🖥 Notebook, Sección 5.

🗣

> «Último nivel. Y la buena noticia: ya lo tienen casi hecho. Van a tomar su ReAct del
> nivel cuatro, crear dos copias con prompts distintos y herramientas distintas —uno de
> abastecimiento, otro de operaciones—, y envolver cada uno en una función. Porque un
> agente expuesto como herramienta **es solo una función que por dentro llama a un
> agente**. Y esas dos funciones se las damos a un tercer agente. Cuatro líneas.»

Deja 7 minutos.

### Minuto ~48 · La pregunta cruzada

Tablero, chip **Cruzada**, N5.

> «Acuérdense del nivel dos, cuando pregunté por el pedido y el molino y tuvo que elegir
> un solo dominio. Misma pregunta.»

El supervisor delega en los dos sub-agentes y sintetiza.

> «Consultó a los dos y diagnosticó: el retraso es materia prima, no equipos. Un agente
> le preguntó a otros dos agentes.»

### Minuto ~50 · La factura

**No te saltes esto. Es la conclusión de la sesión.**

Vista comparación, las cinco columnas de la misma pregunta.

> «Once llamadas al modelo. N4 hacía cinco. Treinta veces el costo de N1 para la misma
> pregunta. Entonces la pregunta de diseño no es *"qué tan agéntico puedo hacerlo"*, es
> *"qué tan agéntico necesito que sea"*.»

⏱ **Corte: minuto 51.**

---

## Minuto 51–55 · Cierre

🖥 Tablero, modo comparación, tabla de las cinco columnas con **los números reales de
esta clase**.

🗣 Recorre la última fila de la tabla de la spec 05:

> «Miren la fila de abajo. Clasificar texto: nivel dos. Consulta puntual: nivel tres.
> Análisis que cruza fuentes: nivel cuatro. Dominios separados de verdad: nivel cinco.
> Y fíjense en el chip de logística: *¿dónde está mi pedido?* se resuelve en nivel tres.
> No necesita un multiagente. La interfaz tipo aeropuerto que quieren construir es un
> nivel tres bien hecho.»

Y entonces el entregable, en 60 segundos:

> «Para la próxima sesión: la sección 6 del notebook. Escriban la herramienta que su
> proyecto necesita. Una pregunta real que hoy nadie pueda responder rápido, la función
> que la responde, y la docstring. Y presten atención al paso 5: si el agente **ignora**
> su herramienta, la culpable es la docstring. Esa docstring es un prompt, no un
> comentario. Es probablemente lo más útil que se van a llevar de hoy.»

Cierre:

> «La próxima sesión estos agentes van a tener memoria y van a leer documentos de
> verdad. Nada de lo que escribieron hoy se tira.»

---

## Preguntas que van a hacer

Previsibles. Tener la respuesta lista evita improvisar mal.

| Pregunta | Respuesta corta |
|---|---|
| «¿Por qué este modelo y no el más grande?» | Porque la diferencia entre los cinco niveles es **arquitectónica**, no de capacidad del modelo. Un modelo pequeño lo demuestra igual y cuesta menos. Elegir modelo según la tarea es tema de la Sesión 5. |
| «¿Esto es RAG?» | No. Aquí el agente consulta datos estructurados por función. RAG es búsqueda semántica sobre documentos, y es la Sesión 2. |
| «¿Y N8N, dónde entra?» | Como orquestador de bajo código para prototipar flujos entre sesiones. El agente puede ser un paso dentro de un flujo de N8N o al revés. |
| «¿Puedo conectarlo a SAP / al ERP?» | Sí, es una herramienta más: una función que consulta y devuelve un dict. Integración con sistemas legacy es un módulo de follow-up. |
| «¿Cuánto costaría esto en producción?» | Depende del nivel de agencia y del volumen — y lo acabamos de medir: la diferencia entre nivel 3 y nivel 5 es de un orden de magnitud. Con esa tabla ya pueden estimar. Control de costos es Sesión 5. |
| «¿Cómo sé si el agente se equivocó?» | Hoy: leyendo la traza. Eso no escala, y es exactamente por eso que existen las sesiones 5 y 7 (evals y observabilidad). |
| «¿Podemos usar nuestros datos reales?» | No en esta sesión, y la razón es concreta: todo lo que una herramienta devuelve se envía al proveedor del modelo. Antes hay que definir contrato de tratamiento y clasificación de la información. Sesiones 2 y 7. |
| «¿No es peligroso darle acceso a la base?» | Muy buena pregunta, y por eso aquí es **solo lectura**. Cada herramienta que le dan a un agente es una capacidad que un prompt malicioso puede intentar usar. Sesión 7. |

Las dos últimas conviene que salgan. Si nadie las hace, plántalas tú.

---

## Cuando algo falla en vivo

| Qué pasa | Qué haces | Qué dices |
|---|---|---|
| Errores `429` | El sistema reintenta solo; los reintentos se ven en la traza | «Miren esto: estamos quince personas contra una sola API key. Esto es rate limiting, y el manejo de reintentos es parte de llevar un agente a producción.» Convierte el fallo en contenido. |
| Aparece el banner de replay | No lo ocultes | «Se nos agotó el presupuesto / la API está lenta, así que lo que sigue son trazas grabadas. Es real, pero grabado.» **Nunca lo presentes como vivo.** |
| Un nivel se cuelga | Botón *Detener* y sigue con el tablero | — |
| Una herramienta falla | Déjala fallar y mira cómo el agente reacciona | «Esto es oro: vean cómo se recupera de un error de herramienta. Un agente que no maneja errores no sirve en producción.» |
| El notebook no le funciona a alguien | Celda de rescate, y sigue | «Ejecuta la celda de rescate y me buscas en el break.» No detengas a 14 personas por una. |
| Docker roto en tu máquina | Plan C: `uvicorn` local (README §8) | — |

**El principio general:** en una clase sobre agentes, casi cualquier fallo es material
didáctico. El único que no lo es es un fallo tuyo de preparación — y para eso está el
checklist de la spec 09.
