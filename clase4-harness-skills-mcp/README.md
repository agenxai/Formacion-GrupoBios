# Clase 4 · Harness, Skills y MCP — de la conversación a la ejecución

> **Última sesión formativa** del programa Formación Grupo Bios en IA. Después
> de esta, S5-S7 son acompañamiento de proyectos sin clase preparada. Todo lo
> que se construye acá tiene que quedar **reutilizable directamente** en el
> proyecto real de cada Champion durante el acompañamiento.
>
> **Duración:** 2 horas · **Audiencia:** ~15 personas (núcleo técnico +
> champions no-software) · **Mecánica:** demo guiada con práctica en vivo.

---

## Qué es esta sesión

La sesión que cierra el ciclo formativo. El arco del programa:

| Sesión | Pregunta |
|---|---|
| **S1** | ¿Qué es un agente de IA? |
| **S2** | ¿Cómo se construye un agente? |
| **S3** | ¿Cómo sabe cosas que no le contamos? (RAG) |
| **S4** | **¿Y si el agente ya está construido y yo lo opero?** ← esta |

La respuesta es el **harness** — un agente ya construido que opera el
computador (lee y escribe archivos, corre comandos, itera solo, pide
permiso). Y las dos capacidades que lo extienden hacia los proyectos reales
de Bios: **Skills** (conocimiento empaquetado) y **MCP** (capacidades
externas sin escribir código).

## Los tres entregables

Cada participante se lleva, instalado / creado en su computador o documentado
para replicar:

1. **Una Skill construida y funcionando** — la "analista operativo", que
   orquesta `bios_ops.db` (S1/S2) y el vector store de OpenAI (RAG
   gestionado, no local) para responder preguntas de
   negocio.
2. **Una automatización n8n creada con el harness conectado a la CLI de
   n8n** — el cierre de la clase: el harness arma en 3-5 minutos lo que
   antes tomaba 20-30 minutos de arrastre manual de nodos.
3. **El proceso documentado de instalar y conectar el harness + la CLI de
   n8n** — el [`INSTALL-HARNESS-N8N-CLI.md`](./INSTALL-HARNESS-N8N-CLI.md),
   reproducible sin el facilitador.

## Estructura de la sesión (120 min)

| Bloque | Min | Qué pasa |
|---|---|---|
| Recap + puente | 0–7 | Dudas de S3; arco S1→S2→S3→S4. |
| **Bloque 1 · Harness** | 7–55 | **Transversal** — técnicos y no-técnicos juntos. Qué es un harness vs. framework. Cómo "piensa": loop percibe-decide-ejecuta-observa, `AGENTS.md` como contexto, permisos. **Práctica corta (10-15 min):** todos operan el harness para una tarea cotidiana no relacionada con código. |
| **Bloque 2 · Skills + MCP + cierre n8n** | 55–115 | Anatomía de un `SKILL.md`. Construcción en vivo de "analista operativo" (con red de seguridad preconstruida). MCP: Linear (referencia) + Google Sheets/Drive (demo en vivo) + Azure (conceptual). **Cierre: el harness + n8n-cli arma un flujo real sobre uno de los 4 dominios.** |
| Puesta en común + puente a S5-S7 | 115–120 | "La próxima ya no hay clase: ustedes con su proyecto, nosotros para resolver." |

Detalle minuto a minuto en [`specs/07-guion-facilitador.md`](./specs/07-guion-facilitador.md).

## Qué se necesita antes de empezar

> ⚠️ **Datos sintéticos siempre.** Ningún dato real de Grupo Bios se procesa
> en esta sesión. La Skill consulta `bios_ops.db` (sintético, S1) y el corpus
> del vector store de OpenAI (mismo corpus sintético que se construyó en S3, ahora indexado en OpenAI). La demo de Google Sheets usa una hoja de la
> agencia, no de Bios. La demo del cierre usa la instancia n8n de la agencia.

### Del facilitador (24-48 h antes — ver [`specs/06-operacion-riesgos.md`](./specs/06-operacion-riesgos.md))

- **Harness principal instalado y funcionando** (OpenCode, por ADR-001 de
  [`specs/02-arquitectura.md`](./specs/02-arquitectura.md)). Auth del LLM
  subyacente probada con cuota suficiente.
- **Skill preconstruida cargada** en `skill-analista-operativo/` — es la red
  de seguridad (ADR-003). Los 3 casos de
  [`specs/03-skill-analista-operativo.md`](./specs/03-skill-analista-operativo.md)
  corridos y verificados.
- **`bios_ops.db` accesible** (path estable o copia local). Reutilizado de
  [`../clase1-lab-agentes/bios_ops.db`](../clase1-lab-agentes/bios_ops.db) —
  no se regenera.
- **`OPENAI_API_KEY` configurada y `OPENAI_VECTOR_STORE_ID` apuntando al
  vector store de OpenAI** ya indexado con el corpus de Bios
  (`vs_6a7dc97b07ac8191aa9240583a27c133` por defecto). Si no está, `tools/rag.py`
  degrada con un mensaje legible.
- **MCP de Google Sheets/Drive conectado** al harness, con la cuenta Google
  de la agencia. Hoja `Seguimiento Demo Clase 4 Bios` creada con columnas
  `Pedido`, `Estado` y filas de ejemplo.
- **CLI de n8n instalada y autenticada** contra la instancia n8n de la
  agencia (`N8N_API_URL`, `N8N_API_KEY`).
- **Caso del cierre cerrado** — el TODO de
  [`specs/05-flujo-n8n-cierre.md`](./specs/05-flujo-n8n-cierre.md)
  resuelto. Propuesta recomendada (no vinculante): dominio Logística.
- **`n8n/plantilla-cierre-rescate.json`** generada y probada (plan B del
  cierre).
- **Transcripciones pre-grabadas** de los tres bloques listas para los
  planes B.

### De los participantes (opcional, para montar a la par)

Si un participante quiere seguir la instalación / la Skill en su propia
máquina durante la clase, necesita seguir el
[`INSTALL-HARNESS-N8N-CLI.md`](./INSTALL-HARNESS-N8N-CLI.md) **antes** de
la sesión. No se instala en vivo — comería 25 de los 55 min de práctica.

## Estructura del repo

```
clase4-harness-skills-mcp/
├── README.md                            ← este archivo
├── INSTALL-HARNESS-N8N-CLI.md           ← Entregable 3 · guía de instalación
├── .env.example                         ← plantilla de configuración
├── .gitignore
│
├── skill-analista-operativo/            ← Entregable 1 · la Skill
│   ├── SKILL.md                           frontmatter + instrucciones + cuándo
│   ├── tools/
│   │   ├── bios_ops.py                      consultas a bios_ops.db (reutiliza S1/S2)
│   │   ├── rag.py                            consultas al vector store de OpenAI (SDK)
│   │   └── copiar_db.sh                      trae bios_ops.db desde la clase 1
│   └── ejemplos.md                         los 3 casos de prueba
│
├── n8n/                                 ← Entregable 2 · el flujo del cierre
│   ├── README.md                          caso del cierre (TODO hasta cerrar) + plan B
│   └── plantilla-cierre-rescate.json      plan B del cierre (TODO: generarla)
│
├── mcp/                                 ← Bloque 2 · los MCPs de la demo
│   └── README.md                          Linear, Google Sheets/Drive, Azure
│
└── specs/                               ← 7 especificaciones
    ├── 01-vision-alcance.md
    ├── 02-arquitectura.md
    ├── 03-skill-analista-operativo.md
    ├── 04-mcps-demo.md
    ├── 05-flujo-n8n-cierre.md            ← TODO: cerrar el caso del cierre
    ├── 06-operacion-riesgos.md
    └── 07-guion-facilitador.md
```

## Cómo se conecta con las clases anteriores

| Pieza | Origen | Cómo se reutiliza en S4 |
|---|---|---|
| `bios_ops.db` (11 tablas, 12.497 filas sintéticas) | S1 | La Skill la consulta vía `tools/bios_ops.py` — referenciada por path, no duplicada. |
| 4 tools canónicas (`consultar_inventario`, `consultar_demanda`, `estado_pedido`, `historial_fallas`) | S2 | Reempaquetadas en `tools/bios_ops.py` con las mismas firmas. |
| Corpus + índice RAG (políticas, manuales, procedimientos) | S3 | Ya indexado en el vector store de OpenAI gestionado por la agencia. La Skill lo consulta vía `tools/rag.py` (SDK de OpenAI). |
| Webhook como frontera de integración | S3 | El cierre n8n usa el mismo patrón: webhook dispara, harness arma, workflow ejecuta. |
| `AGENTS.md` como contexto | este repo | Ejemplo autorreferencial del Bloque 1: el archivo que el harness carga. |

**No se reconstruyen piezas.** La sesión reutiliza y enchufa el harness
encima.

## Stack

- **Harness:** OpenCode (ADR-001). Claude Code y Codex mencionados como
  alternativas del mismo patrón.
- **LLM subyacente:** el que use el harness (OpenAI / Anthropic / el
  proveedor configurado).
- **Skill:** `SKILL.md` + scripts Python (`tools/bios_ops.py`, `tools/rag.py`).
- **MCP:** Linear MCP, Google Sheets/Drive MCP, Azure MCP Server
  (conceptual).
- **n8n:** instancia n8n de la agencia + CLI de n8n (skill `n8n-cli`).

## Checklist antes de la clase

**Hazlo 24-48 horas antes, no el día de la sesión.** Si falta algo, no se da
la clase — se reprograma o se ajusta, no se improvisa en vivo.

### Harness y LLM

- [ ] OpenCode instalado y arrancando sin error en la máquina del facilitador.
- [ ] Auth del LLM subyacente probada (API key con cuota suficiente).
- [ ] Los tres bloques corridos de punta a punta (práctica transversal, 3
      casos de la Skill, lectura+escritura de Sheets, cierre n8n).
- [ ] Transcripciones de plan B listas, marcadas como "ejecución
      pre-grabada".

### Skill preconstruida

- [ ] `skill-analista-operativo/SKILL.md` cargado en el harness y
      funcionando.
- [ ] `tools/bios_ops.py` responde los 3 casos.
- [ ] `tools/rag.py` alcanza el vector store de OpenAI
      (`OPENAI_API_KEY` configurada, `python -m tools.rag --probar`
      devuelve chunks reales).
- [ ] `BIOS_DB_PATH` apunta a un archivo existente (abre en modo lectura).

### MCP de Google Sheets / Drive

- [ ] Cuenta Google de la agencia identificada.
- [ ] Hoja `Seguimiento Demo Clase 4 Bios` creada con columnas y filas de
      ejemplo.
- [ ] MCP conectado al harness; auth vigente.
- [ ] Lectura y escritura probadas.
- [ ] Config del harness con tokens redacted listo para proyectar.

### CLI de n8n y cierre

- [ ] CLI de n8n instalada y autenticada contra la instancia n8n de la
      agencia.
- [ ] Verificación: crear → activar → ejecutar → borrar workflow de
      prueba desde la CLI.
- [ ] **Caso del cierre cerrado** (spec 05 TODO resuelto).
- [ ] `n8n/plantilla-cierre-rescate.json` generada y probada.
- [ ] Cierre practicado al menos dos veces, midiendo tiempos (objetivo:
      3-5 min de armado, 15 min totales con narración).

### Acceso de participantes

- [ ] José / líder confirmó acceso al repo de S4 para quienes quieran
      seguir la instalación.
- [ ] `INSTALL-HARNESS-N8N-CLI.md` probado por alguien que no sea el
      facilitador (prueba de fricción cero, preferentemente un Champion
      no-software).
- [ ] Los 4 del núcleo saben que su rol es desbloquear a su mesa en el
      Bloque 2.

### Hardware y salón

- [ ] Laptop probada en el proyector real, con zoom al 125-150%.
- [ ] Terminal con fuente legible desde el fondo del salón.
- [ ] Navegador con: instancia n8n de la agencia (login hecho) + hoja
      `Seguimiento Demo Clase 4 Bios` abierta + config del harness
      redacted.
- [ ] `.env` cargado con `BIOS_DB_PATH`, `OPENAI_API_KEY`,
      `OPENAI_VECTOR_STORE_ID`, `N8N_API_URL`,
      `N8N_API_KEY`, `GOOGLE_SHEETS_DEMO_ID`.

### Plan C global

- [ ] Transcripciones de los tres bloques listas.
- [ ] `n8n/plantilla-cierre-rescate.json` lista para importar manualmente.

> **Si cualquier item no pasa, no se da la clase.** Mismo candado que S2/S3.

## Especificaciones

- [`specs/01-vision-alcance.md`](./specs/01-vision-alcance.md)
- [`specs/02-arquitectura.md`](./specs/02-arquitectura.md)
- [`specs/03-skill-analista-operativo.md`](./specs/03-skill-analista-operativo.md)
- [`specs/04-mcps-demo.md`](./specs/04-mcps-demo.md)
- [`specs/05-flujo-n8n-cierre.md`](./specs/05-flujo-n8n-cierre.md) *(TODO:
  cerrar el caso del cierre)*
- [`specs/06-operacion-riesgos.md`](./specs/06-operacion-riesgos.md)
- [`specs/07-guion-facilitador.md`](./specs/07-guion-facilitador.md)

## Lo que NO hace esta sesión

- **No construye un MCP propio.** Se muestra cómo *conectar* MCPs
  existentes. Construir uno es decisión de proyecto → acompañamiento S5-S7.
- **No demuestra Azure MCP Server en vivo.** No hay cuenta Azure propia sin
  tarjeta de crédito. Mención conceptual únicamente.
- **No carga datos reales de Bios.** Mismo candado de S1/S2/S3: lo que un
  LLM recibe se envía a un proveedor externo; datos productivos exigen
  contrato de tratamiento.
- **No usa la instancia n8n de Bios durante la clase.** La demo del cierre
  usa la instancia n8n de la agencia. El acceso corporativo lo resuelve TI
  de Bios en el acompañamiento.
- **No es multiagente.** Un harness, una Skill, un MCP. Multiagente es
  tema de acompañamiento.

## Qué sigue (S5-S7)

La próxima sesión ya **no hay clase preparada**. S5-S7 es acompañamiento:
cada Champion con su proyecto real, los facilitadores para resolver dudas,
revisar avance, orientar decisiones, identificar bloqueos.

Los tres entregables de hoy son la base:
- la **Skill** se adapta al dominio del Champion;
- la **automatización n8n** se replica con su cuenta corporativa (vía TI);
- la **guía de instalación** se sigue sola para montar el harness en su
  máquina.

---

<p align="center">
  <em>Qypher · Formación en Inteligencia Artificial</em><br>
  <sub>Los datos de esta sesión son sintéticos y no representan las operaciones de Grupo Bios.</sub>
</p>
