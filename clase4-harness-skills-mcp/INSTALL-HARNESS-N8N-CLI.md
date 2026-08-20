# Cómo instalar el harness + n8n-cli y conectarlos a tu computador

> **Para quién es esto.** Para los participantes de la clase 4 que quieran
> reproducir lo que vimos proyectado: instalar un harness (OpenCode por
> defecto; Claude Code y Codex como alternativas), conectarle la Skill
> "analista operativo", un MCP de Google Sheets y la CLI de n8n — todo en
> su propia máquina, sin ayuda del facilitador.
>
> Es el **Entregable 3** de la sesión: el proceso documentado, paso a paso,
> probado para que cualquiera pueda seguirlo — técnico o no.

Esta guía está escrita para quien llega con una terminal abierta y nada
más. Si algo se rompe, hay una sección "Si algo falla" al final con los
errores más comunes.

---

## 0 · Requisitos

| Qué | Versión | Cómo verificar |
|---|---|---|
| Node.js | 18 o superior | `node --version` |
| npm | cualquiera reciente | `npm --version` |
| Python | 3.10 o superior | `python --version` |
| Una terminal | — | cmd / PowerShell / bash / zsh |
| Git | cualquiera reciente | `git --version` |

Y **una cuenta del proveedor del LLM** (OpenAI o Anthropic) con una API
key válida. Si Bios te entrega credenciales corporativas (Azure OpenAI),
usá esas — no las pegues en un chat ni las subas a un repo.

> **Si no tenés cuenta de LLM todavía:** igual seguí los pasos 1 a 3 — el
> armado no necesita credenciales. Vas a poder correr el harness recién
> cuando completes la auth en el paso 4.

---

## 1 · Bajá el repo de la clase 4

Si tu equipo te dio acceso al repositorio:

```bash
git clone <URL-DEL-REPO>
cd clase4-harness-skills-mcp
```

Si te lo entregaron como `.zip`, descomprimilo y entrá al directorio.

```
clase4-harness-skills-mcp/
├── README.md
├── INSTALL-HARNESS-N8N-CLI.md     ← este archivo
├── .env.example
├── skill-analista-operativo/      ← la Skill que vamos a cargar
├── n8n/                           ← el flujo del cierre
├── mcp/                           ← los MCPs de la demo
└── specs/                         ← las especificaciones (te servirá leerlas)
```

---

## 2 · Instalá las dependencias de Python (para los scripts de la Skill)

La Skill trae dos scripts en `skill-analista-operativo/tools/` que necesitan
Python. No los instales en el Python del sistema — vas a ensuciarlo.

```bash
# adentro de clase4-harness-skills-mcp/
python -m venv .venv

# activá el venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate          # macOS / Linux

# instalá las deps
pip install -r requirements.txt
```

> Si el repo no trae `requirements.txt` todavía, instalá a mano lo mínimo:
> ```bash
> pip install httpx python-dotenv
> ```

La primera vez tarda ~30 segundos. Si termina sin errores rojos, estás.

---

## 3 · Conseguí `bios_ops.db` (la base sintética de la clase 1)

La Skill "analista operativo" consulta la base sintética de operaciones de
planta que se generó en la clase 1. **Es sintética — no tiene datos reales
de Bios.**

Dos opciones:

**(a) Ya la tenés de la clase 1.** Si clonaste el repo de S1 y generaste la
base, copiala:

```bash
# desde clase4-harness-skills-mcp/
bash skill-analista-operativo/tools/copiar_db.sh
# o a mano:
cp ../clase1-lab-agentes/bios_ops.db skill-analista-operativo/bios_ops.db
```

**(b) Regenerá la base desde la clase 1.** Sin la base, `bios_ops.py`
responde "no encontré esa planta".

```bash
cd ../clase1-lab-agentes
docker compose exec tablero python -m backend.db.seed --recrear
# o, si no usás Docker:
python -m backend.db.seed --recrear
cp bios_ops.db ../clase4-harness-skills-mcp/skill-analista-operativo/bios_ops.db
cd ../clase4-harness-skills-mcp
```

> La base no se incluye en el repo — es binaria y se versiona el generador,
> no el archivo (mismo candado que S2/S3).

---

## 4 · Configurá `.env`

Copiá la plantilla y completala:

```bash
cp .env.example .env
# abrí .env con tu editor (Notepad, VS Code, nano, lo que sea)
```

Variables que tenés que completar:

```dotenv
BIOS_DB_PATH=skill-analista-operativo/bios_ops.db
# ── RAG · OpenAI Vector Store (no se construye RAG local) ─────────────
# El corpus de documentos de Bios ya está indexado en este vector store de
# OpenAI. La Skill solo recupera — no indexa. El ID ya viene configurado por
# defecto; sólo necesitas proporcionar tu OPENAI_API_KEY.
OPENAI_API_KEY=
OPENAI_VECTOR_STORE_ID=vs_6a7dc97b07ac8191aa9240583a27c133

# Número de fragmentos a recuperar del vector store.
RAG_TOP_K=4

# Cierre n8n — instancia n8n de la AGENCIA (no de Bios)
N8N_API_URL=
N8N_API_KEY=

# MCP de Google Sheets — cuenta Google de la AGENCIA
GOOGLE_SHEETS_DEMO_ID=
```

> **Si no tenés `OPENAI_API_KEY` configurada todavía:** dejá las variables
> del RAG como están (el vector store ID ya viene por defecto). Vas a poder
> correr el primer script recién cuando completes la key, pero el código y
> la base ya están listos. `tools/rag.py` degrada con un mensaje legible.

**Tres reglas que no se negocian:**

- ❌ Nunca pegues una API key en un chat, correo o mensaje.
- ❌ Nunca subas `.env` al git. Ya está en `.gitignore`; no lo saques de ahí.
- ❌ Si una credencial se te escapa, rotala al instante. Borrar el commit
  no basta — el historial de git la conserva.

---

## 5 · Instalá el harness (OpenCode)

> **Por qué OpenCode.** Hoy usamos OpenCode como harness principal (ADR-001
> de la spec 02). El patrón es el mismo en Claude Code y Codex — si tu
> equipo prefiere otro, los pasos equivalentes están al final de esta
> sección.

### 5.1 · Instalación

```bash
npm install -g opencode
```

Verificá:

```bash
opencode --version
```

Si devuelve un número de versión, estás.

### 5.2 · Auth del LLM subyacente

OpenCode usa el LLM que le configures. La auth vive en el archivo de config
del harness, **no** en el `.env` del repo (ese `.env` es sólo para los
scripts de la Skill).

Seguí el wizard de OpenCode la primera vez:

```bash
opencode
```

Te va a pedir elegir proveedor (OpenAI / Anthropic / Azure OpenAI / otro) y
pegar la API key. Si Bios te entrega credenciales Azure OpenAI, elegí Azure
y completá `endpoint`, `api_key`, `deployment` y `api_version` (mismas
variables que en S2).

> **Importante:** la API key del LLM no se pega nunca en el `.env` del repo.
> Vive en el config del harness. Si tenés que mostrar el config a alguien,
> redactá los campos sensibles antes.

### 5.3 · Alternativas: Claude Code, Codex

Si tu equipo prefiere otro harness:

| Harness | Instalación | Notas |
|---|---|---|
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | Requiere cuenta Anthropic. Soporta `SKILL.md` y MCP. |
| **Codex** | Según distribución OpenAI (ver docs oficiales) | Requiere cuenta OpenAI. Soporta MCP. |

El patrón es idéntico: instalás el binario, lo autenticás con tu LLM, le
cargás el `AGENTS.md` del repo y las Skills. Los scripts de
`skill-analista-operativo/tools/` funcionan igual — son Python estándar.

---

## 6 · Cargá la Skill "analista operativo"

### 6.1 · Verificá los scripts primero

Antes de cargar la Skill al harness, verify que los scripts corren solos:

```bash
# con el venv activado
cd skill-analista-operativo
python -m tools.bios_ops --demo
# debería responder los 4 casos de inventario/demanda/pedido/fallas

python -m tools.rag --probar
# debería responder con chunks del vector store si OPENAI_API_KEY está bien,
# o un mensaje legible si no.
cd ..
```

Si `bios_ops.py` falla con "no encuentro `bios_ops.db`", volvé al paso 3.
Si `rag.py` falla con "no encuentro `OPENAI_API_KEY`", revisá
el `.env` — la variable debe estar completa con una key válida de OpenAI.

### 6.2 · Activá la Skill en OpenCode

OpenCode detecta Skills del directorio de skills configurado. Dos caminos:

**(a) Skill local del proyecto.** Si querés que la Skill viva con este repo:
poné (o dejá) `skill-analista-operativo/SKILL.md` en el directorio de skills
que OpenCode escanea para este proyecto. Lo más simple es apuntar la config
de OpenCode a `./skill-analista-operativo/`.

**(b) Skill global.** Si querés que la Skill esté disponible en cualquier
proyecto: copiá `skill-analista-operativo/` al directorio global de skills
de OpenCode (ver `opencode --help` o la documentación oficial para la ruta
exacta según tu OS).

### 6.3 · Probá la Skill desde el harness

Lanzá OpenCode en el repo:

```bash
opencode
```

Y pedile los 3 casos de
[`skill-analista-operativo/ejemplos.md`](./skill-analista-operativo/ejemplos.md):

```
> ¿Cuánto maíz le queda a la planta de Itagüí?
> ¿Cuál es el procedimiento si el molino EQ-ITG-MOL-01 supera 5.5 mm/s de vibración durante más de dos turnos?
> ¿El retraso del pedido PD-24-00871 es por materia prima o por equipos?
```

**Respuestas esperadas** (ver spec 03 para el detalle):
1. *"En Itagüí quedan 320 toneladas de maíz amarillo, bajo el mínimo."*
2. Respuesta con cita: *"Según la Guía de interpretación de lecturas de
   sensor, el turno de mantenimiento debe detener el lote, aislar el
   equipo, notificar al Coordinador de Mantenimiento con copia al
   Director de Planta, y abrir una orden 'urgente'."*
3. Síntesis de dos fuentes: estado del pedido (muelle, turno 6) + política
   de abastecimiento + inventario bajo → *"el retraso es por materia
   prima."*

Si los tres responden, la Skill está funcionando. Es el **Entregable 1**
completado.

---

## 7 · Conectá el MCP de Google Sheets / Drive

> **Cuenta de la agencia, no de Bios.** Estos pasos los hacés con tu propia
> cuenta Google (o la que te asigne la agencia / Bios para tu proyecto).
> Nunca conectes en clase una cuenta Google productiva de Bios sin
> coordinar con TI.

### 7.1 · Creá una hoja de prueba

1. Abrí Google Sheets y creá una hoja nueva llamada
   `Seguimiento Demo Clase 4 Bios`.
2. En la fila 1, poné los encabezados: `Pedido`, `Estado`.
3. Agregá 3 filas de ejemplo:
   - `PD-24-00871` · `en muelle`
   - `PD-24-00902` · `en tránsito`
   - `PD-24-00993` · `entregado`
4. Copiá el ID de la hoja de la URL:
   `https://docs.google.com/spreadsheets/d/<ESTE-ID>/edit` → pegalo en
   `.env` como `GOOGLE_SHEETS_DEMO_ID`.

### 7.2 · Conectá el MCP en OpenCode

Seguí la documentación del MCP de Google Sheets para OpenCode. Lo típico
es:

1. En el archivo de config de OpenCode, agregá una entrada `mcp` con el
   servidor de Google Sheets.
2. Autenticá con OAuth (te va a abrir el navegador la primera vez) o con
   una service account JSON (si tu organización lo prefiere).
3. Dale alcance de lectura/escritura sobre la hoja — o sobre tu Drive,
   según el MCP.

> Los pasos exactos dependen del MCP que elijas (hay varios community MCPs
> para Google Sheets). El `mcp/README.md` trae la configuración de
> referencia que usamos en la agencia.

### 7.3 · Probá lectura y escritura

Con OpenCode abierto:

```
> leé la hoja "Seguimiento Demo Clase 4 Bios" y mostrame las filas
```

Debería devolver las 3 filas. Después:

```
> añadí una fila a esa hoja con pedido PD-24-01050, estado "en muelle"
```

Refrescá la hoja en el navegador — la fila nueva debe aparecer.

Si eso pasa, el MCP está conectado. Es el patrón que **Compras, Logística y
Producción** pueden replicar con sus propias hojas.

---

## 8 · Instalá la CLI de n8n y conectala (cierre)

> **Instancia n8n de la agencia, no de Bios.** Si en tu proyecto vas a
> usar la instancia n8n de Bios, coordiná con TI el acceso en el
> acompañamiento S5-S7. Hoy conectamos la nuestra para aprender el patrón.

### 8.1 · Instalación de la CLI de n8n

La CLI de n8n se distribuye como paquete npm:

```bash
npm install -g n8n-cli
```

> Si el harness que elegiste trae su propia skill `n8n-cli` (es el caso de
> OpenCode con la skill referenciada en `AGENTS.md` §8), podés usar esa
> envoltura en vez del binario directo. Los comandos son equivalentes.

Verificá:

```bash
n8n-cli --version
```

### 8.2 · Autenticá la CLI

```bash
n8n-cli auth:login --url "$N8N_API_URL" --key "$N8N_API_KEY"
```

(los valores salen de tu `.env` — `N8N_API_URL` y `N8N_API_KEY` de la
instancia n8n de la agencia).

Verificá:

```bash
n8n-cli workflows:list
```

Si devuelve una lista (aunque sea vacía), la auth está bien.

### 8.3 · Probá crear y borrar un workflow

```bash
n8n-cli workflows:create --name "prueba install clase 4" --json '{"nodes":[],"connections":{}}'
# te devuelve un ID

n8n-cli workflows:delete --id <ID>
```

Si creó y borró sin error, la CLI está lista para el cierre.

### 8.4 · El cierre (lo que vimos en clase)

El caso del cierre está documentado en
[`n8n/README.md`](./n8n/README.md) y en
[`specs/05-flujo-n8n-cierre.md`](./specs/05-flujo-n8n-cierre.md). Para
replicarlo:

1. Abrí OpenCode en el repo.
2. Pedile al harness que arme el workflow (la instrucción exacta está en
   el guion del facilitador, spec 07, min 102).
3. El harness va a invocar la CLI de n8n para crear el workflow, configurar
   nodos, y activarlo.
4. Verificá en la UI de n8n de la agencia que el workflow apareció.
5. Dispará el webhook de prueba (curl o botón "Test" de n8n).
6. Mirá la hoja `Seguimiento Demo Clase 4 Bios` — la fila nueva debe
   aparecer.

Si eso pasa, tenés el **Entregable 2** completado: una automatización n8n
creada con el harness + CLI de n8n.

> **Plan B si el harness no te arma el workflow:** importá
> `n8n/plantilla-cierre-rescate.json` manualmente desde la UI de n8n
> (`Workflows → Import from File`). El patrón es el mismo; lo que pierdes
> es el "arma hablando" — pero el workflow queda funcionando.

---

## 9 · Lo que NO hace esta instalación (y por qué)

- **No persiste la Skill entre máquinas.** La Skill vive en el repo. Si
  trabajás en otra máquina, cloná el repo y volvé al paso 6.
- **No conecta datos reales de Bios.** Mismo candado de S1/S2/S3: lo que un
  LLM recibe se envía al proveedor. Datos productivos exigen contrato de
  tratamiento con TI y Legal — eso se hace en el acompañamiento, no ahora.
- **No instala Azure MCP Server.** No tenemos cuenta Azure propia sin
  tarjeta de crédito. La configuración comentada está en
  [`mcp/README.md`](./mcp/README.md) para cuando TI te habilite acceso.
- **No es multiagente.** Un harness, una Skill, un MCP. Multiagente es
  tema de acompañamiento.

---

## 10 · Si algo falla

### `opencode: command not found`

No se instaló global. Reinstalá con `npm install -g opencode` y verificá
que tu `PATH` incluye el directorio global de npm (`npm config get prefix`
te lo dice).

### `python -m tools.bios_ops` falla con `ModuleNotFoundError: httpx`

No activaste el venv o no instalaste deps. Volvé al paso 2.

### `No encuentro bios_ops.db en ...`

Falta la base. Volvé al paso 3.

### `tools/rag.py` dice "no encuentro `OPENAI_API_KEY`"

Falta configurar la API key de OpenAI en `.env`. Volvé al paso 4 y
completá `OPENAI_API_KEY` con una key válida. El `OPENAI_VECTOR_STORE_ID`
ya viene por defecto (`vs_6a7dc97b07ac8191aa9240583a27c133`).

### El harness no reconoce la Skill

Revisá que `skill-analista-operativo/SKILL.md` esté en el directorio que
OpenCode escanea (ver paso 6.2). Si el frontmatter tiene un typo, OpenCode
no la carga — abrí el `SKILL.md` y compará con
[`skill-analista-operativo/SKILL.md`](./skill-analista-operativo/SKILL.md)
del repo.

### `n8n-cli auth:login` falla con 401

La key no es válida o la URL no corresponde a la instancia n8n de la
agencia. Verificá `N8N_API_URL` y `N8N_API_KEY` en tu `.env`.

### El MCP de Sheets no lee la hoja

Revisá el ID (`GOOGLE_SHEETS_DEMO_ID`) y los permisos del MCP. Si usaste
OAuth, volvé a autorizar — el token puede haber caducado. Si usaste
service account, verificá que la service account tenga acceso a la hoja
(compartila con el email de la service account desde Google Sheets).

### El harness arma el workflow n8n pero no se ve en la UI

Refrescá la UI de n8n. Si tampoco aparece, verificá que el workflow se creó
en el "environment" correcto (algunas instancias tienen dev/prod). Si no
está, mirá los logs de la CLI: `n8n-cli workflows:list` te dice si está.

---

## 11 · Siguiente paso

Llevate el repo a tu equipo. Cuando quieras adaptar la Skill a tu proyecto
real de Bios (Mantenimiento, Compras, Logística o Producción/TD):

1. **Editá las instrucciones del `SKILL.md`** para que el `when` y las
   reglas de enrutamiento reflejen tu dominio.
2. **Descomentá la tool relevante** en `tools/bios_ops.py` (las firmas son
   las mismas de S2).
3. **Apuntá `OPENAI_VECTOR_STORE_ID`** al vector store de tu corpus (cuando
   construyas el tuyo — el de la agencia ya viene por defecto). Subir
   documentos al vector store es tarea de preproducción, no de la Skill.
4. **Conectá los MCPs que tu proyecto necesite** (Sheets de tu área, Linear
   de TI, Azure cuando lo habilite).

El harness no cambia. La Skill y los MCPs sí. Esa es la lección de hoy: el
agente ya está construido; vos lo operás y lo extendés.

Cuando quieras pasar a producción, conversamos en el acompañamiento S5-S7.
