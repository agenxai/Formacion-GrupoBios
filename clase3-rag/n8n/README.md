# Parte 2 · El agente en n8n (Clase 3)

Esta carpeta contiene el **agente RAG** expuesto por webhook que se usa
en la Parte 2 de la clase 3. Se importa a la instancia n8n cloud de
Bios **antes** de la clase (ADR-007 spec 02) y el facilitador lo abre,
recorre nodo por nodo y ejecuta el `curl` de apertura del bloque n8n.

> ⚠️ Los datos del corpus son **sintéticos**. Ningún dato real de Grupo
> Bios se procesa en esta sesión.

## Archivos

| Archivo | Qué es |
|---|---|
| `plantilla-agente-bios-rag.json` | Export del workflow, listo para `Import from File`. No trae credenciales. |
| `servicio_rag.py` | Servicio FastAPI que mantiene el índice Chroma y responde `/retrieve` al workflow. Vive en VM/contenedor de Bios. |
| `requirements_servicio.txt` | Dependencias del servicio (`fastapi`, `chromadb`, …). |

## Pipeline del workflow (spec 05)

```
┌──────────────┐     ┌────────────┐     ┌─────────────────┐     ┌────────────┐
│ Webhook      │ ──▶ │ Embeddings │ ──▶ │ HTTP Request    │ ──▶ │ AI Agent   │
│ Trigger      │     │ (Azure    │     │ (servicio Chroma│     │ (Azure +   │
│ POST /ask    │     │  query)   │     │  /retrieve)    │     │  memoria)  │
└──────────────┘     └────────────┘     └─────────────────┘     └─────┬──────┘
                                                                            ▼
                                                                  ┌────────────┐
                                                                  │ Respond to │
                                                                  │ Webhook    │
                                                                  └────────────┘
```

El agente reusa la `Window Buffer Memory` de la clase 2 (ADR-008) y
combina la nueva tool `retrieve_docs` con las 4 tools de S2
(`consultar_inventario`, `consultar_demanda`, `estado_pedido`,
`historial_fallas`) — estas últimas siguen vivas vía
`servicio_tools.py` de la clase 2.

## Cómo levantar el servicio Chroma (`servicio_rag.py`)

```bash
cd clase3-rag
python3 -m venv .venv
.venv/bin/pip install -r n8n/requirements_servicio.txt

# Necesita chunks.json + embeddings.json generados por pre-bakeo
python3 scripts/generar_corpus.py
python3 scripts/prebakear.py                # con credenciales Azure

.venv/bin/python3 n8n/servicio_rag.py
# [servicio_rag] Uvicorn running on http://0.0.0.0:8788
```

Verificación rápida:

```bash
curl http://localhost:8788/salud
# {"status":"ok","chunks_indexados":210,...}

curl -X POST http://localhost:8788/retrieve \
     -H "Content-Type: application/json" \
     -d '{"query_embedding": [/* 1536 floats */], "top_k": 4}'
```

> **Si chromadb no está instalado** el servicio degrada a "in-memory"
> (coseno manual sobre embeddings.json pre-bakeado). Funciona para la
> demo pero no es la arquitectura productiva — Chroma debería estar en
> la VM de Bios.

## Importación del workflow en n8n (24–48 h antes)

Bloqueante — coordinar con TI de Bios (spec 09 checklist):

1. Entrar a la instancia n8n de Bios con un usuario que pueda importar
   workflows.
2. `Workflows → Import from File` → seleccionar
   `plantilla-agente-bios-rag.json`.
3. Abrir cada nodo con credencial de Azure:
   - **Embeddings (Azure)** — credencial `Azure OpenAI API`,
     deployment `text-embedding-3-small`.
   - **AI Agent** — credencial `Azure OpenAI API`, deployment `gpt-4o-mini`.
4. En **Retrieve (Chroma)**, reemplazar `http://servidor-rag-bios:8788`
   por la URL real donde corre `servicio_rag.py` (coordinada con TI).
5. Guardar el workflow y **activarlo** (toggle `Active`).
6. Probar el webhook desde terminal:

   ```bash
   curl -X POST https://n8n.bios.../webhook/ask \
        -H "Content-Type: application/json" \
        -d '{"pregunta": "Si Itagüí declara stock crítico de maíz, ¿cómo procede Compras?"}'
   ```

   Respuesta esperada: JSON con `respuesta` y `citas` con
   `comp_politica_abastecimiento` en top-1.

Si la importación falla o la credencial no está, **la Parte 2 no se da** —
se proyecta la transcripción pre-armada (plan C, spec 07). No se
improvisa.

## Herramientas del agente

| Tool | Tipo | Origen |
|---|---|---|
| `retrieve_docs` | Tool del nodo AI Agent | Llama al servicio Chroma (`/retrieve`) |
| `consultar_inventario` | Tool del nodo AI Agent | Llama a `servicio_tools.py` de S2 |
| `consultar_demanda` | Tool del nodo AI Agent | Llama a `servicio_tools.py` de S2 |
| `estado_pedido` | Tool del nodo AI Agent | Llama a `servicio_tools.py` de S2 |
| `historial_fallas` | Tool del nodo AI Agent | Llama a `servicio_tools.py` de S2 |

> Si `servicio_tools.py` de S2 **no está** corriendo en la VM de Bios
> (no se reactivo desde la clase 2), los participantes lo pueden ver caer
> y el facilitador muestra solo `retrieve_docs` + explica que las tools
> de S2 hay que reactivarlas. No bloquea la clase — la lección del
> webhook se da igual; las tools operativas son 4 bonus demonstrate.

## System prompt (legible aquí para referencia)

```
Sos un agente de operaciones de Grupo Bios. Respondes en español.

Tenés dos tipos de conocimiento:

1. Datos operativos (inventario, demanda, fallas, pedidos): consultá
   SIEMPRE las tools (consultar_inventario, consultar_demanda,
   estado_pedido, historial_fallas). NUNCA inventes una cifra operativa.

2. Procedimientos, políticas, manuales: consultá la tool
   `retrieve_docs`. NUNCA inventes un procedimiento. Si la tool no
   devuelve nada relevante, decís "no encontré documentación sobre eso".

REGLA DE ORO:
Cuando respondas algo que salió de `retrieve_docs`, citás el documento
fuente y el chunk. Cuando respondas algo que salió de una tool
operativa, decís la cifra. Si la info no está en tools ni en docs,
decís "no tengo esa información".

Respondés breve y operativo.
```

## Equivalencias pedagógicas (la tabla que se proyecta al cierre)

| App visual (Parte 1) | Workflow n8n (Parte 2) |
|---|---|
| Pantalla 1 — El problema | Webhook mismo: RAG resuelve el problema |
| Pantalla 2 — Chunking | pre-prod `scripts/prebakear.py` |
| Pantalla 3 — Embeddings | Nodo Embeddings (Azure) en vivo |
| Pantalla 4 — Espacio 3D | no aparece (solo visualización) |
| Pantalla 5 — Vector DB | Servicio Chroma vía HTTP Request |
| Pantalla 6 — Retrieval | HTTP Request devuelve top-K |
| Pantalla 7 — Generación | AI Agent + Respond to Webhook |

Al cierre: *"Miren la tabla. El workflow de n8n es la pipeline de las 7
pantallas. Lo único que no aparece es el plot 3D — porque en producción
no se hace, es solo visualización."*