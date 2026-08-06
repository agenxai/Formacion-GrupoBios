# 03 · Datos — Clase 2

## Naturaleza de los datos

> **Aviso que DEBE aparecer en el README, en `COMO-MONTARLO.md` y al abrir la primera
> conversación de la demo:**
>
> Todos los datos de `bios_ops.db` son **sintéticos**, generados por el seed de la
> clase 1 (`clase1-lab-agentes/backend/db/seed.py`). Los nombres de plantas,
> productos, equipos y clientes son **ficticios** y no representan la red de
> operaciones, los proveedores ni la cartera de clientes de Grupo Bios. Ningún dato
> real de la compañía se procesa en esta sesión.

La razón es la misma de la clase 1: el agente envía el contenido de las tools al
proveedor externo del LLM (Azure OpenAI). Hacerlo con datos productivos exige antes
definir contrato de tratamiento, clasificación de la información y controles de
retención — trabajo que se formaliza en el acompañamiento (S5–S7) cuando un proyecto
lo requiera. La Sesión 2 no normaliza esa práctica.

## Reutilización, no regeneración (ADR-003)

La clase 2 **no** genera datos nuevos. Reutiliza `bios_ops.db` de la clase 1:

- **Once tablas, 12.497 filas sintéticas**, generadas con semilla fija (`42`).
- Los cuatro dominios del negocio ya están modelados: Compras/abastecimiento,
  Demanda/producción, Mantenimiento, Logística/despachos.
- Las cuatro anomalías plantadas ( planta bajo stock, equipo en riesgo, pedido
  atascado, pico de demanda no cubierto) siguen presentes y son el guion de las
  preguntas de la demo.

### Cómo obtener la base

Dos caminos, en orden de preferencia:

1. **Copiar** el archivo `bios_ops.db` desde `clase1-lab-agentes/` al directorio
   `agente-transparente/` de la clase 2. Si ya se generó para la clase 1, es la
   base idéntica que se usó entonces — sin sorpresas.
2. **Regenerar** desde la clase 1 si el archivo no está disponible:
   ```bash
   cd clase1-lab-agentes
   docker compose exec tablero python -m backend.db.seed --recrear
   cp bios_ops.db ../clase2-como-construir-agente/agente-transparente/
   ```
   O sin Docker (README §8 de la clase 1):
   ```bash
   python -m backend.db.seed --recrear
   ```

La base se abre en **modo solo lectura** desde `tools.py`. Un agente no escribe en la
base en esta sesión — misma regla que la clase 1, misma lección de seguridad.

## Esquema (resumen — esquema completo en `clase1-lab-agentes/specs/03-datos.md`)

Once tablas agrupadas en cinco dominios:

| Dominio | Tablas | Qué responde |
|---|---|---|
| **Transversal** | `plantas` | Las 5 plantas: municipio y capacidad. Todo cuelga de aquí. |
| **Compras** | `materias_primas`, `inventario_planta`, `formulas` | Qué materia prima hay y cuánto falta. |
| **Demanda** | `demanda_historica`, `produccion_diaria` | Cuánto se vende y cuánto se fabrica. |
| **Mantenimiento** | `equipos`, `ordenes_mantenimiento`, `lecturas_sensor` | Qué equipo falla y por qué. |
| **Logística** | `pedidos`, `despachos` | Dónde va cada pedido. |

La clase 2 **solo expone cuatro de las siete tools** de la clase 1 — las justas para
que el agente pueda responder una pregunta que encadene dos consultas (el={()=>loop
ReAct}). La simplificación es deliberada: menos tools, menos contexto en el system
prompt, más legible para una demo proyectada. La clase 1 ya demostró las siete; no
hace falta repetirlas.

## Tools expuestas en la clase 2

Cuatro tools, una por dominioexcepto el transversal. Cada una mapea a un reto real
de los Champions:

| Tool | Dominio | Reto Champion | Qué hace |
|---|---|---|---|
| `consultar_inventario(planta, materia_prima=None)` | Compras | Planeación de volúmenes a plantas | Devuelve cantidad, stock mínimo y si está por debajo, por materia prima. |
| `consultar_demanda(planta, materia_prima=None, dias=7)` | Demanda | Planeación de la demanda | Devuelve la demanda histórica/proyectada en toneladas por día. |
| `estado_pedido(pedido_id)` | Logística | Interfaz "tipo aeropuerto" | Devuelve el estado, cuántos pasos faltan y el turno de muelle. |
| `historial_fallas(planta, dias=30)` | Mantenimiento | Predicción de fallas | Devuelve las órdenes de mantenimiento del período, con causa, horas de paro y tendencia de lecturas del sensor. |

**Reglas que aplican a todas** (heredadas del contrato de la clase 1, spec 04):

- Función Python síncrona, anotaciones de tipo completas.
- **La docstring es el prompt que ve el modelo.** Se escribe para el modelo, no para
  el desarrollador — es la lección práctica de la clase 1 que acá se repite.
- Devuelve un `dict` serializable a JSON. Nunca un DataFrame, nunca un objeto.
- El caso "sin resultados" devuelve estructura vacía con un campo `mensaje`, **nunca
  una excepción**. Un agente sabe recuperarse de "no encontré datos"; no sabe hacerlo
  con un stack trace.
- Máximo `LIMITE_FILAS` filas por respuesta, con `truncado: bool`.
- Ninguna escribe: conexión de solo lectura.

> En la Parte 1a, las docstrings se proyectan y se leen: son **el prompt de la tool**.
> En la Parte 2 (n8n), el campo `Description` del nodo Tool juega el mismo papel —
> ahí se ve que el concepto es idéntico: la descripción es lo que ve el modelo.

## Preguntas de la demo

La demo usa **preguntas de negocio** que obligan al agente a encadenar tools (ReAct).
Están elegidas para que la memoria también se vea: la conversación es multi-turno,
no una sola pregunta aislada.

### Conversación insignia (Parte 1a, 1b y Parte 2 — misma en las tres)

La conversación que se proyecta en las tres partes es la misma, para que la
comparación sea directa:

| Turno | Pregunta | Qué debe hacer el agente |
|---|---|---|
| 1 | «¿Cuánto maíz le queda a la planta de Itagüí?» | `consultar_inventario` con `planta=Itagüí, materia_prima=maíz` |
| 2 | «¿Y me alcanza para la demanda proyectada de esta semana?» | `consultar_demanda` con mismos planta y materia, `dias=7`, y comparar |
| 3 | «¿Hay algún equipo de esa misma planta en riesgo de falla?» | `historial_fallas` con `planta=Itagüí` |
| 4 | «¿Cómo va el pedido PD-24-00871?» | `estado_pedido` con `pedido_id=PD-24-00871` |

Por qué esta secuencia:

- El **turno 1** muestra el patrón simple: una tool, una respuesta.
- El **turno 2** muestra el encadenamiento: el agente debe recordar que la pregunta
  anterior fue sobre Itagüí y maíz (**memoria conversacional**), y debe llamar
  `consultar_demanda` para comparar. Es donde la memoria y el loop ReAct se ven
  juntos.
- El **turno 3** extiende el contexto ("esa misma planta") y cambia de dominio.
  Refuerza la memoria y muestra que el agente decide entre tools.
- El **turno 4** es una consulta perezona de Logística, donde el agente change de
  tool sin ambigüedad.

Esta conversación es **el criterio de aceptación** de la spec 05 (validación del
agente): si el agente responde los cuatro turnos correctamente, la clase funciona.

## Constantes garantizadas — contrato con la demo

Las preguntas de la demo contienen identificadores literales que DEBEN existir en
la base. La clase 1 ya los fija en `clase1-lab-agentes/backend/db/constantes.py`:

```python
PLANTA_DEFICIT      = "PL-ITG"        # Planta Itagüí — inventario bajo de maíz
MATERIA_DEFICIT     = "MP-MAIZ"       # Maíz amarillo
EQUIPO_EN_RIESGO    = "EQ-ITG-MOL-01" # Molino, criticidad alta, en Itagüí
PEDIDO_ATASCADO     = "PD-24-00871"   # estado en_muelle, cola de 6 turnos
PLANTA_PICO         = "PL-BUG"        # Planta Buga — día con demanda > producción
```

La clase 2 NO redefine estas constantes. Las importa o las duplica literalmente en
`tools.py`, con un comentario que remite a la clase 1. La base es la misma — los
identificadores son los mismos.

### Verificación (antes de la clase)

El facilitador DEBE ejecutar la conversación insignia completa (4 turnos) en su
máquina con su venv, **24-48 h antes** de la sesión, y verificar:

- El agente llama la tool correcta en cada turno.
- El turno 2 compara inventario contra demanda y concluye que no alcanza (faltan
  ~1.331 toneladas, según el verificación del seed de la clase 1).
- El turno 4 reporta el pedido atascado en `en_muelle` con cola de 6 turnos.

Si cualquiera falla, no se da la clase. La verificación está en el checklist de la
spec 09.

## Diferencias estructurales con la clase 1

| | Clase 1 (spec 03) | Clase 2 (esta spec) |
|---|---|---|
| Generador | `backend/db/seed.py` propio | No hay — se reutiliza |
| Tools expuestas | 7 (`consultar_inventario`, `consultar_demanda`, `estado_pedido`, `historial_fallas`, `consultar_produccion`, `turnos_muelle`, `ejecutar_sql`) | 4 (las cuatro primeras) |
| Preguntas precargadas | 5 (una por dominio + cruzada) | 1 conversación de 4 turnos (insignia) |
| Tablero de "El caso" | Con mapa de tablas en vivo | No hay tablero; se proyecta directamente la conversación |