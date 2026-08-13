# Cómo montarlo — Clase 3 · RAG

> **Audiencia:** el facilitador (preparación 24–48 h antes) y los técnicos
> que quieran reproducir la sesión por su cuenta.
>
> **Ver spec 07 (`plan_c/`) y spec 05 (`README n8n`) para el paralelo n8n.**

Este documento guía dos caminos:

1. **App visual en Docker** (lo mismo que la clase 1) — recomendado.
2. **App visual sin Docker** (Plan C de spec 07) — para emergencias.

Y por separado:

3. **Servicio Chroma + workflow n8n** — lo que aloja TI de Bios.

> ⚠️ Todos los datos del corpus son **sintéticos**. Ningún dato real de
> Grupo Bios se procesa en esta sesión.

---

## 1 · App visual en Docker (recomendado)

Solo dos cosas: Docker + el `.env` con `N8N_WEBHOOK_URL` (la URL pública
del webhook de Bios).

```bash
# 1 · Clonar y entrar
git clone <url-del-repo>
cd clase3-rag

# 2 · Crear tu .env a partir del ejemplo y editar:
cp .env.example .env
nano .env
#   N8N_WEBHOOK_URL=https://n8n.bios.../webhook/ask
#   (el resto no se necesita para correr el tablero)

# 3 · Levantar
docker compose up --build
#    → Uvicorn running on http://0.0.0.0:8000

# 4 · Abrir el navegador
open http://localhost:8000
```

La primera vez el build tarda 1–2 minutos. Las siguientes veces arranca
en segundos.

> Si Docker no está disponible o falla, seguí el §2 (Plan C).

### Verificar que quedó

```bash
curl -s http://localhost:8000/api/salud | python3 -m json.tool
```

Esperás:

```json
{
  "modo": "vivo",
  "listo": true,
  "n_chunks": 12,
  "modelo_embeddings": "text-embedding-3-small",
  "webhook_url_presente": true,
  "version": "3.0.0"
}
```

- `listo: true` — los archivos `app/data/*.json` existen y cargaron.
- `webhook_url_presente: true` — el `.env` tiene `N8N_WEBHOOK_URL`.

### Otros comandos útiles

```bash
docker compose logs -f tablero        # ver logs
docker compose restart                # tras editar .env
docker compose down                   # detener
```

---

## 2 · App visual sin Docker (Plan C)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.backend.main:app --port 8000 --host 127.0.0.1
```

El frontend lo sirve el mismo FastAPI en `http://localhost:8000`. No hay
que levantar nada aparte, no hay Node, no hay build step.

---

## 3 · Generar los datos pre-bakeados (una sola vez)

Si `app/data/*.json` no existen, el backend arranca con `listo: false` y
todas las pantallas muestran un candado de "datos faltan". Hay que
generarlos en pre-prod, una sola vez.

> **El facilitador** debe hacerlo 24–48 h antes de la clase. Los técnicos
> que repliquen en casa no necesitan hacerlo si el repo ya lo trae.

### 3.1 · Generar el corpus sintético (no usa Azure)

```bash
python3 scripts/generar_corpus.py
# → Validación OK, escrito en app/data/corpus.json
```

### 3.2 · Pre-bakear embeddings + UMAP + similitudes

Necesita credenciales Azure OpenAI en `.env`:

```bash
# .env para pre-bakeo (rellega a este set una vez que lo vas a correr):
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Instalar deps del prebakeo (numpy, sklearn, umap-learn, openai, dotenv):
pip install -r scripts/requirements.txt

# Correr el prebakeo
python3 scripts/prebakear.py
# → Validación OK + RAG-1, RAG-2, RAG-3 en top-3
# → Escrito en app/data/{chunks,embeddings,similitudes,proyeccion_3d,_manifest}.json
```

### 3.3 · Verificar visualmente (auditoría de CI)

```bash
python3 scripts/validar_contraste.py   # WCAG 4.5:1
python3 scripts/auditar_visual.py     # tokens + sin style="..." + Plotly custom
python3 scripts/verificar_vendor.py    # vendors solo los permitidos
```

Los tres deben decir `✓`. Si alguno falla, no se proyecta hasta que se
resuelva (spec 04 § "Candado brutal").

### 3.4 · Prueba con `--dry-run` (sin Azure)

Si querés probar la estructura del frontend y el backend sin usar Azure
(embeddings aleatorios deterministas, **no usables para clase**):

```bash
python3 scripts/prebakear.py --dry-run
# → Escrito app/data/*.json con manifest `dry_run: true`
# → Las pantallas 1–6 cargan
# → La pantalla 7 deja el candado de "sin N8N_WEBHOOK_URL"
```

---

## 4 · Servicio Chroma + workflow n8n

Esto **no** corre en Docker con la app visual. Lo aloja TI de Bios en una
VM/contenedor interno. El facilitador coordina con ellos 1 semana antes
(spec 07 § "Bloqueantes").

```bash
# En la VM de Bios (TI lo ejecuta):
git clone <url-del-repo>
cd clase3-rag
python3 -m venv .venv
.venv/bin/pip install -r n8n/requirements_servicio.txt

# Generar datos pre-bakeados (igual que §3.1 + §3.2)
python3 scripts/generar_corpus.py
python3 scripts/prebakear.py

# Levantar el servicio
.venv/bin/python3 n8n/servicio_rag.py
# → Uvicorn running on http://0.0.0.0:8788
```

Verificación:

```bash
curl http://servidor-rag-bios:8788/salud
# {"status":"ok","chunks_indexados":210,...}

curl -X POST http://servidor-rag-bios:8788/retrieve \
     -H "Content-Type: application/json" \
     -d "{\"query_embedding\": [...1536 floats...], \"top_k\": 4}"
# {"chunks":[...]}
```

Para importar el workflow en n8n, seguir `n8n/README.md`.

---

## 5 · Checklist antes de la clase (24–48 h)

Ver `specs/07-operacion-riesgos.md` § "Checklist 24–48 h antes". Las
condiciones estándar son:

- [ ] `docker compose up --build` levanta sin errores y `"listo": true`.
- [ ] `python3 scripts/validar_contraste.py` ✓ 11/11 pares pasan.
- [ ] `python3 scripts/auditar_visual.py` ✓ OK.
- [ ] `python3 scripts/verificar_vendor.py` ✓ OK.
- [ ] Auditoría visual humana: proyectar las 7 pantallas en el proyector
      real con zoom 125%, pararse a 6 m del monitor, cada concepto
      aterriza al ojo inexperto en menos de 2 segundos. Si una falla,
      se refina o se quita — `plan_c/auditoria_visual.md` es el
      registro del criterio.
- [ ] Webhook del workflow importado y respondiendo desde el navegador
      del facilitador (`curl` de apertura probado en terminal).
- [ ] `servicio_rag.py` corriendo en VM de Bios con `/salud` verde.
- [ ] Las 3 preguntas semilla ejecutadas por webhook y respuestas
      guardadas en `app/data/last_response.json` (plan C).

Si cualquier item no pasa, no se da la clase. Se reprograma o se ajusta
— no se improvisa en vivo.

---

## 6 · Estructura del repositorio

```
clase3-rag/
├── specs/            # 8 especificaciones (spec 01 a spec 08)
│   └── *.md
├── app/
│   ├── backend/      # FastAPI: main.py, datos.py, webhook.py
│   ├── frontend/     # index.html, app.js, plot.js, estilos.css
│   │   └── assets/vendor/   # plotly.min.js, alpine.min.js (vendorizados)
│   └── data/         # chunks.json, embeddings.json, etc (pre-bakeado)
├── n8n/
│   ├── plantilla-agente-bios-rag.json   # workflow para importar
│   ├── servicio_rag.py    # Chroma + FastAPI
│   └── README.md          # cómo importar el workflow
├── notebook/
│   └── 3-rag-a-mano.ipynb     # ejercicio de casas
├── scripts/
│   ├── generar_corpus.py
│   ├── prebakear.py
│   ├── validar_contraste.py
│   ├── auditar_visual.py
│   └── verificar_vendor.py
├── plan_c/           # respuestas/capturas pre-guardadas para el plan C
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── COMO-MONTARLO.md  ← este archivo
```