# 08 · Guion del facilitador — Clase 2

Guion minuto a minuto de la Sesión 2: **"Cómo se construye un Agente de IA"**.
**90 minutos reservados** (con gap), **~80 min de ejecución**, en tres partes:
1a transparente, 1b framework, 2 n8n.

## Cómo usar este documento

Cada bloque trae cuatro columnas:

| Marca | Significado |
|---|---|
| 🖥 **Proyectas** | Qué está en pantalla en ese momento |
| 🗣 **Dices** | Lo que hay que decir. Entre comillas va literal; el resto es intención. |
| 👀 **Vigilas** | Qué mirar en el grupo para saber si vas bien |
| ⏱ **Corte** | El minuto en que se avanza, terminado o no |

**La regla del reloj sigue siendo la que rige.** Si a los 25 minutos no estás
donde dice el guion, ya sabés que hay que aplicar un corte.

---

## Montaje — 5 minutos antes de empezar

Antes de que el bloque arranque, con el grupo entrando:

- [ ] `agente-transparente/` abierto en VS Code con los 6 archivos visibles en
      el explorador lateral: `cliente`, `tools`, `memoria`, `loop`, `agente`,
      `chat`. Fuente del editor al 18-20pt (legible desde el fondo).
- [ ] Terminal abierta en la carpeta `agente-transparente/`, con la fuente
      agrandada. **El `.env` y la base ya cargados** (checklist spec 07).
- [ ] `agente-framework/agente.py` abierto en otra pestaña de VS Code, listo
      para mostrar lado a lado con `loop.py` en el minuto 46.
- [ ] Navegador con el workflow del n8n de Bios ya abierto en otra pestaña
      (login hecho, lista para cambiar con Cmd/Ctrl+Tab en el min 53).
- [ ] Zoom del navegador y del editor al 125% verificado desde el fondo.
- [ ] Conversación insignia corrida completa 24-48h antes (checklist spec 07).

> **Si el checklist spec 07 no se cumplió, no arrancás.** Una falla de
> preparación no es material didáctico; es la única falla que no se puede
> improvisar en clase.

---

## Minuto 0–8 · Recap + dónde estamos

🖥 Diapositiva de apertura: el mapa "prototipo → funcional → datos → agéntico"
de Bios. Marcá "hoy: funcional". Una segunda diapositiva con el arco:
**S1 "qué es un agente" → S2 "cómo se construye un agente"**.

🗣

> «La clase pasada vimos qué es un agente de IA, sus niveles de agencia y las
> arquitecturas multiagente. Hoy damos el siguiente paso: vamos a **construir
> uno**, pieza por pieza, en código y en n8n. Y ya de paso, le vamos a montar
> la memoria. Al final del bloque van a poder señalar dónde está cada
> componente de un agente —el cerebro, las herramientas, la memoria, el
> loop— en los dos medios.»

Dudas de la clase 1 (máximo 5 minutos, anuncio del reloj: *"corto y boto,
las dudas largas las agarro después"*).

👀 **Vigilas:** que el grupo recuerde el ciclo ReAct
(Thought → Action → Observation). Si nobody remembers, **no insistas**: lo
van a reconstruir a los ojos en el min 30.

⏱ **Corte: minuto 8.**

---

## Minuto 8–46 · Parte 1a · El agente pieza por pieza (a mano)

**El bloque más largo y más densso.** Vas a abrir los seis archivos en orden,
proyectar las 5-6 líneas que encarnan el concepto, y ejecutar. **No escribís
código en vivo.** El repo ya está.

### Minuto 8–13 · `cliente.py` — el cerebro

🖥 Abrí `agente-transparente/cliente.py`. Proyectá las ~10 líneas que
instancian `AzureChatOpenAI`.

🗣

> «Este archivo entero es **el cerebro** del agente. Trece líneas. Toma
> tres variables de entorno —endpoint, key, deployment— y devuelve un
> objeto `cliente` que ya sabe hablar con Azure. Si mañana Bios cambia de
> proveedor, cambias este archivo y nada más.»

Señalá el `.env` sin abrirlo:

> «La configuración vive en `.env`, que no tocamos y nunca debe ir al git.
> Azure OpenAI es la puerta que Bios ya tienen abierta corporativamente;
> por eso usamos Azure y no OpenAI directo.»

👀 **Vigilas:** si alguien pregunta *"¿y con OpenAI normal?"* —contestás en
una frase: *"sí, mismo código cambiando el import y dos variables. La
abstracción vive en `cliente.py`, no en el agente."*

⏱ **Corte: minuto 13.**

### Minuto 13–21 · `tools.py` — los brazos

🖥 Abrí `agente-transparente/tools.py`. **No recorras todo el archivo.**
Mostrá los tres bloques que importan:

1. **Las 4 funciones** (líneas con `def consultar_inventario(...)` etc.).
2. **La docstring de `consultar_inventario`** —leéla en voz alta.
3. **`SCHEMAS`** —el JSON que el modelo realmente ve.

🗣

> «Estas son las **herramientas** del agente —los brazos. Cuatro funciones:
> inventario, demanda, estado de pedido, historial de fallas. Una por dominio
> de BIOS.»

> «Miren la docstring de `consultar_inventario`. Esto **no** es
> documentación para el desarrollador; esto es **lo que ve el modelo**. Si el
> agente no usa una herramienta, casi siempre la culpa es de esta docstring.
> Es un prompt, no un comentario.»

> «Y acá abajo está `SCHEMAS`: el JSON. Al LLM no le pasamos Python. Le
> pasamos esto. Cada tool es nombre + descripción + parámetros. Es el
> contrato que vimos en la clase 1, en código.»

**Ejecutá una tool sola** (sin agente):

```bash
cd agente-transparente
python -c "from tools import consultar_inventario; import json; print(json.dumps(consultar_inventario('Itagüí', 'maíz'), ensure_ascii=False, indent=1))"
```

> «Sin agente, sin LLM. Directamente la función contra la base. trecientos
> veinte toneladas, bajo el mínimo. Este es el dato real; el agente va a
> acercárselo al modelo.»

👀 **Vigilas:** que alguien del núcleo asienta con la cabeza cuando decís
"la docstring es un prompt". Si nadie hace nada, marcá: *"esta es la lección
más útil que se van a llevar hoy."*

⏱ **Corte: minuto 21.**

### Minuto 21–26 · `memoria.py` — la memoria

🖥 Abrí `agente-transparente/memoria.py`. La clase `Memoria`.

🗣

> «Acá está la **memoria** del agente. Cincuenta líneas. Y miren: es una
> lista de mensajes. Eso es todo. Cuando alguien les diga que un agente
> "tiene memoria", piensen en esto: una lista de mensajes que se pasa al LLM
> en cada llamada. Nada más.»

Señalá `agregar` y `mensajes`:

> «`agregar` mete un mensaje; `mensajes` los devuelve. En la próxima vuelta
> del loop, ese método se lo pasa al LLM. La memoria **es** el historial.
> Si cerzás el script, se pierde. Tendría que conectarse a una base Redis o
> SQLite para persistir; eso es tema de producción, lo vemos en el
> acompañamiento.»

👀 **Vigilas:** si algien pregunta *"¿y para qué sirve una memoria que se
pierde?"* —contestás: *"para que el agente use el contexto del turno
anterior. La persistencia es un problema distinto y lo resolveremos más
adelante."*

⏱ **Corte: minuto 26.**

### Minuto 26–35 · `loop.py` — el ciclo ReAct

🖥 Abrí `agente-transparente/loop.py`. **Esto es el corazón de la clase.**

🗣 (lento, marcando cada cosa con el cursor)

> «Este archivo es **lo que un agente hace, sin abstracción**. Lo escribo
> para que se vea. Ellos lo escribirían a mano; un framework lo empaqueta.
> Vamos a recorrerlo.»

**Recorré las partes (no te pierdas; son las 4-5 claves):**

1. `memoria.agregar("user", pregunta)` — entra la pregunta.
2. `cliente.bind_tools(SCHEMAS)` — le adjuntamos los schemas.
3. `llm.invoke(memoria.mensajes())` — la llamada al LLM.
4. `tool_calls = msg.tool_calls` — **decisión del agente: qué hacer.**
5. El `for tc in tool_calls` — **acción**: `dispatch(...)`.
6. La `Observation` que se imprime.
7. `memoria.agregar("tool", json.dumps(resultado), tool_call_id=tc["id"])`.
8. La iteración vuelve arriba.
9. El bloque `if not tool_calls` — **respuesta final**.

> «Esto que ven —decide, ejecuta, observa, decide de nuevo— es ReAct.
> Pensamiento, acción, observación. Exactamente el ciclo del ebook de la
> clase pasada. Acá está, en treinta líneas de Python.»

**Ejecutá el primer turno de la conversación insignia en vivo:**

```bash
python chat.py
# y escribí:
# ¿Cuánto maíz le queda a la planta de Itagüí?
```

Narrá lo que se va imprimiendo mientras pasa:

> «Miren: ya decidió que necesita `consultar_inventario`. Llamó la función.
> Vio la observación: tresientos veinte toneladas, bajo mínimo. Ahora
> decide si ya respondió o si necesita otra tool. En este caso no, cierra.»

👀 **Vigilas:** que alguien reaccione —es el momento donde la teoría de la
clase 1 se vuelve concreta. Si el grupo se queda plano, **pará 5 segundos** y
preguntá:

> «¿Esto es lo mismo que vimos en el ebook? — Es lo mismo. La diferencia es
> que ahora lo están viendo correr.»

⏱ **Corte: minuto 35.**

### Minuto 35–40 · `agente.py` — ensamblar

🖥 Abrí `agente-transparente/agente.py`.

🗣

> «El `AgenteReAct` es la composición: cliente + memoria + tools + loop. Lo
> único que hace `preguntar` es llamar a `react(cliente, memoria, pregunta)` —
> el loop que vimos recién. Es poca escritura y mucha comprensión. Acá está
> el system prompt también: la identidad del agente. Lean la regla de oro:
> "NUNCA inventes una cifra operativa". Es la salvaguarda más barata.»

Leé SYSTEM_PROMPT en voz alta.

⏱ **Corte: minuto 40.**

### Minuto 40–46 · `chat.py` y los 4 turnos completos

🖥 Corré el resto de la conversación insignia en el terminal.

```bash
# continuar con:
# ¿Y me alcanza para la demanda proyectada de esta semana?
# ¿Hay algún equipo de esa misma planta en riesgo de falla?
# ¿Cómo va el pedido PD-24-00871?
```

🗣 (narrando mientras el agente va trabajando)

> «Miren el turno 2. No le repito "Itagüí" ni "maíz". ¿De dónde los saca?
> De la memoria. Esa es la lección de hoy sobre memoria: no es un oráculo,
> es el historial.»

> «Miren el turno 3: cambia de dominio. En vez de inventario, llama
> `historial_fallas`. Decidió solo.»

> «Turno 4: el pedido PD-24-00871 está en muelle, en cola turno 6. La
> interfaz tipo aeropuerto que Bios quiere construir es **este nivel de
> agencia bien hecho** — ya lo decíamos en la clase 1.»

👀 **Vigilas:** el turno 2 es el crítico. Si el agente repite "no tengo
información" o necesita que repitas la planta, **la memoria falló**. En el
chequeo de 24-48h esto tenía que estar resuelto; si pasa en vivo, decí

> «Esto va a pasar en sus proyectos. Acaba de fallar la memoria. Casi
> siempre es el system prompt o el orden de los mensajes. Lo revisamos en
> el break.»

…y seguís con el turno 3.

⏱ **Corte: minuto 46.** (Si no llegaste a los 4 turnos, dejás los pendientes
para el min 78; el teach moment es el encadenamiento, no el conteo.)

---

## Minuto 46–53 · Parte 1b · El MISMO agente con framework

🖥 **Abrí los dos archivos lado a lado en VS Code:**
- Izquierda: `agente-transparente/loop.py` (130 líneas)
- Derecha: `agente-framework/agente.py` (3 líneas efectivas)

🗣

> «Volvimos al punto de partida. Miren la pantalla. A la izquierda está el
> loop que escribimos a mano —130 líneas. A la derecha, el **mismo** agente
> con framework.»

Señalá con el cursor las tres líneas de `create_react_agent`:

> «Tres líneas. Y el agente que se construye acá hace exactamente lo mismo:
>Thought, Action, Observation, próxima iteración. ¿Cómo? Por qué
> `cliente.py`, `tools.py` y `memoria.py` son **idénticos** en las dos
> carpetas. Lo único que cambió es `agente.py`.»

> **«El framework no es mágia. Es lo que escribimos a mano, empaquetado.»**

**Corré el primer turno** de la conversación con el agente framework:

```bash
cd ../agente-framework
python chat.py
# ¿Cuánto maíz le queda a la planta de Itagüí?
```

> «Misma pregunta, misma respuesta. La traza del framework es menos
> parlanchina —uno no ve el `[Thought]`/`[Action]` a menos que lo
> habilite— pero está haciendo lo mismo.»

👀 **Vigilas:** alguien del núcleo tipicamente quiere discutir
*"¿y por qué no siempre framework?"*. Respuesta corta:

> «El framework abstrae. Cuando querés control fino —reintentos custom,
> logging artesanal,북극 decisiones about the loop— escribís a mano. Cuando
> querés velocidad, framework. Esa decisión es de arquitectura y la vamos
> a visitar en sus proyectos reales.»

⏱ **Corte: minuto 53.** Cambio de pantalla a navegador.

---

## Minuto 53–78 · Parte 2 · El mismo agente en n8n

🖥 Cambiá a la pestaña del navegador con el n8n de Bios. El workflow
"Agente Bios ReAct" ya abierto, listo.

🗣

> «Cambiamos de medio. En Python armamos el agente en archivos. En n8n, en
> nodos. **Es el mismo agente**, con los mismos cuatro dominios, contra la
> misma base. Lo que cambia es la forma —lo visual— no el concepto.»

### Minuto 53–55 · Trigger

Señalá el nodo Trigger (chat input).

> «Esto es el input: el mensaje del usuario. En Python era `input()` en
> `chat.py`. Acá es un nodo.»

### Minuto 55–61 · AI Agent + Azure OpenAI

Señalá el nodo **AI Agent** y, dentro, la credencial Azure.

> «El cerebro. Igual que `cliente.py` instanciaba `AzureChatOpenAI`, este
> nodo llama al modelo. Y miren: tiene dos cosas pegadas —memoria y tools—.
> Vamos a verlas.»

Señalá la credencial Azure OpenAI:

> «Esta credencial ya está registrada en n8n de Bios. Es el `.env` de
> Python —la misma info, configurada por TI. Ustedes no la tocan; solo la
> usan.»

### Minuto 61–65 · Window Buffer Memory

Abrí el nodo **Window Buffer Memory**.

> «La memoria. Igual que `memoria.py` era una lista de mensajes, este nodo
> mantiene una ventana de los últimos turnos. Configuro un `sessionId` y
> un tamaño de ventana —acá 10 turnos.» YMLS

> «Idea: si en su proyecto el cliente quiere que el agente recuerde una
> conversación que tuvo la semana pasada, **este mismo nodo** se conecta a
> una base de datos en vez del buffer en memoria. Pero la abstracción es la
> misma: un identificador de sesión y un almacenamiento.»

### Minuto 65–73 · Cuatro nodos Tool

Abrí cada nodo Tool uno por uno: `consultar_inventario`,
`consultar_demanda`, `estado_pedido`, `historial_fallas`.

Por cada uno, **señalá el campo Description** que tiene la misma docstring de
la Parte 1a:

> «Y este es el campo `Description`. Miren qué dice: "Consulta el inventario
> de materias primas de una planta al último corte…". Es la misma docstring
> que vieron en `tools.py`. En Python era el docstring; acá es este campo.
> **Es lo que ve el modelo.** El concepto es el mismo.»

> «Y abajo, los `Parameters`. Es el mismo JSON de `SCHEMAS`. Idéntico.»

### Minuto 73–78 · Ejecución en vivo

**Ejecutá el turno 1 de la conversación insignia** desde el chat del n8n.

> «"¿Cuánto maíz le queda a la planta de Itagüí?"»

Esperá. Cuando llegue la respuesta:

> «"Tresientos veinte toneladas, bajo el mínimo." Misma respuesta, mismo
> número. En Python y en n8n. **El agente es el mismo. El concepto vive
> independiente del medio.**»

👀 **Vigilas:** si la ejecución tarda mucho, narrá lo que está pasando
(el nodo AI Agent está esperando Azure). No dejes el grupo en silencio.

⏱ **Corte: minuto 78.**

---

## Minuto 78–90 · Puesta en común + puente

🖥 Diapositiva de cierre con la **tabla de equivalencias** (spec 06),
proyectada al lado de la última traza de n8n.

| Concepto | Python transparente | Python framework | n8n |
|---|---|---|---|
| Cerebro | `AzureChatOpenAI` | ídem | nodo Azure OpenAI |
| Tools | funciones `tools.py` | ídem | nodos Tool |
| Prompt de tool | docstring | ídem | campo Description |
| Memoria | `Memoria` clase | ídem | nodo Window Buffer Memory |
| Loop ReAct | `loop.py` a mano | `create_react_agent` | nodo AI Agent |
| Interfaz | `chat.py` | ídem | nodo Trigger |

🗣

> «Miren la tabla. El agente es el mismo en los tres. Lo que eligieron en
> su proyecto es una decisión de medio, no de concepto. Si lo entienden en
> uno, lo entienden en el otro.»

### Recapitulá los cinco conceptos (60 segundos)

> «Hoy construimos un agente. Cinco piezas:
> 1. **El cerebro** — un LLM, en este caso Azure OpenAI de Bios.
> 2. **Las tools** — cuatro, una por dominio.
> 3. **La memoria** — los turnos anteriores, pasados otra vez al LLM.
> 4. **El loop ReAct** — decide, actúa, observa, repite.
> 5. **La interfaz** — terminal o n8n; indiferente.»

### Puente a S3 (60 segundos)

> «La próxima clase su agente va a leer documentos. Hoy el agente consulta
> una base estructurada — tablas, cifras ordenadas. La siguiente capacidad
> es "leer y contestar sobre un manual de operaciones, una política, un
> contrato". Eso es **RAG** — Retrieval-Augmented Generation. No se tira
> nada de lo que vimos hoy: lo extendemos.»

### Cierre + entregable

> «Para la próxima clase: abrí el repo. Recorré `loop.py` —es la pieza
> clave. Cuando lo entiendas, sabés cómo se construye un agente. El
> `COMO-MONTARLO.md` te guía paso a paso para correrlo en tu máquina.»

> «El equipo de TI les va a dar acceso al repo en los próximos días; los
> que quieran, ya pueden probar el workflow del n8n hoy mismo desde su
> navegador.»

⏱ **Cierre del bloque: minuto 90.**

---

## Preguntas que van a hacer

Previsibles. Tener la respuesta lista evita improvisar mal.

| Pregunta | Respuesta corta |
|---|---|
| «¿Y si uso OpenAI normal y no Azure?» | Cambiás `cliente.py` (3 líneas) y nada más. Demostración de por qué aislamos el cliente. |
| «¿Puedo conectarlo a SAP / al ERP?» | Sí — una tool es una función. En `tools.py` reemplazás la consulta SQLite por una API de SAP. El loop, la memoria y el cerebro no se tocan. |
| «¿El `.env` es seguro?» | Sí, **si** no va al git y no se pega en ningún chat. Está en `.gitignore`. Si se te escapa, rotás la key en Azure al instante. |
| «¿Cuánto cuesta correr esto en producción?» | Depende del nivel de agencia y del volumen. Hoy medimos: la conversación insignia es ~8-12 llamadas al modelo. Con caching (tema del acompañamiento) baja un orden de magnitud. |
| «¿Por qué LangGraph y no CrewAI / AutoGen?» | Elegimos por continuidad con el ecosistema LangChain (cliente Azure, tools). El concepto es el mismo en cualquiera: el framework abstrae el loop. La elección de framework es de proyecto. |
| «¿N8n escala para producción?» | Sí, con cuidado: hay que configurar colas y workers. Lo vemos cuando llegue el proyecto real de cada uno. |
| «¿Esto es RAG?» | No. RAG es lectura semántica de documentos —la próxima clase. Hoy el agente consulta **datos estructurados** por función. |
| «¿El agente se puede equivocar y dar un dato falso?» | Sí —si triggeó una tool pero alucinó. Por eso el system prompt prohíbe inventar; por eso cią tool devuelve el dato (no el modelo). Si lo hace, ajustá el system prompt o la docstring. |
| «¿Cómo sé si el agente se equivocó?» | Hoy, leyendo la traza. Eso no escala —y es justamente por lo que la clase 7 del acompañamiento (observabilidad) existe. |

Las dos últimas conviene que salgan. Si nadie las hace, plántalas tú.

---

## Cuando algo falla en vivo

| Qué pasa | Qué haces | Qué dices |
|---|---|---|
| Azure cae en medio de Parte 1a | El `try/except` del loop atrapa el fallo y el agente responde "no pude completar" | «Esto va a pasar en sus proyectos también: Azure se cae. Miren: el agente no se murió, informó. Eso es manejo de errores.» |
| Azure caído sistematimente | Plan C (transcripción pre-armada, marcándola como grabada) | «Se nos cayó Azure. Lo que sigue es la ejecución esperada, pre-grabada. Lo mismo que correrían ustedes, en otro momento.» **Nunca lo present como vivo.** |
| El agente inventa una cifra | Edita el system prompt en `agente.py` y vuelve a ejecutar | «Miren: ajustamos una línea de prompt y responde distinto. El comportamiento del agente vive en el prompt; eso es control.» |
| El agente ignora la tool | Lo mismo: ajustar la docstring en `tools.py` o el prompt | «Fíjense: si el agente no usa la tool, la culpable es la docstring. Es un prompt y se trata como tal.» |
| n8n no carga | Cambio a la transcripción + capturas (preparadas per spec 07) | «La instancia de n8n se nos cayó; tenemos capturas de la ejecución de hace dos días.» |
| Una persona no puede correr el repo | Le decís: «mira la demo, reproduce después con COMO-MONTARLO.md» | «Si no te anda, no te preocupes: el repo te queda y el .md te lleva paso a paso. Hoy seguimos mirando.» |
| El grupo pregunta por algo que no tenés pre-armado | «Lo anoto y lo cubrimos en acompañamiento» | — |

---

**El principio general (el mismo de la clase 1):** en una clase sobre cómo
construir agentes, casi cualquier fallo es material didáctico —un fallo de
Azure enseña manejo de errores, una alucinación enseña prompting, una tool
ignorada enseña docstrings. **El único fallo que no lo es es un fallo de
preparación vuestra** —y para eso está el checklist de la spec 07.