# AGENTS.md — Formación Grupo Bios en IA

> **Para qué es este archivo.** Cada vez que hablemos de las formaciones, este documento
> es el contexto de fondo: quién es el cliente, quiénes son los participantes, qué ya
> dimos, qué falta y cómo funciona nuestro stack pedagógico. Léelo antes de cualquier
> iteración sobre las clases.

---

## 1. El cliente

**Grupo Bios** — empresa líder del sector Agro en Colombia. Grande e importante dentro
del agro nacional. El programa de formación lo recibe el **equipo de Innovación** del
área, con el objetivo de fortalecer conocimientos y capacidades en Inteligencia
Artificial, especialmente en **IA generativa, automatización y sistemas agénticos**.

El equipo quiere **llevar agentes de IA a producción** sobre problemas reales del
negocio, no quedarse en demostraciones aisladas.

---

## 2. Los participantes

Grupo de **~15 personas**, heterogéneo por diseño:

- **Núcleo (~4 personas):** nivel avanzado en desarrollo y capacidades técnicas
  consolidadas. Son los que desbloquean a su mesa y pueden llevar retos ampliados.
- **Champions (~11 personas):** niveles de experiencia heterogéneos. Algunos con
  conocimientos sólidos en desarrollo y aproximación previa a IA; otros en proceso de
  fortalecimiento técnico y requieren mayor acompañamiento.

**Dos poblaciones por perfil profesional:**

| Perfil | Quiénes | Qué exigen |
|---|---|---|
| **Software / dev** | Ingenieros de software, TI, transformación digital con base sólida de código | Prácticas con código (Python + LangChain/LangGraph). No pueden quedar esperando. |
| **No-software** | Agrónomos, ingenieros industriales, economistas. Entienden los conceptos pero no viven de código | Prácticas en **n8n** (low-code). Llegan a la misma comprensión conceptual sin pelear con sintaxis. |

**Características transversales del grupo (observadas en clase 1):**

- Conocimientos previos en tecnología, desarrollo y transformación digital.
- Alta capacidad de apropiación de conceptos técnicos y metodologías avanzadas.
- Niveles de madurez práctica en IA heterogéneos.
- Interés en IA generativa, automatización y sistemas agénticos.
- **Muy participativos**: preguntan, se esfuerzan por entender, dinamizan la clase.
  Esto hizo que la clase 1 se fuera en tiempo de teoría y no alcanzara la práctica.

**Decisión pedagógica clave:** atender a ambas audiencias igual. A los de software,
práctica con código. A los no-software, práctica en n8n. La teoría se da **a la par** de
la práctica (en la misma sesión, intercalando concepto y ejecución), no como bloque
separado previo.

---

## 3. Los retos reales del negocio

Los Champions trabajan sobre **proyectos reales asignados**. La filosofía es ir **de
menos a más**: crear un prototipo → volverlo funcional → conectar/automatizar datos →
conectar capacidades agénticas.

| Área | Reto | Datos clave |
|---|---|---|
| **Mantenimiento** | Predicción sobre fallas de equipos | Historial de fallas, lecturas de sensor |
| **Compras** | Rediseñar el proceso de planeación y asignación de volúmenes/cantidades a plantas | Inventario por planta, demanda |
| **Logística** | Interfaz de clientes "tipo aeropuerto": ver dónde está el pedido, turnos que faltan, etc. | Estado de pedido, turnos de muelle. (Es un caso N3 bien hecho, no necesita multiagente.) |
| **Producción / Transformación Digital** | Planeación de la demanda partiendo de datos existentes y conexión con indicadores clave | Demanda, producción |

El laboratorio de la clase 1 ya modela estos cuatro dominios con un dataset sintético
(`bios_ops.db`) para que cada Champion pueda tirar del hilo de su caso.

---

## 4. El programa (visión general)

**Duración:** 14 horas · 7 sesiones × 2 horas.
**Stack:** Python + LangChain/LangGraph + N8N.
**Objetivo final:** que el equipo de Innovación lleve agentes de IA a sus proyectos
reales y los evolucione hacia producción.

### Estructura aprobada por el cliente (decision de José, sponsor de Bios)

El programa se divide en **dos fases**:

- **Sesiones 1–4: formación con clase preparada.** Los 4 módulos formativos que
  diseñamos; aquí entregamos concepto + práctica estructurada.
- **Sesiones 5–7: acompañamiento de proyectos.** Mismo día y horario, pero **sin clase
  preparada**. Los facilitadores estamos para resolver dudas y revisar el avance de los
  proyectos de los Champions, ya aplicando lo visto en S1–S4.

**Qué encierra el acompañamiento (S5–S7):**
- Resolver dudas técnicas durante el desarrollo.
- Revisar el avance y la arquitectura de cada proyecto.
- Orientar decisiones de implementación.
- Identificar bloqueos o riesgos.
- Validar que lo desarrollado esté alineado con las buenas prácticas vistas.

### Implicación decisiva para el diseño

Con solo **3 sesiones formativas más** (S2, S3, S4) que alimentarán **3 sesiones de
apoyo** (S5-S7), el equipaje técnico que reciben los Champions antes de quedar autónomos
se comprime en S2-S4. Eso fuerza a que cada sesión formativa entregue **algo funcional**
sobre el proyecto real del Champion, no una demos aislada, porque en S5 ya estarán
construyendo solos y en S6-S7 se consolida.

La progresión natural que buscaron ellos ("de menos a más") encaja perfectamente en
3 sesiones de formación:
- **S2 →** prototipo funcional (primer agente con tools).
- **S3 →** datos (memoria + RAG).
- **S4 →** agéntico (multiagente / Skills+MCP / agentes pre-construidos).
- **S5-S7 →** acompañamiento de la construcción real.

### Plan original (referencia, ya superado)

El temario original asumió "15 ingenieros técnicos" con 7 sesiones formativas (Memoria,
RAG, Skills/MCP, Hermes/OpenClaw, Harness, Spec Driven, Observabilidad). La realidad del
grupo y la decisión de José recortan la formación a S2-S4 y mueven S5-S7 a apoyo. Los
temas que caen del programa formativo (Harness, Spec Driven, Observabilidad) **pueden**
atenderse de forma puntual dentro del acompañamiento cuando un proyecto lo requiera, no
como bloque docente.

| Sesión | Tema original | Tema re-pensado | Estado |
|---|---|---|---|
| 1 | Agentes y Arquitecturas Multiagénticas | = (solo teoría dada) | ✅ Dada |
| 2 | Memoria, RAG y Context Engineering | 🔜 Por iterar | A definir |
| 3 | Skills, MCPs y Harness Engineer (teórico) | 🔜 Por iterar | A definir |
| 4 | Asistentes Personales y Coworkers — Hermes / OpenClaw | 🔜 Por iterar | A definir |
| 5 | Harness Engineer | **Acompañamiento de proyectos** | Sostenimiento |
| 6 | Spec Driven Development | **Acompañamiento de proyectos** | Sostenimiento |
| 7 | Observabilidad y Seguridad | **Acompañamiento de proyectos** | Sostenimiento |

> Iteramos sesión por sesión. Empezamos por la clase 2.

---

## 5. Estado de la clase 1 (lo que ya pasó)

**Contenido dado (teoría):** fundamentos de agentes de IA — qué es un agente vs. LLM,
componentes (modelo/herramientas/memoria), niveles de agencia (N1–N5), patrones (ReAct,
Plan-and-Execute, Router), function calling en detalle, arquitecturas multiagente
(supervisor, jerárquica, network, custom).

**Material:** `Notas de Clase 1 - Agentes.md` (ebook) + diapositivas `Clase1.html`/PDF.

**Práctica prevista pero NO ejecutada en vivo por tiempo:** el **Tablero de Agencia** —
app web (`localhost:8000`) que ejecuta los 5 niveles en paralelo sobre datos sintéticos
de operaciones de una planta, más un notebook (Jupyter) con los 5 niveles en Python
plano y un taller con `# TODO`. Se dejó como **material de estudio autónomo**.

**Lecciones de la clase 1:**

- El grupo es muy participativo y eso consume tiempo — asumirlo, no pelearlo.
- No hubo tiempo para la parte práctica; la práctica se postergó.
- Hay que llegar a las dos audiencias (código y n8n) con prácticas paralelas.
- La teoría va **intercalada** con la práctica, no como bloque aparte.

**Laboratorio de la clase 1** (en `clase1-lab-agentes/`):

- App FastAPI + Jupyter en Docker. 5 niveles de agencia sobre `bios_ops.db` (11 tablas,
  12.497 filas sintéticas). Dominios: Mantenimiento, Compras, Logística, Producción/TD.
- Vistas del tablero: "El caso" (contexto), "Paso a paso" (un nivel a la vez),
  "Comparación" (5 columnas en paralelo), "Detalle" (traza + system prompt editable).
- Notebook explicado (`1-los-cinco-niveles-explicado.ipynb`) + taller con TODOs.
- Modo replay (sin API key) con trazas pregrabadas. Control de gasto y concurrencia.
- Especificaciones muy cuidadas en `specs/` (visión, arquitectura, datos, contratos,
  niveles, identidad visual, frontend, notebook, operación/riesgos, guion facilitador).

---

## 6. Decisiones pedagógicas acordadas (para iterar sesión a sesión)

1. **Doble vía en cada sesión:** técnicos en Python/LangChain/LangGraph; no-software en
   n8n. Ambos resuelven el mismo concepto en su herramienta.
2. **Vías paralelas en la misma sesión:** un facilitador, concepto y luego ambos grupos
   practican a la par, con momentos de puesta en común. Requiere 2h muy cronometradas.
3. **Teoría a la par de la práctica:** no hay bloque teórico largo separado. Se intercala
   concepto → ejecución → concepto.
4. **Ir de menos a más:** prototipo → funcional → datos → agéntico.
5. **Proyectos reales:** cada Champion trabaja sobre su caso de Bios.
6. **Recap corto: ~10-15 min** de dudas de la sesión anterior y directo al tema nuevo.
   La práctica pendiente de la clase 1 queda como ejercicio autónomo.
7. **Progresión sin tirar código:** cada sesión parte del trabajo de la anterior.

---

## 7. Estructura de carpetas

```
Formacion-GrupoBios/
├── AGENTS.md                    ← este archivo
├── README.md                    ← descripción del laboratorio de la clase 1
└── clase1-lab-agentes/          ← laboratorio de la clase 1 (tablero + notebook)
    ├── Notas de Clase 1 - Agentes.md   ← ebook de la clase 1
    ├── Clase1.html / .pdf              ← diapositivas
    ├── specs/                          ← 10 especificaciones
    ├── backend/                        ← FastAPI + niveles N1-N5 + tools
    ├── frontend/                       ← tablero web
    ├── notebook/                       ← Jupyter (explicado)
    ├── scripts/                        ← validaciones
    └── images/                         ← diagramas del ebook

../resumen-ejecutivo.md          ← plan original del programa (7 sesiones)
../temario.md                   ← temario detallado original
```

> La carpeta `clase2-*` todavía no existe. La iremos definiendo.

---

## 8. Stack y herramientas del programa

- **LLMs:** OpenAI (gpt-4o-mini como default), Anthropic como alternativa.
- **Frameworks:** LangChain, LangGraph, Pydantic, OpenAI SDK.
- **Low-code:** **n8n** (orquestación para no-software y para integrar flujos existentes
  de Bios). Skill `n8n-cli` disponible para operar instancias n8n desde el CLI.
- **Vector DBs:** ChromaDB (local), Pinecone/Weaviate (para producción).
- **Observabilidad:** LangFuse (open source), LangSmith.
- **Agentes pre-construidos:** Hermes Agent, OpenClaw (sesión 4).
- **Testing:** pytest, DeepEval, LangSmith Evaluations.
- **Contenerización:** Docker + docker-compose (laboratorio de clase 1).

---

## 9. Convenciones para iterar

- **Idioma:** español (todas las clases y materiales van en español).
- **Datos sintéticos primero:** nunca cargar datos reales de Bios hasta resolver
  contrato de tratamiento y clasificación de la información (sesiones 2 y 7).
- **Audiencia dual:** todo material práctico debe tener **doble versión** (código +
  n8n) para la misma idea conceptual.
- **Progresión Narrada:** incorporar a los profesionales de la sección 4 en trabajos más conceptuales para que tengan rol de co-facilitadores.
- **Documentación Spec-driven:** el laboratorio de la clase 1 tiene 10 specs muy
  cuidadas. Es el estándar de calidad a mantener: cada clase nueva con su specs.
- **Lo que NO debe hacer el asistente:** no asumir el temario original como fijo, no
  proponer cargar datos reales de Bios, no mezclar audiencias en una sola práctica que
  excluya a una de las dos poblaciones.

---

## 10. Próxima	iteración

**Clase 2 — DECISIÓN CERRADA**

- **Título:** "Cómo construir un Agente de IA" (par con S1 "qué es un agente").
- **Mecánica:** demo guiada (el facilitador construye y explica en pantalla). Los
  participantes tienen acceso al repo para montarlo a la par si quieren, y un `.md`
  con instrucciones detalladas para montarlo ellos mismos después.
- **Dos partes:**
  1. Agente ReAct con código transparente (concepto por archivo, loop a mano) +
     memoria, usando **Azure OpenAI** (`AzureChatOpenAI` de `langchain-openai`),
     conversación por terminal sobre `bios_ops.db` de la clase 1.
  2. El mismo caso montado en **n8n cloud de Bios** para los no-técnicos.
- **Cierre del bloque de código:** proyectar las 3 líneas equivalentes con
  `langgraph.prebuilt.create_react_agent` — *"esto es lo que el framework abstrae, y
  ustedes ya ven qué esconde"*. Conceptos primero, framework como cierre.
- **Estructura modular del agente de código** (~115 líneas en 6 archivos, cada uno un
  concepto): `cliente.py`, `tools.py`, `memoria.py`, `loop.py`, `agente.py`, `chat.py`.
- **Reutiliza:** `bios_ops.db` de la clase 1 (4 dominios: Mantenimiento, Compras,
  Logística, Producción/TD).
- **Bloqueantes a resolver con Bios antes de la fecha:**
  1. Acceso al repo para todos los técnicos (hablar con José / líder del equipo).
  2. Acceso a instancia n8n de Bios + permiso para subir plantilla + credenciales
     OpenAI/Azure ya configuradas (pedir a TI).
  3. Confirmar que los técnicos tienen Python ≥3.10.

### Hipótesis de progresión S2–S4 (alineada con el "menos a más" de Bios)

- **S2 → cómo construir un agente (código transparente + n8n) con memoria.** cierre
  mostrando qué abstrae un framework.
- **S3 → datos: RAG.** El agente que ya existe ahora lee documentos internos. Conexión
  a fuentes reales una vez resuelto el contrato de tratamiento.
- **S4 → agéntico: Skills, MCP y/o agentes pre-construidos (Hermes/OpenClaw).
  Multiagente ReAct/supervisor.** El salto a unidades modulares y colaboración.
- **S5-S7 → acompañamiento.** Los Champions ya con su base funcional refinando hacia
  producción: aquí pueden entrar puntuales de observabilidad, evals, costos,
  arquitectura legacy, según el caso. Sin clase magistral.

**Esto desplaza temas del original al acompañamiento**: Harness (tests/evals/costos),
Spec Driven y Observabilidad quedan como apoyos puntuales en S5-S7 cuando un proyecto
los necesite, no como bloques docentes aislados.

Ver `clase2-como-construir-agente/` para el resultado de la iteración.