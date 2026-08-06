# Cómo montar el agente tú mismo

> **Para quién es esto.** Para los participantes de la clase 2 que quieran
> reproducir lo que vimos proyectado: levantar el agente en su máquina, en VS
> Code o en la terminal, y conversar con él. Los pasos están escritos para
> quien llega con Python instalado pero jamás corrió un agente.

Esta guía cubre la **Parte 1** (código Python con Azure OpenAI). La Parte 2
(n8n cloud de Bios) se monta desde el workflow exportado que ya está en la
instancia n8n —pregúntale al facilitador si tu equipo no lo ve.

---

## 0 · Requisitos

| Qué | Versión | Cómo verificar |
|---|---|---|
| Python | 3.10 o superior | `python --version` |
| pip | cualquiera reciente | `pip --version` |
| Una terminal | — | cmd / PowerShell / bash / zsh |
| VS Code (opcional) | cualquiera | para leer los archivos con cómodidad |

Y **una cuenta de Azure OpenAI** con un deployment de modelo (por defecto
`gpt-4o-mini`). Bios te entrega las tres credenciales que necesitas; no las
pegues en un chat, ni las subas a un repo.

> **Si no tenés acceso a Azure todavía:** igual seguí los pasos 1 a 4 —el
> armado no necesita credenciales. Vas a poder correr el primer script recién
> cuando completes `.env`, pero el código y la base ya están listos.

---

## 1 · Bajá el repo de la clase 2

Si tu equipo te dio acceso al repositorio (te lo confirma José o el líder de
Innovación), clonalo:

```bash
git clone <URL-DEL-REPO>
cd clase2-como-construir-agente
```

Si te lo entregaron como `.zip`, descomprimilo y entrá al directorio.

```
clase2-como-construir-agente/
├── agente-transparente/   ← Parte 1a · loop ReAct a mano
├── agente-framework/       ← Parte 1b · mismo agente con LangGraph
├── n8n/                    ← Parte 2 · plantilla del workflow (no hace falta para este doc)
├── specs/                  ← las especificaciones (te servirá leerlas)
├── requirements.txt
├── .env.example
└── COMO-MONTARLO.md        ← este archivo
```

---

## 2 · Instalá las dependencias

No las instales en el Python del sistema —vas a ensuciarlo. Creá un entorno
virtual:

```bash
# adentro de clase2-como-construir-agente/
python -m venv .venv

# activá el venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate          # macOS / Linux

# instalá las deps (versiones fijadas, probadas)
pip install -r requirements.txt
```

La primera vez tarda ~30 segundos. Si termina sin errores rojos, estás.

---

## 3 · Configurá las credenciales de Azure OpenAI

Copiá la plantilla y completala:

```bash
cp .env.example .env
# abrí .env con tu editor (Notepad, VS Code, nano, lo que sea)
```

El `.env` que tenés que completar se ve así:

```dotenv
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.openai.azure.com/
AZURE_OPENAI_API_KEY=<pega-aqui-tu-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```

**Tres reglas que no se negocian:**

- ❌ Nunca pegues la key en un chat, correo, mensagem, ni en el chat de
  Innovación. Si Bios te la da por un canal seguro (gestor de contraseñas o
  mensaje directo), solamente ahí.
- ❌ Nunca subas `.env` al git. Ya está en `.gitignore`; no lo saques de ahí.
- ❌ Si la clave se te escapa, rotala al instante en Azure. Borrar el commit
  no basta — el historial de git la conserva.

---

## 4 · Conseguí la base de datos `bios_ops.db`

El agente consulta operaciones de planta. La base es **sintética** —ficticia—,
generada por el laboratorio de la clase 1. No tiene datos reales de Bios.

Dos opciones:

**(a) Ya la tenés en la clase 1.** Si clonaste el repo de la clase 1 y
generaste la base, copiala:

```bash
cp ../clase1-lab-agentes/bios_ops.db agente-transparente/bios_ops.db
# también a la carpeta framework si vas a probar la Parte 1b
cp ../clase1-lab-agentes/bios_ops.db agente-framework/bios_ops.db
```

**(b) Regenerá la base desde la clase 1.** Sin la base, las tools van a
responder "no encontré esa planta". Generada una sola vez (seed fija) y
copiada adentro:

```bash
cd ../clase1-lab-agentes
docker compose exec tablero python -m backend.db.seed --recrear
# o, si no usás Docker:
python -m backend.db.seed --recrear
cp bios_ops.db ../clase2-como-construir-agente/agente-transparente/
cd ../clase2-como-construir-agente
```

> La base ya NO se incluye en el repo —es binaria y se versiona el generador,
> no el archivo (spec 03 de la clase 1).

---

## 5 · Corré el agente transparente (Parte 1a)

```bash
cd agente-transparente
python chat.py
```

Si todo está bien, vas a ver el banner con 4 preguntas sugridas y el aviso de
datos sintéticos. El cursor va a decir `tú › `.

Probá la conversación insignia —es la misma que vimos en clase:

```
tú › ¿Cuánto maíz le queda a la planta de Itagüí?
tú › ¿Y me alcanza para la demanda proyectada de esta semana?
tú › ¿Hay algún equipo de esa misma planta en riesgo de falla?
tú › ¿Cómo va el pedido PD-24-00871?
```

O, si querés correr los 4 turnos solo sin teclear:

```bash
python chat.py --demo
```

Para salir, escribí `salir`.

### Qué vas a ver

Cada vez que el agente decide invocar una tool, el terminal imprime:

```
── iteración 1 ──
[Thought] El usuario pregunta por el inventario de maíz…
[Action]   consultar_inventario({"planta": "Itagüí", "materia_prima": "maíz"})
[Observation] {"planta": "Planta itagüí", "items": [{"cantidad_ton": 320.0, ...
── iteración 2 ──
[Respuesta] En Itagüí quedan 320 toneladas de maíz amarillo, bajo el mínimo ...
```

Eso es el ciclo ReAct materializado —pensamiento, acción, observación. Es
exactamente lo que vimos en la clase 1, ahora en código.

---

## 6 · Corré el agente con framework (Parte 1b)

```bash
cd ../agente-framework
python chat.py
# o
python chat.py --demo
```

Vas a ver las mismas respuestas, pero la traza es distinta: el framework
LangGraph maneja el ciclo internamente. Si querés verlo, podés imprimir
`resultado["messages"]` antes de tomar el último, y vas a ver cada paso.

### La lección, en una frase

Abrí los dos archivos lado a lado:

```bash
# en VS Code, abrí estos dos en una ventana partida:
agente-transparente/loop.py            ← 130 líneas que escribimos a mano
agente-framework/agente.py             ← 3 líneas efectivas con create_react_agent
```

El framework no hace otra cosa; **empaqueta** lo que escribimos a mano.

---

## 7 · Leé los archivos (lo útil de verdad)

La clase muestra cómo se construye el agente pieza por pieza. Cuando lo querás
revisar con calma, abrí en este orden (cada uno enseña un concepto):

| Archivo | Concepto | Cuántas líneas |
|---|---|---|
| `cliente.py` | el cerebro (Azure OpenAI) | 15 |
| `tools.py` | los brazos (4 funciones + schemas) | 250 con comentarios |
| `memoria.py` | la memoria (buffer de mensajes) | 50 |
| `loop.py` | el ciclo ReAct a mano | 130 |
| `agente.py` | ensamblar todo en una clase | 60 |
| `chat.py` | la interfaz de terminal | 80 |

Empezá por el `loop.py` —es donde está la diferencia clave entre un agente y
un LLM puro.

---

## 8 · Si algo falla

### `ModuleNotFoundError: No module named 'langchain_openai'`

Te faltó activar el venv o instalar las dependencias. Volvé al paso 2.

### `SystemExit: Faltan variables de entorno requeridas: ...`

El `.env` está incompleto. Volvé al paso 3.

### `No encuentro bios_ops.db en ...`

Falta la base. Volvé al paso 4.

### Error `401 Unauthorized` al preguntar

La key no es válida (o el deployment no existe). Verificá en Azure que
tenés un deployment llamado como `AZURE_OPENAI_DEPLOYMENT` y que la key
coincide.

### Error `429 Too Many Requests`

Estás golpeando el rate limit del deployment. Esperá un minuto o reducí la
frecuencia de las preguntas. Esto es contenido: en producción se maneja con
reintentos y caching (sesión 5 del acompañamiento).

### "El agente no resolvió en 5 iteraciones"

El LLM se quedó iterando sin terminar. Reformulá la pregunta o aumentá
`MAX_ITERACIONES` en `loop.py` (no se recomienda para producción; mejor
afinar el prompt).

### Todo arranó pero las respuestas son raras (inventa cifras)

El system prompt no está cargándose. Verificá que `agente.py` mande
`SYSTEM_PROMPT` (en la Parte 1a es `Memoria(system_prompt=SYSTEM_PROMPT)`).
Si faltan reglas en el prompt, agregalas: la prohibición de inventar cifras
es la salvaguarda más barata.

---

## 9 · Lo que NO hace este agente (y por qué)

- **No persiste la memoria** entre ejecuciones. Al cerrar `chat.py`, el agente
  olvida. La persistencia es tema de producción —lo vemos en el acompanamiento.
- **No tiene RAG** (lectura de documentos). Eso es la clase 3.
- **No es multiagente**. Un solo agente. Multiagente es la clase 4.
- **No tiene observabilidad formal** (LangFuse, LangSmith). Las trazas del
  terminal sirven para entender, no para auditar en producción.
- **No escribe en la base**. La conexión es de solo lectura —una decisión de
  diseño, no una limitación. Es la primera salvaguarda que vimos.

---

## 10 · El mismo agente en n8n (Parte 2)

La Parte 2 vive en la instancia n8n cloud de Bios — el workflow ya está
importado (si tu equipo no lo ve, preguntale al facilitador). Los detalles de
montaje están en `n8n/README.md`. Lo que importa acá es la equivalencia: **es
el mismo agente**, pieza por pieza:

| Concepto | Python (Parte 1a/1b) | n8n (Parte 2) |
|---|---|---|
| Cerebro (LLM) | `AzureChatOpenAI` en `cliente.py` | Nodo *Azure OpenAI Chat Model* |
| Herramientas | funciones en `tools.py` + `TOOLS_FUNC` | Nodos *Tool* conectados al *AI Agent* |
| Prompt de cada tool | la docstring de la función | campo *Description* del nodo Tool |
| Schema de parámetros | JSON en `SCHEMAS` | *Placeholders* del nodo Tool |
| Memoria | `Memoria` (lista de mensajes) | Nodo *Window Buffer Memory* |
| Loop ReAct | `loop.py` (1a) / `create_react_agent` (1b) | El nodo *AI Agent* lo hace internamente |
| Interfaz | `chat.py` (bucle de `input()`) | El *Chat Trigger* es la interfaz |

El agente es el mismo. Lo que cambia es el medio. Si lo entendés en uno, lo
entendés en el otro.

---

## 11 · Siguiente paso

Llevate el repo a tu equipo. Cuando quieras empezar a adaptar las tools a tu
proyecto real de Bios (mantenimiento, compras, logística o producción),
reemplazá las funciones de `tools.py` por las funciones que consulten tus
datos —pero **sin tocar `loop.py`, `agente.py` ni `memoria.py`**. El agente
cambia de cara sin cambiar de cerebro.

Cuando quieras pasar a producción, conversamos en el acompañamiento.