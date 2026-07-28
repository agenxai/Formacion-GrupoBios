# Especificaciones · Laboratorio "Niveles de Agencia"

**Cliente:** Grupo Bios · **Programa:** Qypher — Formación en IA y Agentes
**Sesión:** 1 — Agentes y Arquitecturas Multiagénticas
**Estado:** `v1.0` — **implementado**, salvo la spec [11](./11-contexto-caso.md)
(**pendiente de implementar**). Ver [`../README.md`](../README.md) para ejecutarlo.

Las specs se escribieron completas antes del código y se corrigieron **después**, allí
donde la implementación demostró que estaban equivocadas. Cada una de esas correcciones
quedó anotada en su spec con el motivo, porque en la Sesión 6 este conjunto se presenta
como caso de estudio y lo que enseña no es una spec perfecta: es qué hace una spec
cuando se topa con el código. Los cambios de fondo fueron cinco:

| Spec | Qué cambió al implementar |
|---|---|
| 03 | Una tabla más, `formulas`: sin ella la pregunta insignia comparaba toneladas de producto con toneladas de materia prima |
| 04 | La resolución de nombres de planta pasó a ser estricta con la identidad — resolvía «la planta de Cali» a otra planta |
| 05 | La brecha de la demo es ~1.330 t, no ~40 t: la cifra ilustrativa era incompatible con el inventario de 320 t, que sí tiene contrato |
| 06 | Dos tonos de la paleta y la escala tipográfica: `validar_contraste.py` encontró cuatro incumplimientos |
| 09 | La clave de caché lleva además `fecha_referencia` y `variante`, o el caché servía datos de ayer y tapaba los errores de los participantes |

---

## Qué es este documento

El conjunto de especificaciones del componente práctico de la Sesión 1. Se escribe
**antes** del código, a propósito: el mismo laboratorio se usará en la Sesión 6
(*Spec Driven Development*) como caso de estudio de "un proyecto 100% especificado".
Es decir, estas specs son a la vez el contrato de construcción y material didáctico.

## Los dos artefactos

| Artefacto | Quién lo usa | Cuándo |
|---|---|---|
| **Tablero de Agencia** (app web dockerizada) | El facilitador, proyectado | En vivo, durante la clase |
| **Notebook guiado** (Jupyter, mismo Docker) | Cada participante | Hands-on y post-clase |

Ambos implementan **los mismos cinco niveles de agencia** del ebook de la clase,
sobre **el mismo dataset**, con **las mismas tools**. El tablero los *muestra*; el
notebook los *reconstruye*.

## Índice

| # | Spec | Contenido |
|---|---|---|
| [01](./01-vision-alcance.md) | Visión y alcance | Objetivo pedagógico, audiencia, qué NO se hace |
| [02](./02-arquitectura.md) | Arquitectura | Componentes, Docker, decisiones técnicas (ADR) |
| [03](./03-datos.md) | Modelo de datos | Esquema `bios_ops.db` + generador sintético |
| [04](./04-contratos.md) | Contratos | Eventos SSE, tools, API HTTP — **el núcleo** |
| [05](./05-niveles.md) | Niveles N1–N5 | Comportamiento y criterios de aceptación por nivel |
| [06](./06-identidad-visual.md) | Identidad visual | Logos, paleta Grupo Bios, tipografía, accesibilidad |
| [07](./07-frontend.md) | Frontend | Layout, vistas, estados, interacción |
| [08](./08-notebook.md) | Notebook | Estructura de celdas, retos, auto-verificación |
| [09](./09-operacion-riesgos.md) | Operación y riesgos | API key compartida, costos, seguridad, plan B |
| [10](./10-guion-facilitador.md) | Guion del facilitador | Minuto a minuto de los 55 min: qué proyectas, qué dices, dónde cortas |
| [11](./11-contexto-caso.md) | Contexto del caso | La vista previa a los niveles: escenario, datos, herramientas en vivo y preguntas — **pendiente de implementar** |

Además, fuera de este directorio:

| Documento | Contenido |
|---|---|
| [`../README.md`](../README.md) | **Guía de ejecución del repositorio.** Requisitos, Docker, variables de entorno, verificación, solución de problemas, checklist de preflight. Es el documento que lee quien clona el repo. |
| [`../.env.example`](../.env.example) | Plantilla de configuración, comentada variable por variable. |

## Decisiones ya cerradas

Registradas para que no se re-litiguen durante la construcción:

- **Proveedor LLM:** OpenAI para los cinco niveles. Modelo configurable por variable
  de entorno.
- **Framework:** LangGraph. N5 es un supervisor con sub-agentes expuestos como tools
  en LangGraph, no Claude Agent SDK. El Agent SDK se menciona en el cierre como
  contraste conceptual, sin dependencia en el repo.
- **Datos:** SQLite sintético, generado por script con semilla fija. Cero datos
  reales de Grupo Bios en la Sesión 1.
- **Frontend:** HTML + CSS utilitario + Alpine.js. Sin build step, sin Node en la
  imagen.
- **API key:** una sola compartida para el grupo. Esto condiciona el diseño — ver
  [spec 09](./09-operacion-riesgos.md).
- **Alcance en clase:** los **cinco** niveles se construyen durante los 55 minutos de
  hands-on. Esto impone el presupuesto de 13 líneas de código escritas por el
  participante — ver [spec 01](./01-vision-alcance.md).
- **Nombres del dataset:** municipios reales de Colombia con aviso explícito de que la
  asignación planta↔municipio es ficticia.

## Convenciones

- `DEBE` / `NO DEBE` — requisito obligatorio; su ausencia es un defecto.
- `DEBERÍA` — recomendado; omitirlo requiere justificación.
- `PUEDE` — opcional, alcance ampliado si sobra tiempo.
- Código, identificadores y comentarios en **español**. Los nombres de librerías y
  APIs externas quedan en su idioma original.
