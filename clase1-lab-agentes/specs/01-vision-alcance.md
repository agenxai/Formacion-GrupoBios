# 01 · Visión y alcance

## El problema pedagógico

El ebook de la Sesión 1 explica cinco niveles de agencia con diagramas estáticos. Un
participante puede leer los cinco y salir sin haber *sentido* la diferencia entre
ellos. Peor: sale creyendo que "más agéntico es mejor" y diseña un sistema multiagente
para un problema que un tool caller resolvía.

El laboratorio existe para producir tres convicciones, en este orden:

1. **Un LLM sin herramientas inventa datos operativos.** No es una advertencia
   teórica: lo ven pasar con una cifra de inventario en pantalla.
2. **Cada nivel de agencia tiene un costo.** Latencia, llamadas al modelo y dólares
   suben con la autonomía. La tabla comparativa lo hace innegable.
3. **El nivel correcto depende del problema.** La consulta de estado de un pedido no
   necesita un supervisor multiagente. Esa decisión de diseño es el entregable
   intelectual de la sesión.

## Objetivo medible

Al terminar la sesión, cada participante DEBE poder:

- Señalar en su propio proyecto qué nivel de agencia necesita, y defenderlo.
- Escribir una tool nueva (función Python + esquema) y conectarla a un agente
  LangGraph, sin copiar y pegar de la solución.
- Leer una traza de agente e identificar dónde se decidió llamar a una herramienta.

## Audiencia y sus consecuencias de diseño

15 personas. Dos poblaciones con necesidades opuestas:

| Población | Perfil | Qué exige del diseño |
|---|---|---|
| **Núcleo** (~4) | Desarrollo avanzado, capacidades consolidadas | Retos ampliados en cada nivel; no pueden quedar esperando |
| **Champions** (~11) | Heterogéneos: de sólidos en dev a en fortalecimiento técnico | Cada nivel arranca de código que ya corre; nadie pierde la sesión por trabarse |

Consecuencias concretas, no negociables:

- **Independencia entre niveles.** El notebook DEBE permitir ejecutar N4 sin haber
  completado N3. Cada sección arranca de un estado funcional.
- **Solución al lado.** Cada reto tiene su implementación de referencia disponible.
  Trabarse cuesta minutos, no la sesión.
- **Retos `[NÚCLEO]`** marcados explícitamente para los 4 avanzados, diseñados para
  que su trabajo extra sea *desbloquear a su mesa*, no adelantarse solos.
- **Cero instalación local.** Todo corre en Docker. La spec 09 cubre el plan B.

## Los cuatro dominios

El laboratorio toca los cuatro proyectos reales de los Champions con un solo dataset,
de modo que cada uno pueda tirar del hilo de su caso:

| Dominio | Proyecto del Champion | Tools que lo alimentan |
|---|---|---|
| **Mantenimiento** | Predicción de fallas de equipos | `historial_fallas`, `lecturas_sensor` |
| **Compras** | Planeación y asignación de volúmenes a plantas | `consultar_inventario`, `consultar_demanda` |
| **Logística** | Interfaz de cliente tipo aeropuerto | `estado_pedido`, `turnos_muelle` |
| **Producción / TD** | Planeación de la demanda | `consultar_demanda`, `consultar_produccion` |

El reto de cierre es el mismo para todos: **"agrega la tool que tu proyecto
necesita"**. Sale de la clase con una tool propia funcionando.

## Presupuesto de tiempo

El bloque de hands-on de la Sesión 1 son **55 minutos**, y **los cinco niveles se
construyen en clase** (decisión del facilitador). Es un objetivo exigente y solo se
alcanza con una restricción de diseño explícita:

> **El presupuesto no se mide en minutos, se mide en líneas que el participante
> escribe.** Todo el andamiaje viene dado. Cada nivel deja al descubierto únicamente
> las líneas que *encarnan la idea de ese nivel*.

| Momento | Min | Líneas a escribir | Qué escribe exactamente |
|---|---|---|---|
| N1 — el LLM inventa | 4 | **0** | Solo ejecuta y observa. La cifra inventada es el contenido. |
| N2 — router | 7 | **2** | El modelo Pydantic de salida estructurada |
| N3 — tool caller | 14 | **4** | El bloque que ejecuta la tool call dentro del loop |
| N4 — ReAct | 14 | **3** | `create_react_agent` + lista de tools + system prompt |
| N5 — supervisor | 12 | **4** | Envolver dos ReAct como tools y pasarlas al supervisor |
| Cierre y comparación | 4 | — | Tablero en modo comparación |

**Total: 55 min, 13 líneas de código.** El resto —tools, cliente del modelo, emisión
de eventos, impresión de trazas— está escrito y probado en `backend/`.

N5 es viable en 12 minutos por una razón estructural: **se apoya en N4**. Si el ReAct
del participante funciona, N5 es «haz dos de estos, dales su propio prompt y su
subconjunto de tools, y entrégaselos a un tercero como si fueran funciones». Es poca
escritura y mucha comprensión — la proporción correcta.

### Condiciones duras

Sin estas tres, el plan de 55 minutos no se cumple y hay que recortar en vivo:

1. **Preflight cumplido por los 15** (spec 09). Instalar en clase consume 25 de los 55
   minutos. No es negociable.
2. **Celda de rescate al inicio de cada nivel** (spec 08). Trabarse cuesta 2 minutos,
   no la sesión.
3. **Checkpoints de tiempo anunciados en voz alta.** El [guion del facilitador](./10-guion-facilitador.md)
   marca el minuto en que hay que ejecutar la celda de rescate y avanzar, esté o no
   terminado. Quien decide cortar es el reloj, no el orgullo.
4. **Ensayo cronometrado, una semana antes.** Una o dos personas del núcleo recorren el
   notebook completo **sin haberlo escrito**, con cronómetro, y se registra el minuto
   real en que termina cada nivel.

### El presupuesto de 13 líneas es una apuesta, no un hecho

Asume que el andamiaje es tan bueno que un `# TODO` de cuatro líneas se resuelve en
ocho minutos. **Eso no se sabe hasta que alguien que no escribió el notebook lo
cronometre**, y es la única incógnita capaz de cambiar el diseño del hands-on.

Del ensayo del punto 4 salen dos números: minutos reales por nivel, y en qué `# TODO`
se atascó la gente. Reglas de decisión, fijadas de antemano para no improvisar bajo
presión:

| Resultado del ensayo | Acción |
|---|---|
| Total ≤ 55 min | Se procede como está. |
| Total entre 55 y 70 min | Se mueve andamiaje adicional a `backend/`, reduciendo `# TODO`. No se recortan niveles. |
| Total > 70 min | Se aplica la válvula de escape de forma planificada: N5 pasa a demo desde el diseño, no en vivo. |
| Un `# TODO` concreto atasca al ensayista | Ese `# TODO` se reduce o se acompaña de una pista en comentario. |

### Válvula de escape

Si a los 35 minutos el grupo no va terminando N4, el facilitador convierte **N5 en
demo del tablero** y lo deja como entregable para el recap de la Sesión 2 (que ya
tiene 10 minutos reservados). Se decide con el grupo, en voz alta y sin drama: es
mejor que cinco niveles a medias.

Esta válvula está documentada para que exista la opción, no porque sea el plan.

## Fuera de alcance (Sesión 1)

Se declara explícitamente para evitar que el laboratorio crezca:

- **RAG y memoria persistente** → Sesión 2. Los agentes de N1–N5 son sin estado
  entre ejecuciones, a propósito.
- **Datos reales de Grupo Bios** → Sesión 2 en adelante, y solo después de resolver
  dónde se procesan y bajo qué contrato con el proveedor del modelo.
- **MCP, Skills** → Sesión 3.
- **Tests, evals, CI/CD** → Sesión 5. El notebook incluye `assert` de
  auto-verificación, que es la semilla, no el harness.
- **Observabilidad con LangFuse/LangSmith** → Sesión 7. El tablero tiene trazas
  propias, deliberadamente artesanales, para que en la Sesión 7 se aprecie qué
  aporta una herramienta real.
- **Autenticación de usuarios.** El tablero corre en la red local de la sesión.
- **Persistencia de conversaciones.** Cada ejecución es independiente.
