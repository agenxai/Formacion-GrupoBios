# 07 · Frontend — el Tablero de Agencia

## Principio de diseño

**No es un chat. Es un instrumento de observación.**

La tentación es construir una interfaz de conversación bonita. Sería un error: en un
chat, todo el trabajo del agente queda invisible y lo único que se ve es el resultado
—exactamente lo contrario del objetivo de la sesión—. Aquí el resultado es lo *menos*
interesante; lo que enseña es el proceso.

Regla que resuelve las dudas de diseño: **si un elemento no revela algo del
funcionamiento interno del agente, no va.**

Segunda regla: **se proyecta**. Todo se diseña para leerse desde la última fila del
salón. Mínimo 14 px, contrastes medidos, sin información crítica en gris claro.

## Vistas

**Tres**, conmutables por pestañas en el encabezado. La predeterminada es *Paso a
paso*.

### Por qué se agregó "Paso a paso" después de construir el tablero

La primera versión abría en modo comparación, y al proyectarla quedó claro que la
vista que mejor cierra la sesión es la peor para explicarla: **cinco columnas
avanzando a la vez no se pueden narrar.** El facilitador no puede señalar qué está
pasando en N3 mientras N5 se mueve al lado, y el grupo mira cinco cosas y no sigue
ninguna.

Así que hay un modo para explicar y un modo para comparar, y no son el mismo:

| Vista | Para qué | Cuándo |
|---|---|---|
| **Paso a paso** | Un nivel a la vez, con su diagrama de arquitectura encendiéndose conforme corre | Los bloques de N1 a N5, minutos 0–51 |
| **Comparación** | Los cinco en paralelo, con la tabla de cierre | El cierre, minutos 51–55 |
| **Detalle** | Traza completa y system prompt editable | Cuando alguien pregunta «¿y si…?» |

### Vista · Paso a paso (la predeterminada)

Por nivel: el patrón de código en grande, *qué hace* / *qué NO hace* / *cuándo
usarlo*, el **diagrama de arquitectura**, la traza en vivo con cada llamada a
herramienta junto a su respuesta, y un panel *qué observar* que aparece al terminar.
Navegación con «Siguiente nivel →», y al final «Ver los cinco juntos».

#### El diagrama: la traza ocurriendo SOBRE el dibujo

No es una ilustración al lado de la traza. Es un **SVG por el que viaja la petición**:
cada evento manda un paquete etiquetado a recorrer la arista que le corresponde, así
que se ve entrar la pregunta al modelo, salir el `tool_call` hacia la herramienta,
volver el dato y salir la respuesta.

Cuatro cosas distintas viajan, y se distinguen a simple vista por color y etiqueta:

| Paquete | Qué es | Ejemplo de etiqueta |
|---|---|---|
| `peticion` (teal) | lo que entra | «la pregunta» |
| `decision` (teal claro) | una elección del modelo | «ruta: compras», «instrucción» |
| `tool` (ámbar) | la llamada a una herramienta | «consultar_inventario» |
| `resultado` (lima) | el dato que vuelve | «datos reales», «observación» |
| `respuesta` (verde) | lo que sale | «la respuesta» |

Lo que cada nivel muestra por sí solo, sin que el facilitador tenga que explicarlo:

- **N1** — dos flechas y nada en el medio. No hay a dónde ir a buscar un dato.
- **N2** — cuatro caminos dibujados, **tres quedan tenues** y uno se enciende. Eso es,
  visualmente, la información que el enrutador tuvo que tirar.
- **N3** — una línea recta: pregunta → modelo → herramienta → modelo → respuesta. Se
  ve que no hay forma de volver a consultar.
- **N4** — el mismo dibujo de N3 **más una flecha que vuelve por debajo**. El paquete
  de resultado la recorre hacia atrás una vez por iteración: se pueden contar las
  vueltas en pantalla.
- **N5** — el supervisor reparte instrucciones y recibe diagnósticos, y sobre cada
  agente **destella 🔧 con el nombre de la herramienta** que usó por dentro. Dice «cada
  uno es un ReAct completo» sin dibujar catorce herramientas alrededor.

Debajo del lienzo, la **narración numerada**: los mismos pasos en palabras, para poder
señalarlos cuando los paquetes ya pasaron. Y un botón **↻ Repetir animación** que
reproduce el flujo grabado **respetando los tiempos originales y sin volver a llamar a
la API**. En clase el mismo paso se explica dos y tres veces; que repetirlo sea gratis
es la diferencia entre poder hacerlo y no.

##### Dos decisiones de implementación que no son de gusto

1. **El SVG se genera como cadena y se inyecta con `x-html`**, no con
   `<template x-for>` dentro del `<svg>`. Un `<template>` escrito dentro de `<svg>` se
   crea en el espacio de nombres SVG y **deja de ser un `HTMLTemplateElement`**, así
   que Alpine no lo reconoce y no renderiza nada. El síntoma es un lienzo con las
   flechas y sin ningún nodo, y cuesta un rato de depuración encontrarlo.
2. **La posición de los paquetes la mueve un bucle de `requestAnimationFrame`** usando
   `getPointAtLength` sobre el trazado real de la arista, escribiendo el `transform`
   directamente en el DOM. Reasignar el arreglo de paquetes en cada fotograma
   dispararía el re-render de Alpine sesenta veces por segundo; el arreglo solo se
   reasigna cuando un paquete muere.

#### La activación, en datos

Los diagramas **NO viven en el frontend**: los describe el backend en
`backend/niveles/presentacion.py` y `GET /api/niveles` los entrega. Un diagrama es
conocimiento del nivel —la forma de su arquitectura— y la spec 02 dice que toda
diferencia entre niveles vive del lado del nivel. Consecuencia práctica: agregar un
sexto nivel no obliga a tocar una línea de JavaScript.

Un diagrama son columnas de nodos; el frontend traza los conectores. `activacion`
mapea *tipo de evento* → *plantilla del id del nodo* que se ilumina, con campos del
evento entre llaves:

    "ruta": "{dominio}"             → N2 enciende SOLO el dominio elegido
    "llm_request": "llm{n_llamada}" → N3 distingue la 1ª llamada de la 2ª
    "delegacion": "{agente}"        → N5 enciende el sub-agente al que delegó

Tres estados por nodo: pendiente (punteado gris), en curso (teal, latiendo), hecho
(lima). Y el tipo de nodo se distingue **por forma además de por color** —entrada y
salida redondeadas, decisión inclinada, herramienta con barra lateral— porque los
proyectores desaturan.

Que en N2 queden tres dominios apagados y uno encendido dice de un vistazo lo que un
párrafo tarda en explicar. Y el `bucle` de N4 —una flecha de retorno etiquetada
`while llm_should_continue()`— es literalmente la única diferencia visual con N3, que
es exactamente la lección.

#### La pareja llamada / respuesta

Cada `tool_call` se muestra **junto a su `tool_result`**, lado a lado y sin plegar:

| Izquierda | Derecha |
|---|---|
| 🔧 **Lo que pidió el modelo** — el JSON crudo, con la nota de que el modelo no ejecuta nada, solo dice qué ejecutarías | ↩ **Lo que devolvió la herramienta** — un resumen en una línea legible, más el JSON completo desplegable |

Debajo, la **docstring tal como la ve el modelo**. Las tres piezas juntas son
*function calling* completo en una pantalla: qué pidió, qué recibió y qué texto le
hizo elegir esa herramienta. Ese emparejamiento fue la petición explícita del
facilitador tras la primera prueba, y con razón: sin la respuesta al lado, el JSON de
la llamada es una curiosidad; con ella, es el mecanismo.



### Vista · Comparación (el cierre)

Una pregunta, cinco columnas ejecutando en paralelo.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ [logo Grupo Bios]   Laboratorio · Niveles de Agencia    ▓▓▓░░ $1.42/$10  ● vivo │
│                     ┌──────────────┬───────────┐                                │
│                     │ Comparación  │  Detalle  │                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ¿Cuánto maíz le queda a la planta de Itagüí y me alcanza para la demanda…      │
│  [ Ejecutar ]   niveles: [✓N1][✓N2][✓N3][✓N4][✓N5]                             │
│                                                                                 │
│  Preguntas listas:  ⬡ Inventario vs demanda   ⬡ Equipo con fallas               │
│                     ⬡ ¿Dónde está mi pedido?  ⬡ Pico de demanda                 │
│                     ⬡ Cruzada (dos dominios)                                    │
├──────────┬──────────┬──────────┬──────────┬──────────────────────────────────────┤
│ ☆☆☆ N1   │ ★☆☆ N2   │ ★★☆ N3   │ ★★★ N4   │ ★★★★ N5                              │
│ Procesa. │ Router   │ Tool c.  │ ReAct    │ Supervisor                           │
│ ─────────│──────────│──────────│──────────│──────────────────────────────────────│
│ ● LLM 1  │ ● LLM 1  │ ● LLM 1  │ ● LLM 1  │ ● LLM 1                              │
│ ⚠ afirmó │ ● ruta:  │ ● tool_c │ ● pensó  │ ● delega → agente_abastecimiento     │
│   una    │   compras│   ▾ JSON │ ● tool_c │   ├ ● tool_call inventario           │
│   cifra  │          │ ● result │ ● result │   └ ● tool_call demanda              │
│   sin    │          │ ● LLM 2  │ ● pensó  │ ● delega → agente_operaciones        │
│   fuente │          │          │ ● tool_c │   └ ● tool_call fallas               │
│          │          │          │ ● result │ ● LLM síntesis                       │
│          │          │          │ ● LLM 5  │                                      │
│ ─────────│──────────│──────────│──────────│──────────────────────────────────────│
│ «Aprox.  │ «Corres- │ «Itagüí  │ «No al-  │ «El retraso es por materia prima:    │
│  450 t»  │  ponde a │  tiene   │  canza:  │  Itagüí está 40 t bajo el requeri-   │
│          │  compras»│  320 t»  │  faltan  │  miento; los equipos operan normal»  │
│          │          │          │  ~40 t»  │                                      │
│ ─────────│──────────│──────────│──────────│──────────────────────────────────────│
│ 1 LLM    │ 1 LLM    │ 2 LLM    │ 3 LLM    │ 6 LLM                                │
│ 0 tools  │ 0 tools  │ 1 tool   │ 2 tools  │ 5 tools                              │
│ 1.3 s    │ 1.1 s    │ 2.3 s    │ 6.6 s    │ 7.0 s                                │
│ 156 tok  │ 160 tok  │ 1.9k tok │ 9.7k tok │ 8.1k tok                             │
└──────────┴──────────┴──────────┴──────────┴──────────────────────────────────────┘
                    Qypher · Formación en Inteligencia Artificial
```

Las cifras de la maqueta son de corridas reales con gpt-4o-mini. Nótese que el pie
muestra **tokens**, no solo dólares: con las tarifas sin configurar es la única
métrica honesta, y además es la que de verdad separa a N3 de N4 —que pueden empatar
en número de llamadas y diferir 5× en tokens— porque lo que crece es el contexto.

El valor de esta vista es que las cinco columnas avanzan **a distinta velocidad y en
tiempo real**. N1 y N2 terminan en un segundo; N5 sigue trabajando diez segundos
después. Esa asimetría, vista en vivo, comunica el costo de la agencia mejor que
cualquier tabla.

Requisitos:
- Las columnas DEBEN compartir el eje temporal (`ts_ms` relativo del contrato). Un
  evento a los 3 s en N4 aparece a la misma altura visual que uno a los 3 s en N5.
- La fila de métricas DEBE actualizarse en vivo, no al final.
- El aviso `⚠` de N1 DEBE ser visualmente prominente: es el clímax de la demo.
- Con menos de 5 niveles seleccionados, las columnas se reparten el ancho.

### Vista · Detalle de un nivel

Selector de nivel y, debajo, tres paneles:

1. **System prompt** — en `<textarea>` monoespaciado, **editable**. Botones *Aplicar*
   y *Restaurar*. Es la herramienta más útil del tablero: cuando alguien pregunte «¿y
   si le prohibimos inventar?», se edita, se corre y se ve que N1 sigue fallando.
2. **Traza completa** — todos los eventos, expandibles, con:
   - Mensajes enviados al modelo en cada llamada (el contexto creciendo: se ve por qué
     N4 cuesta más).
   - **JSON crudo** de cada tool call, resaltado, con botón de copiar.
   - Resultado de cada tool, plegado por defecto.
   - Duración por paso.
3. **Tools disponibles** — lista con nombre, firma y docstring tal como la ve el
   modelo. Refuerza la lección: *la docstring es el prompt*.

## Preguntas precargadas

Cinco *chips*, una por anomalía plantada (spec 03) más la cruzada. NO son decorativas:
con API key compartida, los chips maximizan aciertos de caché — quince personas
haciendo clic en el mismo chip cuestan una sola llamada al modelo (spec 09).

| Chip | Pregunta | Dominio | Nivel que la resuelve bien |
|---|---|---|---|
| Inventario vs demanda | ¿Cuánto maíz le queda a la planta de Itagüí y me alcanza para la demanda proyectada de esta semana? | Compras | N4 |
| Equipo con fallas | ¿Cuál equipo de Itagüí está en riesgo de falla y por qué? | Mantenimiento | N4 |
| ¿Dónde está mi pedido? | ¿Dónde está el pedido PD-24-00871 y cuántos turnos le faltan? | Logística | N3 |
| Pico de demanda | ¿Hubo algún día en que la demanda superó la producción y en cuánto? | Producción/TD | N4 |
| Cruzada | El pedido PD-24-00871 va retrasado. ¿Es por falta de materia prima o por un problema de equipos? | Dos dominios | N5 |

La columna "nivel que la resuelve bien" es contenido, no metadata: mostrarla enseña
que **no toda pregunta necesita el nivel más alto**. El chip de logística se resuelve
en N3, y eso es exactamente lo que el Champion de logística necesita oír.

## Encabezado — indicadores de estado

| Indicador | Contenido | Por qué está |
|---|---|---|
| Modo | `● vivo` (teal) / `◐ replay` (alerta) | El facilitador DEBE saber en todo momento si lo que se proyecta es real o pregrabado. Nunca se demuestra replay como si fuera vivo. |
| Gasto | Barra + `$1.42 / $10.00` | Control operativo y didáctico |
| Modelo | nombre del modelo activo | Transparencia; se pregunta siempre |

### La conmutación a replay DEBE ser intrusiva

Con `MODO=auto` (el default), el sistema cae a replay solo ante `429` persistentes o al
tocar el tope de gasto. Un badge que cambia de color **no basta**: el facilitador está
hablando y mirando al grupo, no la esquina de la pantalla. Y entonces dice «miren cómo
el agente decide» sobre una traza grabada — lo que la spec 09 prohíbe expresamente.

Requisito: al conmutar, el tablero DEBE mostrar un **banner del ancho completo del
encabezado**, en `--alerta`, con texto explícito —*«Modo replay: lo que ves a
continuación son trazas pregrabadas, no ejecución real»*— que persiste hasta que se
cierre a mano. Además se emite un evento `aviso` en todos los runs afectados, de modo
que quede en la traza y no solo en la pantalla.

### Cuando el costo no está configurado

Si `PRECIO_ENTRADA_POR_1M` y `PRECIO_SALIDA_POR_1M` valen 0, el pie de columna **NO
DEBE mostrar `$0.00`**. Mostraría en ceros justamente la fila que sostiene la lección de
diseño del laboratorio, sin fallar ni avisar: enseñaría algo falso en silencio.

En ese caso el pie muestra `costo no configurado` y usa **tokens** como métrica
comparativa —que llegan reales de la API—, más el número de llamadas al modelo. La
comparación entre N1 y N5 funciona igual de bien en tokens que en dólares.

### Ejecuciones desde caché

Una columna servida desde caché DEBE verse **idéntica a una real**: los eventos se
reemiten con sus `ts_ms` originales, así que la asimetría de velocidad entre columnas
—el corazón de esta vista— se conserva (ver *Caché y fidelidad temporal*, spec 04).

Se distingue solo por una marca discreta `⚡ caché` junto a las métricas, y su costo se
reporta como `$0.00 (caché)`. Es a la vez honesto y didáctico: la primera vez que
alguien ve que su ejecución fue gratis hay una conversación de 30 segundos sobre
caching que la Sesión 5 retoma formalmente.

## Comportamiento

- **Streaming:** un `EventSource` por run, sobre `/api/stream/{run_id}`. Todos los
  niveles comparten el stream y se separan por el campo `nivel`.
- **Render incremental:** cada evento se agrega al DOM al llegar. No se espera nada.
- **Reconexión:** si el `EventSource` cae, reconecta con `Last-Event-ID` y continúa
  desde el `seq`. Un corte de red no arruina la demo en curso.
- **Cancelación:** botón *Detener* → `POST /api/cancelar/{run_id}`.
- **Sin key:** el tablero arranca igual, en modo replay, con el indicador en
  `◐ replay`. Nunca una pantalla de error como primera impresión.
- **Errores de tool:** se muestran en la traza en `--error` **sin abortar el run**. Un
  agente que se recupera de un error de tool es contenido valioso, no un fallo de la
  demo.

## Accesibilidad y proyección

- Contrastes medidos por `scripts/validar_contraste.py` (spec 06). Sin excepciones.
- El color NUNCA es el único portador de significado: cada estado tiene además su
  marca (`○ ● ✕ ⚠`). Proyectores desaturan y hay daltonismo en cualquier grupo de 15.
- `prefers-reduced-motion` respetado en el pulso de "en curso".
- Navegable por teclado: Tab a los chips, Enter para ejecutar.
- **Zoom hasta 150% sin romper el layout de 5 columnas.** Requisito práctico: es lo
  primero que hace un facilitador cuando alguien del fondo dice que no ve.

## Implementación

- HTML + CSS propio + Alpine.js vendorizado (ADR-004). Sin build, sin Node, sin CDN.
- Un solo `index.html`, un `app.js`, un `estilos.css`. Si `app.js` pasa de ~400
  líneas, la vista está haciendo demasiado — la lógica pertenece al backend.
- Servido por el mismo FastAPI: sin CORS, sin segundo puerto, sin proxy.
