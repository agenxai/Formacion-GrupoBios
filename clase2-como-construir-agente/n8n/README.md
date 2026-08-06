# Parte 2 · El mismo agente en n8n

Esta carpeta contiene la Parte 2 de la clase: el **mismo agente ReAct con
memoria** de las Partes 1a/1b, como workflow visual de n8n. Se importa a la
instancia n8n cloud de Bios **antes** de la clase (ADR-006 — no se arma en
vivo) y en el minuto 53 el facilitador lo abre, lo recorre nodo por nodo y
ejecuta la conversación insignia.

> ⚠️ Los datos de `bios_ops.db` son **sintéticos**. Ningún dato real de Grupo
> Bios se procesa en esta sesión.

## Archivos

| Archivo | Qué es |
|---|---|
| `plantilla-agente-bios-react.json` | Export del workflow, listo para `Import from File`. No contiene credenciales. |
| `servicio_tools.py` | Servicio HTTP liviano que expone las 4 tools de `agente-transparente/tools.py`. Los nodos Tool del workflow lo llaman. |

## Decisión de conexión a datos (spec 06)

Se implementó la **opción 1 (recomendada): servicio liviano de tools.** Las
herramientas de n8n hacen `POST` a `servicio_tools.py`, que importa y ejecuta
las **mismas funciones** de `agente-transparente/tools.py` — la consulta SQL,
el whitelisting y el manejo de "no encontré" no se duplican. Si las Partes 1
y 2 responden distinto, el problema no puede estar en la lógica de las tools:
es la misma.

## Cómo levantar el servicio de tools

```bash
cd clase2-como-construir-agente
python n8n/servicio_tools.py
# [servicio_tools] Escuchando en http://0.0.0.0:8788
```

Verificación rápida:

```bash
curl http://localhost:8788/salud
curl -X POST http://localhost:8788/tools/consultar_inventario \
     -H "Content-Type: application/json" \
     -d '{"planta": "Itagüí", "materia_prima": "maíz"}'
```

Requiere `bios_ops.db` copiada en `agente-transparente/` (paso 4 de
`COMO-MONTARLO.md`). No necesita credenciales de Azure: solo lee la base
sintética, en modo solo lectura.

### Cómo lo alcanza la instancia n8n cloud de Bios

El n8n cloud de Bios no puede llamar a `localhost` del facilitador. Dos
caminos, a coordinar con TI de Bios (bloqueante del checklist, spec 07):

1. **(Preferido) Alojarlo en infraestructura de Bios** — una VM o contenedor
   interno que TI pueda levantar con `python n8n/servicio_tools.py` y la base
   sintética al lado. La URL interna resultante se pone en los 4 nodos Tool.
2. **Túnel temporal durante la clase** (p. ej. el que apruebe TI de Bios).
   Solo mientras dura la demo — el servicio no queda expuesto después.

En ambos casos: el servicio solo expone 4 consultas de solo lectura sobre
datos sintéticos. Aún así, se apaga al terminar la clase — es una demo, no un
despliegue.

## Importación en n8n (24–48 h antes — checklist spec 07)

1. Entrar a la instancia n8n de Bios con un usuario que pueda importar
   workflows.
2. `Workflows → Import from File` → seleccionar
   `plantilla-agente-bios-react.json`.
3. Abrir el nodo **Azure OpenAI Chat Model** y seleccionar la credencial
   `Azure OpenAI API` ya registrada por TI (el JSON no la trae — n8n exporta
   referencias, no secrets). Verificar deployment `gpt-4o-mini` y API version
   `2024-10-21`.
4. En los **4 nodos Tool**, reemplazar `HOST-SERVICIO-TOOLS:8788` por la URL
   real donde corre `servicio_tools.py`.
5. Guardar y abrir el chat del workflow. Ejecutar el turno 1 de la
   conversación insignia y verificar la respuesta:

   > «¿Cuánto maíz le queda a la planta de Itagüí?»
   > → 320 toneladas de maíz amarillo, bajo el mínimo (1.190 t).

Si la importación falla o la credencial no está, **la Parte 2 no se da** — se
proyecta la transcripción pre-armada (plan C, spec 07). No se improvisa.

## La conversación insignia (la misma de las Partes 1a/1b)

| Turno | Pregunta | Tool esperada |
|---|---|---|
| 1 | ¿Cuánto maíz le queda a la planta de Itagüí? | `consultar_inventario` |
| 2 | ¿Y me alcanza para la demanda proyectada de esta semana? | `consultar_demanda` (memoria: Itagüí + maíz) |
| 3 | ¿Hay algún equipo de esa misma planta en riesgo de falla? | `historial_fallas` (memoria: Itagüí) |
| 4 | ¿Cómo va el pedido PD-24-00871? | `estado_pedido` |

La memoria (`Window Buffer Memory`, sessionId `bios-clase2`, ventana de 10
turnos) es lo que permite que los turnos 2 y 3 no repitan "Itagüí" ni "maíz".

## Equivalencias pedagógicas (la tabla que se proyecta al cierre)

| Concepto | Python (Parte 1a/1b) | n8n (Parte 2) |
|---|---|---|
| Cerebro (LLM) | `AzureChatOpenAI` en `cliente.py` | Nodo *Azure OpenAI Chat Model* |
| Herramientas | funciones en `tools.py` + `TOOLS_FUNC` | Nodos *Tool* conectados al *AI Agent* |
| Prompt de cada tool | la docstring de la función | campo *Description* del nodo Tool |
| Schema de parámetros | JSON en `SCHEMAS` | *Placeholders* del nodo Tool |
| Memoria | `Memoria` (lista de mensajes) | Nodo *Window Buffer Memory* |
| Loop ReAct | `loop.py` (1a) / `create_react_agent` (1b) | El nodo *AI Agent* lo hace internamente |
| Interfaz | `chat.py` (bucle de `input()`) | El *Chat Trigger* es la interfaz |

Al cierre: *"El agente es el mismo. Lo que cambia es el medio. Si lo
entienden en uno, lo entienden en el otro."*
