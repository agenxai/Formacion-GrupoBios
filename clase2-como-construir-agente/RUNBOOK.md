# Run Book · Clase 2 — Cómo se construye un Agente de IA

> **Para qué es este documento.** Es la guía **operacional** del facilitador: qué
> comando correr, qué ventana tener abierta, qué verificar en cada corte temporal y
> qué fallback técnico aplicar si algo falla. No reemplaza al guion narrativo
> (`specs/08-guion-facilitador.md`) ni a la matriz de riesgos (`specs/07-operacion-riesgos.md`):
> los complementa con la capa de *ejecución técnica*.
>
> - `08-guion-facilitador.md` → **qué proyectas y qué dices** (narrativa).
> - `07-operacion-riesgos.md` → **qué puede romperse y cómo se mitiga** (riesgos).
> - `RUNBOOK.md` (este)       → **cómo se opera la máquina en cada minuto** (táctica).

---

## 0 · Realidad del ambiente (lectura obligatoria antes de la clase)

El `.env` de Bios en esta iteración apunta a **Azure AI Foundry**, no a Azure OpenAI
clásico:

```dotenv
AZURE_OPENAI_ENDPOINT=https://<recurso>.services.ai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-5.2
```

Por eso `cliente.py` (en `agente-transparente/` y en `agente-framework/`) usa
`ChatOpenAI(base_url=..., model=...)` de `langchain-openai`, **no** `AzureChatOpenAI`.
Encontrar `AzureChatOpenAI` en la spec 08 y en el ebook de la clase 1 es normal: la
spec original describe el *caso ideal*; el código ya está adaptado a la cuenta de
Foundry que Bios asignó a la formación. Funcionalmente el agente es idéntico (mismas
llamadas, `bind_tools`, formato de mensajes OpenAI estándar), solo cambia la puerta
de entrada al LLM.

> Si Bios cambia a un endpoint `*.openai.azure.com` (Azure OpenAI clásico) antes de
> la clase, basta con revertir `cliente.py` al bloque `AzureChatOpenAI` que conserva
> la git history —y usar `AZURE_OPENAI_API_VERSION=2024-10-21`. El resto del agente
> no se toca. Por eso el `cliente.py` vive aislado en su propio archivo.

**Comprobación rápida (antes de clase):**

```bash
cd clase2-como-construir-agente
python -c "
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
load_dotenv('.env')
llm = ChatOpenAI(base_url=os.environ['AZURE_OPENAI_ENDPOINT'],
                 api_key=os.environ['AZURE_OPENAI_API_KEY'],
                 model=os.environ['AZURE_OPENAI_DEPLOYMENT'], temperature=0)
r = llm.invoke('Responde solo: OK')
print('LLM ok ->', repr(r.content))
"
# LLM ok -> 'OK'
```

Si esto responde `'OK'`, las credenciales y la ruta son correctas.

---

## 1 · Pre-clase · Checklist 24–48 h antes (verificación, no setup)

El setup ya está hecho. Esto es *smoke test*. **Si cualquier item no pasa, no se da
la clase** (mismo principio que la spec 07).

### 1.1 · Dependencias y entorno

```bash
cd clase2-como-construir-agente
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -c "import langchain_openai, langchain_core, langgraph, openai, dotenv; \
          print('VERSIONES:', langchain_openai.__version__, langchain_core.__version__)"
# VERSIONES: 1.4.1 1.5.3
```

- [ ] `pip install` sin errores rojos.
- [ ] Importaciones limpias. Versiones esperadas: `langchain-openai==1.4.1`,
      `langchain-core==1.5.3`. (El `__version__` de `langgraph` no existe — no es un
      problema, solo que no lo verifiques así.)

### 1.2 · Base de datos

```bash
cp ../clase1-lab-agentes/bios_ops.db agente-transparente/bios_ops.db
cp ../clase1-lab-agentes/bios_ops.db agente-framework/bios_ops.db
ls -lh **/bios_ops.db                # ~2.2 MB
sqlite3 agente-transparente/bios_ops.db "SELECT COUNT(*) FROM (
    SELECT table_name FROM information_schema.tables);" 2>/dev/null || \
python -c "import sqlite3; \
           c=sqlite3.connect('agente-transparente/bios_ops.db'); \
           print('tablas:', len(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()))"
```

- [ ] `bios_ops.db` presente en **ambas** carpetas (transparente y framework).
- [ ] Abre en solo lectura (la abrió `tools.py` con `?mode=ro`).

### 1.3 · Conversación insignia · Parte 1a (transparente)

```bash
cd clase2-como-construir-agente/agente-transparente
python chat.py --demo
```

- [ ] Los 4 turnos devuelven respuestas correctas:
      1. 320 t maíz en Itagüí, bajo el mínimo (1.190 t).
      2. No alcanza: faltan ~1.331,9 t (demanda proyectada vs inventario).
      3. Molino EQ-ITG-MOL-01 con correctivos repetidos de la misma causa.
      4. PD-24-00871 en muelle, turno 6, 3 pasos faltantes.
- [ ] Turnos 2 y 3 **no** te piden repetir "Itagüí": la memoria funciona.
- [ ] Sin `404`, `401` ni `ConnectionError`.

### 1.4 · Conversación insignia · Parte 1b (framework)

```bash
cd ../agente-framework
python chat.py --demo
```

- [ ] Mismas respuestas esperadas (no `"no tengo esa información"`). Aquí la traza
      no imprime `[Thought]/[Action]/[Observation]` — es normal, el framework los
      maneja internamente.
- [ ] La memoria entre turnos está (implementada en `chat.py` vía
      `estado["messages"]` persistente; verificado).

### 1.5 · Servicio de tools para n8n (Parte 2)

```bash
cd clase2-como-construir-agente
python n8n/servicio_tools.py &
sleep 1 && curl -s http://localhost:8788/salud
# {"ok": true, "tools": ["consultar_demanda","consultar_inventario","estado_pedido","historial_fallas"], ...}

curl -s -X POST http://localhost:8788/tools/consultar_inventario \
     -H "Content-Type: application/json" \
     -d '{"planta":"Itagüí","materia_prima":"maíz"}'
# {"planta":"Planta Itagüí","fecha_corte":"2026-08-01","items":[{"materia_prima":"Maíz amarillo",...}]

pkill -f servicio_tools.py   # lo apagas para no dejarlo corriendo
```

- [ ] `/salud` responde con las 4 tools.
- [ ] `POST /tools/consultar_inventario` devuelve 320 t.
- [ ] No depende del `.env` de Azure —solo lee `bios_ops.db`.

### 1.6 · n8n cloud de Bios

- [ ] Acceso a la instancia: usuario con permisos de **import**.
- [ ] `plantilla-agente-bios-react.json` importado en el workflow `Agente Bios ReAct`.
- [ ] Nodo **Azure OpenAI Chat Model** (`@n8n/n8n-llm-openai`) con la **credencial
      ya registrada** por TI. Encontrar el tipo de credencial depende de cómo la haya
      configurado Bios: si Bios entró por Foundry, el nodo se llama *OpenAI* con
      `Base URL` apuntando al endpoint de Foundry, y el model = `gpt-5.2`. Si entró
      por Azure OpenAI clásico, es *Azure OpenAI Model* con deployment y API version.
      Alinear con TI antes de la clase (ver apéndice B).
- [ ] En los **4 nodos Tool**, reemplazar `HOST-SERVICIO-TOOLS:8788` por la URL
      interna donde correrá `servicio_tools.py` (coordinar con TI — ver §4.1).
- [ ] Turno 1 de la conversación insignia ejecutado desde el chat del workflow en
      el navegador, respuesta 320 t.

### 1.7 · Plan C

- [ ] Transcripción de la conversación esperada (Partes 1a/1b) lista para proyectar
      si Azure falla. **Marcada como "ejecución pre-grabada"** —nunca pasarla por viva.
- [ ] Capturas de pantalla del workflow de n8n ejecutado, en orden.
- [ ] Graba un video del flujo completo de la Parte 2 como respaldo (5 min alcanza).

---

## 2 · Montaje · 5 minutos antes de empezar

Con el grupo entrando:

- [ ] **Ventanas abiertas en VS Code** (fuente 18-20pt, zoom al 125%):
      - `agente-transparente/` con los 6 archivos visibles en el explorador lateral:
        `cliente`, `tools`, `memoria`, `loop`, `agente`, `chat`.
      - `agente-framework/agente.py` abierto en otra pestaña (para el min 46).
- [ ] **Terminal** en `agente-transparente/`, fuente agrandada, `.env` ya cargado,
      `bios_ops.db` presente.
- [ ] **Segunda terminal** en `clase2-como-construir-agente/`, lista para levantar
      `servicio_tools.py` en el minuto 52.
- [ ] **Navegador** con el workflow de n8n ya abierto, login hecho, pestaña lista.
- [ ] **Otra pestaña del navegador** con el plan C (transcripción) cargado, por si
      Azure cae —no cerrar.
- [ ] **Pantalla de diapositivas** con: mapa "prototipo → funcional → datos →
      agéntico" (marcar "hoy: funcional"), arco S1 → S2, tabla de equivalencias
      para el cierre.

> **Si el checklist 24-48h no se cumplió** → no arrancar. Reagendar o ajustar. Un
> fallo de preparación no es material didáctico.

---

## 3 · Parte 1a · El agente pieza por pieza (min 8–46)

Narrativa: ver `08-guion-facilitador.md` §"Parte 1a". Aquí solo la operatoria.

### 3.1 · `cliente.py` (min 8–13)

**Comando rápido para mostrar el `.env` sin exponer la key:**

```bash
awk -F= '/^[A-Z_]+=/{print $1": "(length($2)?"OK":"FALTA")}' .env
```

- [ ] Las 3 obligatorias dicen `OK`.
- [ ] Señala que `cliente.py` usa `ChatOpenAI` con `base_url` apuntando a Foundry.
      Si alguien pregunta por Azure clásico: *"mismo archivo, distinto constructor —
      `AzureChatOpenAI` lo tengan en el bolsillo, lo desempolvan si TI cambia de
      puerta"*.

### 3.2 · `tools.py` (min 13–21) — ejecutar una tool sola

```bash
cd agente-transparente
python -c "from tools import consultar_inventario; import json; \
          print(json.dumps(consultar_inventario('Itagüí','maíz'), ensure_ascii=False, indent=1))"
```

- [ ] Output: 320 t, `bajo_minimo: true`. Si da error "no encuentra la planta"
      → `bios_ops.db` falta o está corrupta, ver §7.1.

### 3.3 · `loop.py` (min 26–35) — primer turno en vivo

```bash
python chat.py
# tú › ¿Cuánto maíz le queda a la planta de Itagüí?
```

**Verificaciones durante la ejecución:**

- [ ] Aparece `── iteración 1 ──` casi de inmediato.
- [ ] `[Action] consultar_inventario(...)` dentro de los 5-8 s.
- [ ] `[Observation]` con 320 t.
- [ ] `── iteración 2 ──` y luego `[Respuesta]` con la cifra correcta.

**Qué hacer si se cuelga más de 15 s esperando Azure:**

| Síntoma | Acción |
|---|---|
| `404 Resource not found` | Ver §7.2 — el endpoint del `.env` no calza con el constructor del `cliente.py`. |
| `401 Unauthorized` | La key del `.env` está mal o expiró. Revisar con TI en el break. Plan C ahora. |
| `RateLimit / 429` | Azure saturado. Plan C o ejecuta solo el turno 2 (la lección). |
| Sin traza, parado | `Ctrl+C`. Verificá red o cambio de variable. |
| `Connection refused` | Proxy corporativo bloqueando `*.services.ai.azure.com`. Plan C. |

### 3.4 · Resto de la conversación (min 40–46)

```bash
tú › ¿Y me alcanza para la demanda proyectada de esta semana?
tú › ¿Hay algún equipo de esa misma planta en riesgo de falla?
tú › ¿Cómo va el pedido PD-24-00871?
tú › salir
```

- [ ] El turno 2 encadena con el 1 (no repite planta ni materia prima).
- [ ] El turno 3 cambia de dominio (de inventario a `historial_fallas`).
- [ ] Si `MAX_ITERACIONES = 5` corta algún turno, lo señalas como material
      didáctico y lo retomas en el break.

---

## 4 · Parte 2 · n8n (min 53–78)

### 4.1 · Levantar el servicio de tools (hacerlo en el min 52)

Abre la segunda terminal (la de `clase2-como-construir-agente/`):

```bash
python n8n/servicio_tools.py
# [servicio_tools] Escuchando en http://0.0.0.0:8788
# [servicio_tools] Tools expuestas: consultar_demanda, consultar_inventario, ...
```

- [ ] El log dice "Escuchando en 8788".
- [ ] Deja esta terminal visible (minimizada con log a un costado) para ver que
      lleguen los `POST /tools/...` cuando n8n ejecute.

> **Bloqueante de red.** Si n8n cloud de Bios no puede alcanzar tu `localhost`
> (lo normal), TI de Bios tiene que haber alojado `servicio_tools.py` en una VM
> interna y haber puesto esa URL en los 4 nodos Tool del workflow. Si no está
> hecho, la Parte 2 no es viable —plan C. Ver `n8n/README.md` §"Cómo lo alcanza
> la instancia n8n cloud de Bios".

### 4.2 · Recorrido de nodos (min 53–73)

Narrativa: ver `08-guion-facilitador.md` §"Parte 2". Operatoria:

- [ ] Abrir cada nodo Tool, señalar `Description` (idéntico a la docstring).
- [ ] Abrir **Window Buffer Memory**, sessionId `bios-clase2`, ventana 10.
- [ ] Abrir el nodo AI Agent y el nodo de credencial (sin mostrar la key misma).

### 4.3 · Ejecución en vivo (min 73–78)

Ejecutá el turno 1 desde el **chat del workflow** en el navegador:

> «¿Cuánto maíz le queda a la planta de Itagüí?»

- [ ] En la terminal de `servicio_tools.py` aparece un `POST /tools/consultar_inventario`.
- [ ] En el navegador, el nodo AI Agent se enciende, el nodo Tool ejecuta y vuelve.
- [ ] Respuesta: "320 toneladas de maíz amarillo, bajo el mínimo (1.190 t)".

**Caídas:**

| Síntoma | Acción | Qué dices |
|---|---|---|
| El nodo Tool da error de red | El servicio no está corriendo o no es alcanzable. Verifica en la terminal: ¿llegó el `POST`? | «Esperá que reviso el servicio» — silencio breve, reconfigura la URL en el nodo, reintenta. Si no resuelves en 2 min → plan C. |
| El nodo AI Agent da 404/401 en proveedor | La credencial de Bios no fue actualizada / expiró. Plan C. | «Se nos cayó la credencial en Bios. Esto pasa en producción y por eso TI lo credential a parte. Vamos con la transcripción.» |
| El workflow no está cargado | Lo importaste mal. Reimportar desde `Import from File`. | breve, reintenta. Si no carga, plan C con capturas. |

---

## 5 · Cierre (min 78–90)

- [ ] Proyectar la **tabla de equivalencias** (`n8n/README.md` §"Equivalencias").
- [ ] Recapitular los 5 conceptos (60 s): cerebro, tools, memoria, loop, interfaz.
- [ ] **Puente a S3**: el agente de hoy lee **datos estructurados** (tablas). La
      próxima clase el agente leerá **documentos** (manuales, políticas,
      contratos): **RAG**. No se tira nada de hoy: se extiende.
- [ ] Entregable señalado: `COMO-MONTARLO.md` + el repo (acceso que TI confirma).

---

## 6 · Posh-clase

- [ ] `pkill -f servicio_tools.py` en la terminal de tools —no dejar corriendo.
- [ ] Guarda la traza del terminal (`script` o copia del buffer) por si hay que
      ajustar el system prompt para S3.
- [ ] Si se editó el system prompt en vivo, `git diff agente-transparente/agente.py`
      antes de cerrar —decidir si se queda o se revierte.
- [ ] Recordar al equipo de Innovación: el `.env` **no** al git, **no** al chat.
- [ ] Cerrar la sesión del navegador de n8n.

---

## 7 · Apéndice · Resolución de incidentes técnicos

### 7.1 · `bios_ops.db` corrupta o ausente

```bash
ls -lh agente-transparente/bios_ops.db
# si no existe o pesa <500 KB:
cp ../clase1-lab-agentes/bios_ops.db agente-transparente/bios_ops.db
cp ../clase1-lab-agentes/bios_ops.db agente-framework/bios_ops.db
# última opción: regenerar
cd ../clase1-lab-agentes && python -m backend.db.seed --recrear && cd -
cp ../clase1-lab-agentes/bios_ops.db agente-transparente/bios_ops.db
```

### 7.2 · Error 404 en la primera llamada al LLM

Casi siempre: el constructor del `cliente.py` no calza con el endpoint del `.env`.

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')
ep = os.getenv('AZURE_OPENAI_ENDPOINT','')
print('endpoint:', ep)
print('¿Foundry?:', 'services.ai.azure.com' in ep)
print('¿OpenAI clásico?:', ep.endswith('.openai.azure.com') or 'openai.azure.com' in ep and 'services.ai' not in ep)
"
```

- Si dice **Foundry** → `cliente.py` debe usar `ChatOpenAI(base_url=ep, model=dep)`.
  Es el caso actual.
- Si dice **OpenAI clásico** → `cliente.py` debe usar `AzureChatOpenAI(azure_endpoint=ep,
  azure_deployment=dep, api_version=...)`. Revisa el historial git para el bloque
  previo.
- Si dudas → prueba los dos constructores con el comando de §0 y quédate con el que
  responde `'OK'`.

### 7.3 · Agente pierde memoria entre turnos (Parte 1a)

- Síntoma: turno 2 responde *"¿de qué planta?"* en vez de encadenar.
- Causa más común: `memoria.py` está bien, pero se reinicializa el objeto `AgenteReAct`
  por error. Verifica que en `chat.py` el `agente = AgenteReAct()` está **fuera** del
  `while`.
- Causa secundaria: el system prompt demasiado verboso empuja los mensajes de
  memoria fuera del contexto. Si el modelo es pequeño, reducir prompt.

### 7.4 · Agente pierde memoria entre turnos (Parte 1b)

- Síntoma: el grafo responde *"no tengo información"* en turnos 2/3.
- Causa: se está invocando `agente.invoke({"messages": [user]})` con una lista
  **fresca** en cada turno. Verifica que `chat.py` persiste `estado["messages"]`
  entre turnos (bloque `_preguntar` en `agente-framework/chat.py`).
- Fix rápido: `estado = {"messages": []}` antes del bucle, y
  `estado["messages"] = resultado["messages"]` tras cada invoke.

### 7.5 · n8n no puede alcanzar `servicio_tools.py`

- `localhost:8788` desde el navegador de Bios cloud no funciona (es tu máquina, no
  la de n8n). Tres salidas:
  1. **Túnel temporal** aprobado por TI durante la clase (p. ej. delete después).
  2. **Alojar `servicio_tools.py` en VM interna de Bios** (la opción permanente).
  3. **Plan C**: transcripción + capturas, sin demo en vivo.
- Si Bios tiene n8n self-hosted en la misma red que tu laptop → funciona con tu IP
  local (`http://192.168.x.x:8788`). Verifica con `curl` desde la VM de n8n antes.

### 7.6 · Comandos de rescate rápido

```bash
# Revertir edit del system prompt hecho en vivo
cd clase2-como-construir-agente
git checkout -- agente-transparente/agente.py

# Reiniciar el servicio de tools
pkill -f servicio_tools.py
python n8n/servicio_tools.py

# Limpiar caché de Python (si imports raras después de upgrades)
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
```

## Apéndice B · Credencial en n8n: Foundry vs Azure OpenAI clásico

El flujo JSON exporta el nodo del proveedor como referencia, no como secret. Al
abrirlo en la instancia de Bios, TI elige la credencial. Dos escenarios:

| TI de Bios configuró... | Nodo a usar en n8n | Campos clave |
|---|---|---|
| **Azure AI Foundry** (endpoint `*.services.ai.azure.com/openai/v1`) | *OpenAI* model node (no el de Azure) | `Base URL` = endpoint de Foundry · `Model` = `gpt-5.2` (el deployment name) |
| **Azure OpenAI clásico** (endpoint `*.openai.azure.com`) | *Azure OpenAI Chat Model* | `Resource name` + `Deployment name` = `gpt-4o-mini` + `API version 2024-10-21` |

**El agente no sabe ni le importa** cuál sea la puerta: el contrato (mensajes,
tool_calls, bind_tools) es OpenAI estándar en ambos. La decisión es de TI, no del
curso. Si la duda surge en clase: *"el nodo del proveedor lo configura TI de Bios
porque conoce la puerta que les abrieron; el modelo es el mismo en cualquier
caso"*.

### Detección visual (sin abrir el `.env`)

Si en el workflow importado TI llamó al nodo *OpenAI* y no *Azure OpenAI Chat
Model*, es Foundry. Si lo llamó *Azure OpenAI Chat Model* y pide `Deployment name`,
es el camino clásico. Aceptar lo que TI armó —no configurar en clase.

---

## 8 · Decisiones docentes que el run book asume

- **No se monta el tablero de la clase 1.** Ese backend era solo para el frontend
  de los 5 niveles. La Parte 2 usa `servicio_tools.py` (servicio nuevo, 120 líneas,
  hereda `tools.py` de la clase 2). Levantar el tablero no ayuda y confunde.
- **No se edita `.env` en clase.** Si no funciona, plan C. Ajustar `.env` en vivo
  pierde tiempo y expone la key.
- **No se cambia de framework en vivo** (de Foundry a Azure clásico o viceversa).
  Es decisión de TI / infraestructura, no del curso.
- **Servicio de tools se apaga al terminar la clase.** No queda expuesto.

---

## 9 · Atajos de tiempo

Si llegás a un corte y vas tarde:

| Corte | Si vas >5 min tarde, recorta |
|---|---|
| Min 13 (`cliente.py`) | Saltá la ejecución del awk; sólo señalá que las 3 variables están. |
| Min 21 (`tools.py`) | Ejecutá solo `consultar_inventario`, no los 4 en demo suelta. |
| Min 26 (`memoria.py`) | Mostrá `agregar` y `mensajes`, no recorra la clase entera. |
| Min 35 (`loop.py`) | Ejecutá solo el turno 1, dejá 2-4 para el min 40. |
| Min 46 (Parte 1b) | Mostrá sólo el diff lado a lado —no corras el demo de framework. |
| Min 78 (Cierre) | Acortá el puente a S3 a 30 s. La tabla de equivalencias siempre. |

La pieza no recortable: la ejecución del turno 1 en el agente transparente (min 30)
y la tabla de equivalencias al cierre. El resto es teasing.