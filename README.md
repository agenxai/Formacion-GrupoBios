<p align="center">
  <img src="clase1-lab-agentes/frontend/assets/grupo-bios.png" alt="Grupo Bios" width="260">
</p>

<h1 align="center">Laboratorio · Niveles de Agencia</h1>

<p align="center">
  <strong>Clase 1 — Agentes de IA y Arquitecturas Multiagénticas</strong><br>
  Formación en Inteligencia Artificial para Grupo Bios · Programa Qypher<br>
  <em>Python · LangGraph · FastAPI · Docker</em>
</p>

---

## Qué es esto

Un laboratorio para **construir el mismo agente cinco veces**, subiendo un nivel de
agencia cada vez, sobre datos de operaciones de una planta.

| Nivel | Qué hace | Agencia |
|---|---|---|
| **N1** Procesador simple | Responde con el LLM, sin herramientas. **Inventa las cifras.** | ☆☆☆ |
| **N2** Enrutador | Clasifica la pregunta en un dominio. No ejecuta nada. | ★☆☆ |
| **N3** Llamador de herramientas | Llama una herramienta y responde. Una sola ronda. | ★★☆ |
| **N4** Agente multipasos (ReAct) | Encadena varias herramientas hasta resolver. | ★★★ |
| **N5** Supervisor multiagente | Delega en dos sub-agentes especializados y sintetiza. | ★★★★ |

Se responde siempre la misma pregunta, para que la diferencia entre niveles se vea sin
cambiar de ejemplo:

> *«¿Cuánto maíz le queda a la planta de Itagüí y me alcanza para la demanda proyectada
> de esta semana?»*

N1 la inventa. N2 solo la clasifica. N3 la responde a medias. N4 la responde bien. N5
la cruza con otro dominio.

### Los dos artefactos

| | Qué es | Dónde | Para qué |
|---|---|---|---|
| **Tablero de Agencia** | App web que ejecuta los 5 niveles en paralelo y muestra sus trazas | `localhost:8000` | Ver por dentro qué hace cada nivel |
| **Notebook explicado** | Los 5 niveles en Python plano, sin abstracciones | `localhost:8888` | Leer el código y entenderlo |

> **Aviso sobre los datos.** Todo el contenido de `bios_ops.db` es **sintético**,
> generado por script. Los nombres de plantas, productos, equipos y clientes son
> **ficticios** y no representan la red de operaciones ni los clientes de Grupo Bios.
> Ningún dato real de la compañía se procesa en este laboratorio.

---

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Inicio rápido](#2-inicio-rápido)
3. [Variables de entorno](#3-variables-de-entorno)
4. [Verificar que quedó bien](#4-verificar-que-quedó-bien)
5. [Cómo usar el tablero](#5-cómo-usar-el-tablero)
6. [Cómo usar los notebooks](#6-cómo-usar-los-notebooks)
7. [Sin API key: modo replay](#7-sin-api-key-modo-replay)
8. [Ejecutar sin Docker](#8-ejecutar-sin-docker)
9. [Comandos útiles](#9-comandos-útiles)
10. [Solución de problemas](#10-solución-de-problemas)
11. [Seguridad: lo que no debes hacer](#11-seguridad-lo-que-no-debes-hacer)
12. [Estructura del repositorio](#12-estructura-del-repositorio)
13. [Checklist antes de la clase](#13-checklist-antes-de-la-clase)
14. [Qué sigue](#14-qué-sigue)

---

## 1. Requisitos previos

Solo dos cosas. **No necesitas instalar Python, LangGraph ni nada más**: todo corre
dentro de Docker.

| Herramienta | Versión mínima | Cómo obtenerla |
|---|---|---|
| **Docker** | 24.0 | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS/Windows) o `docker` + `docker-compose-plugin` (Linux) |
| **Git** | cualquiera | Preinstalado en macOS/Linux. En Windows: [git-scm.com](https://git-scm.com/) |

Y **una API key de OpenAI** (sección 3). Sin ella el laboratorio funciona igual, en
modo replay (sección 7).

### Verifica que Docker está listo

```bash
docker --version          # Docker version 24.x o superior
docker compose version    # v2.x — OJO: "docker compose", con espacio
docker info               # debe responder sin error
```

Si `docker info` falla con *«Cannot connect to the Docker daemon»*, Docker Desktop no
está corriendo. Ábrelo y espera a que el icono deje de animarse.

> **Nota para Windows:** usa **WSL2** como backend de Docker Desktop (es el default
> desde hace años). Clona el repo **dentro** del sistema de archivos de Linux
> (`\\wsl$\Ubuntu\home\tu-usuario\`), no en `C:\Users\...`. Clonarlo en la ruta de
> Windows hace que el montaje de volúmenes sea entre 5 y 10 veces más lento y Jupyter
> tarda una eternidad en abrir.

> **Nota para Apple Silicon (M1/M2/M3/M4):** funciona sin configuración extra. Las
> imágenes se construyen para `arm64` nativamente.

**Espacio en disco:** ~1.5 GB para las imágenes.

---

## 2. Inicio rápido

Cinco comandos. Si todo va bien, en unos 3 minutos tienes el laboratorio corriendo.

```bash
# 1 · Clonar y entrar
git clone <URL-DEL-REPOSITORIO>
cd clase1-lab-agentes

# 2 · Crear tu archivo de configuración a partir de la plantilla
cp .env.example .env

# 3 · Editar .env y pegar tu API key en OPENAI_API_KEY
#     (con el editor que prefieras: nano, vim, code, notepad)
nano .env

# 4 · Construir y levantar
docker compose up --build

# 5 · Abrir en el navegador
#     Tablero  → http://localhost:8000
#     Notebook → http://localhost:8888
```

La primera vez, el paso 4 tarda entre 2 y 5 minutos: descarga la imagen base, instala
las dependencias y **genera la base de datos sintética**. Las siguientes veces arranca
en segundos.

Cuando esté listo verás en la terminal:

```
tablero   | ✓ bios_ops.db  11 tablas · 12.497 filas
tablero   | ✓ modo: vivo   modelo: gpt-4o-mini   key: presente
tablero   | INFO:     Uvicorn running on http://0.0.0.0:8000
notebook  | [I ...] Jupyter Server is running at:
notebook  | [I ...] http://localhost:8888/lab
```

Para dejarlo corriendo en segundo plano y recuperar la terminal:

```bash
docker compose up -d --build
```

Para detenerlo:

```bash
docker compose down
```

---

## 3. Variables de entorno

Toda la configuración vive en un archivo `.env` en la raíz del proyecto. **Ese archivo
no está en el repositorio** (está en `.gitignore`, a propósito): lo creas tú a partir de
`.env.example`.

```bash
cp .env.example .env
```

### Conseguir la API key

1. Entra a **https://platform.openai.com/api-keys**
2. *Create new secret key*
3. Cópiala completa (empieza por `sk-`). **Solo se muestra una vez.**
4. Pégala en `.env`:

```bash
OPENAI_API_KEY=sk-proj-tu-key-real-aqui
```

> **Si están usando una key compartida del equipo:** te la entregan por un canal
> seguro (gestor de contraseñas o mensaje directo), **nunca por un chat de grupo ni
> por correo**. Y revisa el ajuste `MAX_CONCURRENCIA` más abajo: es lo que evita que
> 15 personas ejecutando al mismo tiempo tumben la key con errores 429.

### Referencia completa

| Variable | Default | Qué hace |
|---|---|---|
| `OPENAI_API_KEY` | — | Tu key. Sin ella, arranca en modo replay. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo de los 5 niveles. ⚠ Confirma cuáles están habilitados en tu cuenta. |
| `MODELO_SUPERVISOR` | *(vacío)* | Modelo solo para el supervisor de N5. Vacío = el mismo. |
| `MODO` | `auto` | `vivo` \| `replay` \| `auto` (vivo si hay key y presupuesto; si no, replay). |
| `TOPE_USD` | `10.00` | Gasto máximo. Al alcanzarlo conmuta a replay y avisa; no se cae. |
| `MAX_CONCURRENCIA` | `4` | Llamadas simultáneas a la API. Protege una key compartida. |
| `CACHE_ACTIVO` | `true` | Caché en disco. 15 personas con la misma pregunta = 1 llamada. |
| `PRECIO_ENTRADA_POR_1M` | `0.00` | ⚠ Tarifa por millón de tokens de entrada. **Verifícala** en los precios de OpenAI. |
| `PRECIO_SALIDA_POR_1M` | `0.00` | ⚠ Ídem, de salida. Con ambas en 0 el tablero **no** muestra `$0.00`: dice «costo no configurado» y compara por tokens. |
| `SEMILLA_DATOS` | `42` | Semilla del generador. Fija = base idéntica en todas las máquinas. |
| `FECHA_REFERENCIA` | *(hoy)* | `YYYY-MM-DD` desde donde se generan los datos hacia atrás. |
| `PUERTO_TABLERO` | `8000` | Cámbialo si ya lo tienes ocupado. |
| `PUERTO_NOTEBOOK` | `8888` | Ídem. |

### Después de cambiar `.env`

Reinicia los servicios para que tomen los valores nuevos:

```bash
docker compose restart
```

Si cambiaste `SEMILLA_DATOS` o `FECHA_REFERENCIA`, hay que **regenerar la base**
(sección 9) porque los datos ya no corresponden.

---

## 4. Verificar que quedó bien

Tres comprobaciones, de la más rápida a la más completa.

### a) El backend responde

```bash
curl -s http://localhost:8000/api/salud | python3 -m json.tool
```

```json
{
  "modo": "vivo",
  "modelo": "gpt-4o-mini",
  "key_presente": true,
  "gasto_usd": 0.0,
  "tope_usd": 10.0,
  "cache_activo": true,
  "version": "1.0.0"
}
```

Lo importante: `key_presente: true` y `modo: "vivo"`. Si dice `"replay"`, la key no se
está leyendo — ve a la sección 10.

### b) El tablero se ve

Abre **http://localhost:8000**. Debes ver el logo de Grupo Bios arriba a la izquierda,
el indicador `● vivo` a la derecha, y la vista **El caso** con el escenario, el mapa
de las once tablas y las herramientas con su botón ▶ Probar.

### c) El notebook está listo

Abre **http://localhost:8888**, abre `2-los-cinco-niveles-taller.ipynb`, y ejecuta las celdas
de la **Sección 0 · Preparación**. La última imprime:

```
✓ Python 3.12.x
✓ langgraph 0.x.y
✓ bios_ops.db  (11 tablas, 12.497 filas)
✓ OPENAI_API_KEY presente
✓ Conectividad con la API: 240 ms
→ Todo listo. Puedes empezar por la sección 1.
```

**Si esas tres comprobaciones pasan, estás listo.** Esto es exactamente lo que hay que
haber corrido antes de la clase (sección 13).

---

## 5. Cómo usar el tablero

**http://localhost:8000**

No es un chat: es un instrumento para ver el interior de un agente. El resultado es lo
menos interesante; lo que enseña es el proceso.

Hay **cuatro vistas**, y la elección importa: la que mejor cierra la sesión es la peor
para explicarla.

| Vista | Para qué | Cuándo |
|---|---|---|
| **El caso** *(predeterminada)* | El contexto del ejercicio: el escenario, el mapa de la base, las herramientas en vivo y las preguntas | Antes de empezar los niveles; referencia durante la clase |
| **Paso a paso** | Un nivel a la vez, con su diagrama de arquitectura encendiéndose conforme corre | Mientras explicas cada nivel |
| **Comparación** | Los cinco en paralelo + tabla de cierre | El cierre |
| **Detalle** | Traza completa y system prompt editable | Cuando alguien pregunta «¿y si…?» |

### Vista El caso — el contexto antes de los niveles

El tablero abre aquí, a propósito: antes de ver al agente *usar* las herramientas,
hay que haberlas visto. Cuatro bloques, y **ninguna llamada al modelo** en toda la
vista:

1. **El escenario** — la ficción del laboratorio: cinco plantas, cuatro dominios,
   y las preguntas que nadie responde rápido.
2. **Los datos** — un mapa de las once tablas agrupadas por dominio, con su conteo
   real de filas, una línea de qué aporta cada una y las llaves foráneas como
   flechas. Toca una tabla (o su chip) y verás sus columnas y tres filas de
   ejemplo.
3. **Las herramientas** — las siete tools con su docstring tal como la ve el
   modelo y un botón **▶ Probar** que las ejecuta en vivo contra la base, sin
   agente y con costo $0. El rótulo lo dice: *«aquí no hay ningún agente
   corriendo»*.
4. **Las preguntas** — las cinco preguntas de negocio con lo que hay que cruzar
   para responderlas, sin las respuestas. Cierra con el botón de transición:
   *«¿Cómo responde un LLM a esto? → Nivel 1»*.

La regla de la vista: **muestra datos, nunca conclusiones**. Las anomalías las
descubre la clase con los niveles, no esta pantalla.

### Vista Paso a paso — la que se usa para explicar

1. Elige el nivel en las tarjetas de arriba (`N1`…`N5`).
2. Haz clic en una **pregunta precargada** o escribe la tuya.
3. **Ejecutar N1** (el botón toma el nombre del nivel seleccionado).
4. **Siguiente nivel →** cuando termines de explicar ese.

Qué vas a ver, y qué señalar:

- **La petición viaja por el diagrama.** No es un dibujo al lado de la traza: cada
  evento manda un paquete etiquetado a recorrer su flecha. Se ve entrar la pregunta al
  modelo, salir el `tool_call` hacia la herramienta —en ámbar, con el nombre de la
  herramienta escrito—, volver el dato en lima y salir la respuesta en verde. Los nodos
  pasan de gris punteado a teal latiendo a lima.
- **En N2 tres caminos quedan tenues** y uno se enciende: eso es, visualmente, la
  información que el enrutador tuvo que tirar. **En N4** el paquete de resultado
  recorre hacia atrás la flecha de abajo, una vez por iteración — se pueden contar las
  vueltas. **En N5** destella 🔧 sobre cada agente con la herramienta que usó por
  dentro.
- **Debajo, la narración numerada** y el botón **↻ Repetir animación**, que reproduce
  el flujo con sus tiempos originales **sin volver a llamar a la API**. Explica el mismo
  paso tres veces si hace falta: no cuesta nada.
- **Cada llamada a herramienta va junto a su respuesta**, lado a lado: a la izquierda el
  JSON crudo que produjo el modelo, a la derecha lo que devolvió la base —resumido en
  una línea, con el JSON completo desplegable— y debajo la **docstring tal como la ve el
  modelo**. Las tres piezas juntas son *function calling* completo en una pantalla.
- **Qué observar** aparece al terminar la corrida. Está escrito para leerse en voz alta.

Cinco columnas avanzando a la vez no se pueden narrar. Por eso este modo es el
predeterminado y la comparación se guarda para el final.

### Vista Comparación — el cierre

1. Haz clic en una **pregunta precargada** (o escribe la tuya).
2. Elige qué niveles ejecutar con las casillas `N1`…`N5`.
3. **Ejecutar**.

Las cinco columnas avanzan **en tiempo real y a distinta velocidad**. N1 y N2 terminan
en un segundo; N5 sigue trabajando diez segundos después. Esa asimetría es el punto:
comunica el costo de la agencia mejor que cualquier explicación.

Al pie de cada columna: llamadas al modelo, herramientas usadas, tiempo y costo. La
comparación de esa fila entre N1 y N5 es la lección de diseño del laboratorio —
**más agencia no es gratis, y no toda pregunta necesita el nivel más alto.**

Las cinco preguntas precargadas:

| Pregunta | Dominio | Nivel que la resuelve bien |
|---|---|---|
| ¿Cuánto maíz le queda a Itagüí y me alcanza para la demanda de esta semana? | Compras | N4 |
| ¿Cuál equipo de Itagüí está en riesgo de falla y por qué? | Mantenimiento | N4 |
| ¿Dónde está el pedido PD-24-00871 y cuántos turnos le faltan? | Logística | **N3** |
| ¿Hubo algún día en que la demanda superó la producción y en cuánto? | Producción | N4 |
| El pedido PD-24-00871 va retrasado: ¿es materia prima o equipos? | Cruzada | N5 |

### Vista Detalle

Elige un nivel y verás:

- **Su system prompt, editable.** Cámbialo, aplica y vuelve a ejecutar. Es la
  herramienta más útil del tablero: prueba a prohibirle a N1 que invente cifras y
  observa si obedece.
- **La traza completa**: cada llamada al modelo con los mensajes enviados (verás el
  contexto crecer, y entenderás por qué N4 cuesta más), el **JSON crudo de cada tool
  call** —el mismo de la sección 7.2 del ebook— y el resultado de cada herramienta.
- **Las herramientas disponibles**, con la docstring **tal como la ve el modelo**.
  Esa docstring *es* el prompt de la herramienta. Es una de las lecciones del nivel 3.

---

## 6. Cómo usar los notebooks

**http://localhost:8888** — Jupyter abre directamente en el primero.


| | Para qué | Cómo se usa |
|---|---|---|
| **`1-los-cinco-niveles-explicado.ipynb`** | **Entender** el código de cada nivel | Se lee y se corre mientras el facilitador explica. Todo funciona; no hay nada que completar. |

### 1 · El notebook explicado

Existe porque el taller usa el mismo código que corre detrás del tablero —`NivelBase`,
`stream_react`, el contrato de eventos— y esa plomería es justo lo que estorba cuando
lo que se está explicando es *qué es* un llamador de herramientas.

Este **no importa nada del repositorio**. Solo `openai` y Python:

- Llamadas **síncronas**: se lee de arriba abajo, sin `async`/`await`.
- La "base de datos" es un **diccionario de quince líneas**. Cuando la fuente cabe en
  pantalla, nadie confunde el mérito del agente con el mérito del SQL.
- Los esquemas de las herramientas están **escritos a mano**, porque ver ese JSON *es*
  la lección de function calling.
- Cada nivel es una función que cabe en una pantalla y se puede proyectar completa.
- Corre igual en **Colab** con un `pip install openai`, por si alguien no logra
  levantar Docker.

Lo que hace que la progresión se entienda: **N4 es N3 dentro de un `while`**. Están uno
al lado del otro y la diferencia son tres líneas. Y **N5 es `n4()` llamada tres veces**
—dos especialistas y un supervisor—, así que la función `n5()` es literalmente una
línea. Al final de N4 se muestran las tres líneas equivalentes de
`create_react_agent`, para que se vea qué abstrae el framework y qué no.

Cada nivel cierra con **👀 Qué acaba de pasar** (para leer en voz alta) y **🔬 Tu
turno** (un experimento de una línea: pon `max_vueltas=1` y acabas de convertir N4 en
N3; quita la planta de la pregunta de N5 y verás el modo de falla del multiagente).

### 2 · El taller

Los mismos cinco niveles, pero los escribes tú. Tres reglas:

1. **Cada sección corre sin haber terminado la anterior** — hay una celda de rescate
   plegada con la implementación del nivel previo.
2. **Lo único que escribes son los `# TODO`**: 13 líneas en total (0 / 2 / 4 / 3 / 4).
3. **Los `assert` te dicen si terminaste**, sin preguntarle al facilitador.

Este sí usa LangGraph y el mismo código del tablero, a propósito: lo que construyes es
lo que después ves dibujado en `localhost:8000`.

---

## 7. Sin API key: modo replay

El laboratorio **funciona completo sin internet y sin API key**. Pon en `.env`:

```bash
MODO=replay
```

En replay, los cinco niveles reproducen trazas pregrabadas de las cinco preguntas
precargadas, **con sus tiempos originales**: la demo se ve igual, incluida la asimetría
de velocidad entre columnas.

> ### ⚠ Las trazas hay que grabarlas una vez
>
> **`backend/replay/trazas.json` no viene en el repositorio, y es a propósito.** Una
> traza es el registro de una ejecución real; fabricar su contenido a mano y
> presentarlo como grabación sería exactamente lo que este laboratorio enseña a no
> hacer. Así que el archivo se genera ejecutando, una sola vez, con API key:
>
> ```bash
> # con OPENAI_API_KEY en .env y MODO=vivo
> docker compose exec tablero python -m backend.replay.grabar
> # Prueba de humo completa SIN gastar cuota de API: los cinco niveles, los diez
# invariantes del contrato y las tools. Corre en ~20 s.
# Úsalo cada vez que edites un prompt, una tool o subas una dependencia.
docker compose exec tablero python scripts/prueba_humo.py

docker compose exec tablero python scripts/verificar_contrato.py backend/replay/trazas.json
> ```
>
> Mientras no existan, `MODO=replay` no falla ni simula: cada columna dice
> *«no hay traza pregrabada para este nivel»* y te remite a este comando. Es la
> respuesta honesta, y es lo que verás si arrancas el laboratorio sin key antes de
> grabar.
>
> Está en el checklist de la semana previa a la sesión ([spec 09](./specs/09-operacion-riesgos.md)).

Para qué sirve:

- Recorrer el laboratorio sin gastar (o sin cuenta).
- Estudiar las trazas después de la clase.
- **Plan B en clase** si la red del sitio bloquea la API o el proveedor se cae.

### Dos advertencias

**El indicador `◐ replay` del encabezado está siempre visible, y así debe quedarse.**
Si facilitas una demo, no presentes replay como si fuera ejecución en vivo. Si dices
«miren cómo el agente decide» sobre una traza grabada y alguien lo nota, pierdes la
credibilidad de todo el programa.

**Las trazas caducan.** Si cambias los system prompts o el modelo, hay que regrabarlas
o estarás mostrando algo que ya no es cierto:

```bash
docker compose exec tablero python -m backend.replay.grabar
```

Con `MODO=auto` (el default) no tienes que pensar en esto: usa vivo si hay key y
presupuesto, y cae a replay si no.

### Una nota de versiones que importa para tus proyectos

El laboratorio usa `create_react_agent` de `langgraph.prebuilt`, que es el nombre que
aparece en el ebook de la clase. **En LangGraph 1.x esa función está deprecada** en
favor de `langchain.agents.create_agent`, y se elimina en la 2.0. Funciona en la
versión fijada en `requirements.txt`, y se mantiene a propósito para que el código no
diga una cosa distinta que el material de clase.

**Para un proyecto real, usa la API vigente.** El cambio son dos líneas:

```diff
  # requirements.txt
+ langchain==1.*                     # confirma la versión menor al instalar

  # backend/niveles/react.py
- from langgraph.prebuilt import create_react_agent
- return create_react_agent(cliente(modelo), tools, prompt=system_prompt)
+ from langchain.agents import create_agent
+ return create_agent(cliente(modelo), tools, prompt=system_prompt)
```

Todo lo demás del repositorio sigue igual: el contrato de eventos, `stream_react` y el
tablero no dependen del nombre de esa función. Que aislar el framework detrás de un
módulo permita cambiarlo en dos líneas no es casualidad — es la razón de que
`construir_agente` exista como función aparte.

---

## 8. Ejecutar sin Docker

Docker es el camino recomendado. Usa esto solo si Docker no es una opción en tu equipo,
o si eres el facilitador y necesitas un plan C en la máquina que proyecta.

Necesitas **Python 3.12 o superior**.

```bash
# 1 · Entorno virtual
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2 · Dependencias
pip install -r requirements.txt

# 3 · Configuración
cp .env.example .env
nano .env                          # pega tu OPENAI_API_KEY

# 4 · Generar la base de datos sintética
python -m backend.db.seed --recrear

# 5 · Backend + frontend  (el mismo proceso sirve los dos)
uvicorn backend.main:app --reload --port 8000

# 6 · En OTRA terminal, con el entorno activado: el notebook
jupyter lab --notebook-dir=notebook --port=8888
```

El frontend lo sirve el mismo FastAPI en `http://localhost:8000` — no hay que levantar
nada aparte, ni hay Node, ni build step.

Si usas [`uv`](https://github.com/astral-sh/uv), los pasos 1 y 2 son:

```bash
uv venv && uv pip install -r requirements.txt
```

---

## 9. Comandos útiles

Todos desde la raíz del proyecto.

### Ciclo de vida

```bash
docker compose up -d --build     # construir y levantar en segundo plano
docker compose ps                # ¿qué está corriendo?
docker compose logs -f tablero   # ver logs del backend en vivo
docker compose logs -f notebook  # ver logs de Jupyter (aquí sale la URL)
docker compose restart           # reiniciar (tras cambiar .env)
docker compose down              # detener y eliminar contenedores
docker compose down -v           # ...y además borrar volúmenes (caché y base)
```

### Datos

```bash
# Regenerar la base de datos sintética desde cero
docker compose exec tablero python -m backend.db.seed --recrear

# Ver el esquema y el conteo de filas
curl -s localhost:8000/api/esquema | python3 -m json.tool

# Abrir una consola SQL sobre la base
docker compose exec tablero sqlite3 bios_ops.db
```

### Costo y caché

```bash
# Gasto acumulado, desglosado por nivel
curl -s localhost:8000/api/gasto | python3 -m json.tool

# Vaciar el caché de respuestas (para forzar llamadas reales)
docker compose exec tablero rm -rf .cache_llm/
```

### Diagnóstico

```bash
# Ver el stream de eventos crudo, sin navegador
RUN=$(curl -s -X POST localhost:8000/api/ejecutar \
  -H 'Content-Type: application/json' \
  -d '{"pregunta":"¿Cuánto maíz le queda a Itagüí?","niveles":["n3"]}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["run_id"])')
curl -N localhost:8000/api/stream/$RUN

# Documentación interactiva de la API
open http://localhost:8000/docs
```

### Validaciones del repo

```bash
# Contrastes de color WCAG de la interfaz
docker compose exec tablero python scripts/validar_contraste.py

# Verificar los 10 invariantes del contrato de eventos sobre las trazas de replay
docker compose exec tablero python scripts/verificar_contrato.py backend/replay/trazas.json

# Regrabar las trazas de replay
docker compose exec tablero python -m backend.replay.grabar
```

La autocomprobación de la base de datos corre sola al generarla, y verifica que los
identificadores usados por las 5 preguntas de demo existan:

```bash
docker compose exec tablero python -m backend.db.seed --recrear
# ✓ PD-24-00871 existe · estado = en_muelle · posición en cola = 6 ✓
# → Base de datos válida para las 5 preguntas de demo.
```

---

## 10. Solución de problemas

### Docker no arranca

| Síntoma | Causa | Solución |
|---|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop no está corriendo | Ábrelo y espera a que el icono se estabilice |
| `docker: 'compose' is not a docker command` | Docker muy antiguo o falta el plugin | Actualiza a Docker 24+. En Linux: `sudo apt install docker-compose-plugin` |
| `port is already allocated` | Otro proceso usa el 8000 o el 8888 | Averigua quién con `docker ps` (suele ser otro contenedor tuyo) y detenlo con `docker stop <nombre>`, **o** cambia `PUERTO_TABLERO` / `PUERTO_NOTEBOOK` en `.env` |
| Liberaste el puerto pero `localhost:8000` sigue sin responder | El contenedor se **creó** cuando el puerto estaba ocupado, así que quedó sin mapeo. `docker compose up` lo reinicia pero no lo recrea | `docker compose up -d --force-recreate tablero`. Para comprobarlo: `docker inspect clase1-tablero --format '{{json .NetworkSettings.Ports}}'` — si sale `{"8000/tcp":[]}`, el mapeo está vacío |
| El build falla descargando paquetes | Proxy corporativo o red inestable | Reintenta; si persiste, configura el proxy en Docker Desktop → Settings → Resources → Proxies |
| `no space left on device` | Disco lleno de imágenes viejas | `docker system prune -a` (⚠ borra imágenes no usadas de **todos** tus proyectos) |

### La API key no funciona

| Síntoma | Causa | Solución |
|---|---|---|
| `/api/salud` dice `key_presente: false` | El `.env` no existe, o la variable está mal escrita | ¿Existe `.env` en la **raíz**? ¿Se llama exactamente `OPENAI_API_KEY`? ¿Sin espacios ni comillas alrededor del valor? |
| Sigue en `false` tras arreglar el `.env` | Los contenedores tienen los valores viejos | `docker compose restart` |
| Error `401 Unauthorized` | Key inválida, revocada o incompleta | Genera una nueva en platform.openai.com. Verifica que copiaste **toda** la key |
| Error `429 Too Many Requests` | Límite de peticiones de la cuenta, o varias personas con la misma key | Baja `MAX_CONCURRENCIA` a `2`. Verifica que `CACHE_ACTIVO=true`. Si es una key compartida, es lo esperado bajo carga: el sistema reintenta solo |
| Error `insufficient_quota` | La cuenta no tiene saldo | Carga saldo, o usa `MODO=replay` para seguir sin gastar |
| El costo sale siempre `$0.00` | `PRECIO_*_POR_1M` están en `0.00` | Ponles la tarifa real del modelo, verificada en los precios de OpenAI |

### El tablero se ve mal o no responde

| Síntoma | Causa | Solución |
|---|---|---|
| Página en blanco | El backend no arrancó | `docker compose logs tablero` y lee el error |
| Sin estilos, texto plano | Faltan los archivos de `frontend/assets/vendor/` | `docker compose up --build` (deben venir en el repo, no de internet) |
| No aparece el logo de Bios | Falta `frontend/assets/grupo-bios.png` | Verifica que el archivo existe en el repo |
| Las columnas dejan de actualizarse a la mitad | La conexión SSE se cortó (proxy) | Recarga la página: reconecta y continúa desde donde iba. Si es sistemático, el proxy corta conexiones largas: usa `MODO=replay` |
| Una columna queda «pensando» para siempre | Un nivel se colgó | `docker compose logs -f tablero`. Los niveles tienen tope de iteraciones: no deberían colgarse. Si pasa, es un bug: repórtalo |
| No veo bien desde el fondo del salón | — | El tablero soporta zoom hasta 150% sin romper las 5 columnas: `Cmd/Ctrl` + `+` |

### El notebook

| Síntoma | Causa | Solución |
|---|---|---|
| `localhost:8888` no abre | El servicio no levantó | `docker compose logs notebook` |
| Pide un token | Configuración alterada | El servicio corre sin token a propósito (red local). Si pide uno, sale en `docker compose logs notebook` |
| `ModuleNotFoundError: backend` | El notebook se abrió fuera del contenedor | Ábrelo desde `localhost:8888`, no con el Jupyter de tu equipo |
| `no such table: plantas` | La base no se generó | `docker compose exec tablero python -m backend.db.seed --recrear` |
| Un `assert` falla y no entiendo por qué | — | El mensaje del `assert` dice qué se esperaba. Si sigue sin cuadrar, ejecuta la celda de rescate y sigue: no pierdas la sesión en un nivel |
| Jupyter lentísimo en Windows | El repo está en `C:\` en vez de en WSL2 | Clónalo dentro del sistema de archivos de WSL2 (sección 1) |

### Cuando nada de lo anterior sirve

```bash
# Reconstruir todo desde cero (borra caché y base de datos)
docker compose down -v
docker compose build --no-cache
docker compose up
```

Si sigue fallando, junta esta información antes de pedir ayuda en el canal del
programa — con esto se diagnostica en minutos:

```bash
docker --version && docker compose version
docker compose ps
docker compose logs --tail=50 tablero
curl -s localhost:8000/api/salud
```

Y di en qué sistema operativo estás. **No pegues el contenido de tu `.env`** en el
canal: contiene tu API key.

---

## 11. Seguridad: lo que no debes hacer

Los datos de este laboratorio son sintéticos, pero **este repositorio es la plantilla
mental con la que vas a construir tus proyectos reales**. Lo que se normalice aquí se
repite en producción.

### Nunca

- ❌ **Subir `.env` a git.** Ya está en `.gitignore`; no lo saques. Si alguna vez
  subes una key por accidente: **rótala de inmediato** en platform.openai.com. Borrar
  el commit no basta — el historial de git y cualquier copia del repositorio la
  conservan.
- ❌ **Pegar tu API key** en el notebook, en una celda, en el chat del equipo o en un
  issue. Va solo en `.env`.
- ❌ **Publicar los puertos en `0.0.0.0`.** El `docker-compose.yml` los ata a
  `127.0.0.1` deliberadamente: el endpoint que edita los system prompts no tiene
  autenticación y Jupyter corre sin token. Son herramientas de demo en red local.
- ❌ **Cargar datos reales de Grupo Bios** en este laboratorio. Todo lo que una
  herramienta devuelve se envía al proveedor del modelo. Usar datos productivos exige
  antes definir contrato de tratamiento, clasificación de la información y controles de
  retención: eso se trabaja en las sesiones 2 y 7.
- ❌ **Darle permisos de escritura a un agente** sin una razón deliberada. Aquí las
  herramientas abren la base en **solo lectura**, y eso es una decisión de diseño, no
  una limitación.

### La idea que hay que llevarse

**Una herramienta es una superficie de ataque.** Cada función que le das a un agente es
una capacidad que un prompt malicioso puede intentar usar. Por eso la herramienta
opcional `ejecutar_sql` tiene seis restricciones apiladas —solo `SELECT`, lista negra
de tokens, conexión de solo lectura, `LIMIT` forzado, timeout y registro— y la garantía
real es la tercera, no la primera: **validar por texto el SQL que genera un LLM es
frágil**.

Esto se desarrolla completo en la Sesión 7. Aquí solo se siembra.

---

## 12. Estructura del repositorio

```
clase1-lab-agentes/
├── README.md                    ← este archivo
├── docker-compose.yml           dos servicios: tablero y notebook
├── Dockerfile
├── requirements.txt             versiones fijadas con ==
├── .env.example                 plantilla de configuración
├── .gitignore                   incluye .env, *.db, .cache_llm/
│
├── specs/                       ⭐ las especificaciones (léelas)
│   ├── README.md                índice y decisiones cerradas
│   ├── 01-vision-alcance.md     objetivo pedagógico y presupuesto de tiempo
│   ├── 02-arquitectura.md       componentes y decisiones técnicas (ADR)
│   ├── 03-datos.md              esquema y generador sintético
│   ├── 04-contratos.md          eventos, herramientas y API
│   ├── 05-niveles.md            N1–N5 y criterios de aceptación
│   ├── 06-identidad-visual.md   paleta de Grupo Bios y reglas de marca
│   ├── 07-frontend.md           el tablero
│   ├── 08-notebook.md           el notebook guiado
│   ├── 09-operacion-riesgos.md  riesgos, costos y seguridad
│   └── 10-guion-facilitador.md  minuto a minuto de la clase
│
├── backend/
│   ├── main.py                  FastAPI: rutas y streaming SSE
│   ├── config.py                variables de entorno, validadas
│   ├── eventos.py               el contrato de eventos
│   ├── caso.py                  el agregado de la vista El caso (spec 11)
│   ├── llm.py                   cliente + reintentos + caché + contador de gasto
│   ├── prompts.py               system prompts, editables en caliente
│   ├── db/seed.py               generador de datos sintéticos
│   ├── db/descripciones.py      qué aporta cada tabla, en lenguaje de negocio
│   ├── tools/operaciones.py     las 7 herramientas de dominio
│   ├── tools/ejemplos.py        ejemplos curados del botón «Probar»
│   ├── niveles/n1..n5           un módulo por nivel de agencia
│   └── replay/trazas.json       trazas pregrabadas (plan B)
│
├── frontend/
│   ├── index.html               el tablero (sin build step)
│   ├── app.js
│   ├── caso.js                  la vista El caso: mapa de la base y «Probar»
│   ├── diagrama.js              el diagrama animado de los niveles
│   ├── estilos.css
│   ├── caso.css
│   └── assets/                  logos y dependencias vendorizadas
│
├── notebook/
│   └── 2-los-cinco-niveles-taller.ipynb
│
└── scripts/
    ├── validar_contraste.py     verifica accesibilidad de la paleta
    └── verificar_contrato.py    valida los invariantes del contrato de eventos
```

**Por dónde empezar a leer el código**, si vas a estudiarlo:

1. `backend/eventos.py` — el contrato que todos los niveles cumplen. Todo lo demás
   depende de esto.
2. `backend/niveles/n3_tool_caller.py` — el loop de function calling **escrito a
   mano**. Es el corazón conceptual del laboratorio.
3. `backend/niveles/n4_react.py` — el mismo comportamiento con LangGraph, en 15
   líneas. Compáralos: la diferencia es exactamente lo que el framework abstrae.
4. `backend/tools/operaciones.py` — fíjate en las docstrings: son prompts.

---

## 13. Checklist antes de la clase

**Hazlo 24–48 horas antes, no el día de la sesión.** Si el grupo instala en clase, se
van 25 de los 55 minutos de práctica.

- [ ] Docker Desktop instalado y `docker info` responde
- [ ] Repositorio clonado (en Windows: **dentro de WSL2**)
- [ ] `.env` creado a partir de `.env.example`, con la API key pegada
- [ ] `docker compose up --build` termina sin errores
- [ ] `http://localhost:8000` muestra el tablero con `● vivo`
- [ ] **Pestaña El caso recorrida**: el escenario, el mapa de las tablas y un
      ▶ Probar ejecutado (llegar sabiendo qué es `inventario_planta` es la
      diferencia entre seguir N3 y mirarlo pasar)
- [ ] `http://localhost:8888` abre el notebook
- [ ] **Sección 0 del notebook ejecutada, con todos los `✓` en verde**
- [ ] Una pregunta precargada ejecutada en N3 desde el tablero, con respuesta
- [ ] Resultado reportado en el canal del programa (aunque haya fallado — **sobre todo
      si falló**)

### Adicional, para el facilitador

- [ ] Modelos habilitados y límites de tasa confirmados en la cuenta de OpenAI
- [ ] `PRECIO_ENTRADA_POR_1M` / `PRECIO_SALIDA_POR_1M` con la tarifa vigente
- [ ] `TOPE_USD` acordado con quien paga la cuenta
- [ ] Key compartida distribuida por canal seguro
- [ ] Trazas de replay regrabadas con los prompts y el modelo definitivos
- [ ] Las 5 preguntas ejecutadas en los 5 niveles, con respuestas revisadas
- [ ] Tablero probado **en el proyector real**, con zoom al 150%
- [ ] Plan C (sin Docker, sección 8) probado en la máquina que proyecta

---

## 14. Qué sigue

Este laboratorio es la **Sesión 1** de siete. El agente que construyes acá es la base
del proyecto integrador: no se tira nada.

| Sesión | Qué le agrega a este agente |
|---|---|
| **2** | Memoria conversacional y RAG sobre documentos internos |
| **3** | Skills estructuradas y conexión a MCPs |
| **4** | Configuración de agentes pre-construidos (Hermes, OpenClaw) |
| **5** | Harness: prompts versionados, tests, evals, control de costos |
| **6** | Spec Driven Development — y estas `specs/` como caso de estudio |
| **7** | Observabilidad con LangFuse/LangSmith, guardrails y seguridad |

Dos cosas de este laboratorio se retoman explícitamente más adelante: los `assert` del
notebook son el germen de los **evals** de la Sesión 5, y las trazas artesanales del
tablero existen para que en la Sesión 7 se aprecie qué aporta una herramienta de
observabilidad de verdad.

### Material de la clase

- **Ebook de la Sesión 1:** `../Clase 1 - Agentes/Notas de Clase 1 - Agentes.md`
- **Diapositivas:** `../Clase 1 - Agentes/index.html`
- **Especificaciones:** [`specs/`](./specs/)

### Lecturas

- *ReAct: Synergizing Reasoning and Acting in Language Models* — Yao et al.
- [LangGraph — Multi-agent concepts](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [LangChain — What is an agent?](https://blog.langchain.com/what-is-an-agent/)
- [OpenAI — Function calling](https://platform.openai.com/docs/guides/function-calling)

---

<p align="center">
  <img src="./frontend/assets/qypher.png" alt="Qypher" width="120">
</p>
<p align="center">
  <em>Qypher · Formación en Inteligencia Artificial</em><br>
  <sub>Los datos de este laboratorio son sintéticos y no representan las operaciones de Grupo Bios.</sub>
</p>
