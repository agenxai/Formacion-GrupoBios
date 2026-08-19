# Ejemplos — Skill "analista operativo"

Los tres casos de prueba que se corren en el Bloque 2 de la clase 4, y que
cualquier Champion puede correr después para validar su Skill.

> **Los tres casos aplican la REGLA DE DOBLE CONSULTA** — toda pregunta de
> negocio se responde consultando las dos familias (datos + documentos)
> antes de contestar. La diferencia entre los casos es el peso relativo de
> cada familia, no si se llama o no.

Para correrlos: cargá la Skill en el harness (ver
[`../INSTALL-HARNESS-N8N-CLI.md`](../INSTALL-HARNESS-N8N-CLI.md)) y pegá las
preguntas. Las respuestas esperadas están abajo — si la Skill las reproduce,
está funcionando.

---

## Caso 1 — pregunta de inventario (doble consulta: dato + norma)

**Pregunta:**
> ¿Cuánto maíz le queda a la planta de Itagüí?

**Comportamiento esperado (REGLA DE DOBLE CONSULTA):**
- El harness invoca `consultar_inventario(planta="Itagüí",
  materia_prima="maíz")` → familia A (dato).
- El harness invoca `retrieve_docs(consulta="cobertura mínima materia
  prima inventario stock crítico", dominios=["comp"])` → familia B (norma).
- Respuesta **sintetizada**: *"En Itagüí quedan 320 toneladas de maíz
  amarillo, bajo el mínimo de 1190 t que define la política de
  abastecimiento. Según el manual de volúmenes de Compras, un stock bajo el
  mínimo dispara el reabastecimiento con lead time de 21 días. [Manual de
  volúmenes de Compras; consultar_inventario]."*

**Si falla:** revisá `BIOS_DB_PATH` (¿apunta a un archivo existente?) y que
`tools/bios_ops.py` arranca con `python -m tools.bios_ops --demo`.

> Aunque la pregunta parece "sólo datos", la REGLA DE DOBLE CONSULTA obliga
> a traer también la norma que enmarca la cifra — el dato solo no es una
> respuesta.

---

## Caso 2 — pregunta de procedimiento (doble consulta: norma + dato)

**Pregunta:**
> ¿Cuál es el procedimiento si el molino EQ-ITG-MOL-01 supera 5.5 mm/s de
> vibración durante más de dos turnos?

**Comportamiento esperado (REGLA DE DOBLE CONSULTA):**
- El harness invoca `retrieve_docs(consulta="umbral vibración molino
  criticidad alta procedimiento alerta roja", dominios=["mant"])` →
  familia B (norma).
- El harness invoca `historial_fallas(planta="Itagüí", dias=30)` → familia
  A (dato actual — ¿el molino está realmente en riesgo?).
- Respuesta **sintetizada con cita**: *"Según la Guía de interpretación de
  lecturas de sensor, el turno de mantenimiento debe detener el lote en
  curso, aislar el equipo, notificar al Coordinador de Mantenimiento con
  copia al Director de Planta, y abrir una orden de mantenimiento de tipo
  'urgente'. En los últimos 30 días, Itagüí registra [N] correctivos en
  molinos — [sí/no] hay patrón activo. [Guía de interpretación de lecturas
  de sensor, chunk 2; historial_fallas]."*

**Si falla:** revisá que `OPENAI_API_KEY` esté configurada en `.env` y que
el vector store `OPENAI_VECTOR_STORE_ID` tenga el corpus indexado. Si no
es así, `tools/rag.py` degrada con un mensaje legible — la Skill debe
responder *"no encontré documentación sobre eso"*.

---

## Caso 3 — pregunta cruzada (N5 de S1)

**Pregunta:**
> ¿El retraso del pedido PD-24-00871 es por materia prima o por equipos?

**Comportamiento esperado (doble consulta por definición):**
- El harness invoca `estado_pedido(pedido_id="PD-24-00871")` → familia A.
- El harness invoca `retrieve_docs(consulta="causa retraso despacho materia
  prima abastecimiento equipos", dominios=["logi","comp"])` → familia B.
- Respuesta **sintetizada con ambas fuentes**: *"El pedido PD-24-00871 está
  en muelle, en cola turno 6. La política de abastecimiento indica que un
  retraso en muelle con inventario bajo de materia prima se escala a
  Compras; si el inventario está en mínimo, el retraso se atribuye a
  materia prima. Itagüí reporta 320 t de maíz, bajo mínimo — el retraso es
  por materia prima. [Política de abastecimiento, chunk 3;
  estado_pedido]."*

**Si falla:** el caso 3 es el más difícil. Si los casos 1 y 2 pasan pero el
3 no, la Skill está bien enrutable pero la síntesis falla — suele ser el
system prompt del harness o las instrucciones del `SKILL.md` que no
enfatizan suficientemente la REGLA DE DOBLE CONSULTA. Ajustá las reglas 1-2
del `SKILL.md` ("retrieve_docs se llama SIEMPRE").

> El caso 3 es el más importante para enseñar — es la pregunta N5 de S1,
> donde el cruce de dominios es explícito. Si no se resuelve en vivo, el
> facilitador cambia a la Skill preconstruida y lo corre ahí.

---

## Cómo extender para tu dominio (Champions)

La Skill es una plantilla. Cada Champion la adapta a su dominio:

| Dominio | Tools de la familia A | `dominios` por defecto en `retrieve_docs` |
|---|---|---|
| **Mantenimiento** | `historial_fallas` (+ `lecturas_sensor` si lo traés de S1) | `["mant"]` (o `["mant","comp"]` si toca abastecimiento de repuestos) |
| **Compras** | `consultar_inventario` + `consultar_demanda` | `["comp"]` (o `["comp","logi"]` si toca despacho) |
| **Logística** | `estado_pedido` + `turnos_muelle` | `["logi"]` (o `["logi","comp"]` si toca abastecimiento) |
| **Producción / TD** | `consultar_demanda` + `consultar_produccion` | `["prod"]` (o `["prod","comp"]` si toca inventario) |

La adaptación es **editar las instrucciones del `SKILL.md` y descomentar
la tool relevante** — no reescribir el loop. El loop lo provee el harness.

> Los 4 dominios del corpus (`mant`, `comp`, `logi`, `prod`) ya están
> indexados en el vector store de OpenAI. Cada documento del corpus tiene
> el atributo `dominio` — por eso `retrieve_docs` puede filtrar. Si tu
> proyecto añade documentos nuevos, subilos al vector store con el
> atributo `dominio` correcto y la Skill los encontrará sin cambios.
