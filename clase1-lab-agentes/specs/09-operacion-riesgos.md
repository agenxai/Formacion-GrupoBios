# 09 · Operación y riesgos

Esta spec existe porque el laboratorio se ejecuta **una sola vez, en vivo, delante de
15 personas**. No hay segunda oportunidad y no hay tiempo de depurar. Cada riesgo
listado abajo tiene una mitigación implementada en código, no un plan de contingencia
verbal.

---

## Riesgo 1 · La API key compartida (el más probable)

**Decisión tomada:** una sola `OPENAI_API_KEY` para las 15 personas.

**Qué va a pasar sin mitigación:** en el bloque de N3, quince personas ejecutan sus
celdas casi al mismo tiempo. Los límites de peticiones por minuto del proveedor se
aplican por organización, no por persona. Resultado: errores `429` en cascada,
justo en el momento pedagógico más importante de la clase.

Esto no es un riesgo hipotético; es la consecuencia aritmética de la decisión. Cuatro
mitigaciones, en capas:

### 1a. Caché en disco — la mitigación principal
Clave: `sha256(nivel + pregunta + modelo + hash(system_prompt) + semilla_datos +
fecha_referencia + variante)`.

Los dos últimos componentes se agregaron al implementar, y los dos por un fallo
concreto:

· **`fecha_referencia`.** Los datos se generan hacia atrás desde ella, así que con
  `FECHA_REFERENCIA` vacía la base cambia cada día. Sin este componente, el caché
  servía hoy respuestas calculadas sobre la base de ayer.
· **`variante`** — huella del código del nivel que se está ejecutando. Sin ella, un
  participante con su N3 a medio escribir recibía la traza cacheada del N3 correcto
  del facilitador, sus `assert` pasaban y el ejercicio quedaba anulado sin que nadie
  lo notara. Con ella, el caché se comparte entre quienes escribieron el MISMO código
  —que es la mayoría, y ahí sigue protegiendo la key compartida— y no entre
  implementaciones distintas.

Con datos deterministas (ADR-005) y preguntas precargadas (spec 07), **quince personas
haciendo clic en el mismo chip cuestan una sola llamada al modelo**. El caché es
compartido: el volumen del compose es el mismo para el tablero y el notebook, así que
lo que corre el facilitador en la demo queda cacheado para los participantes.

**El caché DEBE preservar los tiempos originales.** Esto no es un detalle de
implementación: un caché ingenuo devuelve en 20 milisegundos y **destruye la lección
central del laboratorio**. El valor de la vista comparación está en que N1 termina en un
segundo y N5 sigue trabajando diez segundos después; si todo llega instantáneo, las
cinco columnas se ven iguales y el costo de la agencia deja de ser visible.

Por eso la entrada de caché guarda la secuencia completa de eventos con sus `ts_ms` y
sus métricas, y al servirla los reemite con el mismo escalonamiento temporal — la misma
mecánica del modo replay, aplicada por pregunta. Detalle completo en *Caché y fidelidad
temporal*, spec 04.

Efecto secundario didáctico: `inicio` y `metricas` traen `desde_cache: true` y el
tablero lo marca con `⚡ caché`. La primera vez que alguien vea que su ejecución costó
$0.00 hay una conversación de 30 segundos sobre caching que la Sesión 5 retoma
formalmente.

`CACHE_ACTIVO=false` sigue disponible para demostrar ejecución real, pero **ya no es
necesario para que la demo enseñe lo que debe enseñar** — que era el motivo por el que
antes había que elegir entre proteger la key y dar buena clase.

### 1b. Semáforo de concurrencia
`MAX_CONCURRENCIA=4` llamadas simultáneas a la API. Las demás encolan. Preferimos
latencia predecible a errores impredecibles.

### 1c. Reintentos con backoff exponencial y jitter
Ante `429` o `5xx`: hasta 4 reintentos, base 1 s, factor 2, jitter aleatorio ±30%.
El jitter importa: sin él, quince clientes reintentan sincronizados y se vuelven a
chocar.

Cada reintento emite un evento `error` con `recuperable: true` y `reintento: n`. Se ve
en la traza — y es contenido: manejo de errores es tema de la Sesión 5.

### 1d. Modelo económico por defecto
`OPENAI_MODEL=gpt-4o-mini`. Los cinco niveles funcionan con un modelo pequeño; la
diferencia entre niveles es arquitectónica, no de capacidad del modelo.

> **Acción pendiente antes de la clase:** confirmar qué modelos están efectivamente
> habilitados en la cuenta de OpenAI de Grupo Bios y con qué límites de tasa. La spec
> fija un default razonable, pero el valor correcto depende de la cuenta y **no se
> puede asumir**. Sin este dato no se puede dimensionar `MAX_CONCURRENCIA`.

---

## Riesgo 2 · Sin red, red filtrada o API caída

El proxy de una red corporativa puede bloquear dominios, y la API del proveedor puede
degradarse en cualquier momento.

**Mitigación: `MODO=replay`.** `backend/replay/trazas.json` contiene los eventos
completos de las cinco preguntas precargadas × cinco niveles, grabados previamente. En
replay, los niveles reproducen los eventos **con sus tiempos originales** — la demo se
ve igual, incluida la asimetría de velocidad entre columnas.

Requisitos:
- `MODO=auto` (recomendado para clase): usa vivo si hay key y no se excedió el tope;
  cae a replay si no.
- Las trazas se graban con `python -m backend.replay.grabar` y **DEBEN regrabarse si
  cambian los prompts o el modelo**, o mostrarán algo que ya no es cierto.
- El indicador `◐ replay` DEBE estar visible siempre. **NO DEBE demostrarse replay
  como si fuera ejecución en vivo.** Es una cuestión de honestidad con el grupo: si el
  facilitador dice "miren cómo el agente decide" sobre una traza grabada, y alguien lo
  descubre, se pierde la credibilidad de todo el programa.
- **La conmutación automática DEBE ser intrusiva, no un badge.** Con `MODO=auto`, el
  sistema puede caer a replay en cualquier momento —un `429` persistente, el tope de
  gasto— y el facilitador está mirando al grupo, no la esquina de la pantalla. Sin un
  aviso imposible de ignorar, el propio default hace que el sistema incumpla el punto
  anterior. Requisito: banner de ancho completo, persistente hasta cerrarse a mano, más
  un evento `aviso` en los runs afectados (spec 07).
- Todo lo demás —datos, tools, front, notebook— funciona sin red. La base se genera en
  el build y las dependencias del front están vendorizadas (ADR-004).

---

## Riesgo 3 · Gasto descontrolado

Quince personas experimentando con N5 (≈11 llamadas por ejecución) pueden gastar más
de lo previsto, sobre todo si alguien deja un bucle corriendo.

**Mitigación: tope duro.** `TOPE_USD=10.00`, contabilizado en proceso a partir de los
tokens reportados por la API. Al alcanzarlo, el sistema conmuta a `replay` y muestra un
aviso; no falla ni se detiene.

- La barra de gasto es visible en el encabezado en todo momento.
- `GET /api/gasto` desglosa por nivel.
- Estimación de referencia: con caché activo, el laboratorio completo para 15 personas
  debería costar **menos de 3 USD** con un modelo pequeño. El tope de 10 es holgura,
  no presupuesto esperado.

> El precio por token no se codifica como constante sin verificar. `config.py` DEBE
> leer `PRECIO_ENTRADA_POR_1M` y `PRECIO_SALIDA_POR_1M` del entorno, con la tarifa
> vigente del modelo elegido confirmada en la documentación del proveedor al momento
> de preparar la clase. Un costo mal calculado en pantalla es peor que no mostrarlo:
> el grupo va a tomar decisiones de arquitectura con ese número.

**Y si nadie los configura, el sistema NO DEBE mostrar `$0.00`.** Los defaults del
`.env.example` son 0 —correctamente, para no inventar tarifas—, pero eso significa que
quien clone el repo y no los ajuste vería en ceros justamente la fila que sostiene la
lección de diseño del laboratorio, sin ningún fallo ni aviso.

Requisito: con precios en 0, el tablero muestra `costo no configurado` y usa **tokens**
como métrica comparativa, que llegan reales de la API. La comparación entre N1 y N5
funciona igual de bien en tokens que en dólares; lo que no funciona es enseñar en
silencio que un supervisor multiagente cuesta lo mismo que una sola llamada.

---

## Riesgo 4 · "A mí no me funciona"

El riesgo que motivó dockerizar todo.

**Mitigación: Docker + preflight obligatorio.**

- `docker compose up` DEBE dejar los dos servicios operativos sin ningún otro paso.
- La imagen incluye `bios_ops.db` ya generada. Arrancar no requiere red.
- Versiones fijadas con `==` en `requirements.txt` (spec 02).
- **Preflight 24–48 h antes de la sesión.** Cada participante DEBE haber ejecutado:
  ```
  git clone … && cd clase1-lab-agentes
  cp .env.example .env      # y pegar la key compartida
  docker compose up
  # abrir localhost:8888 → sección 0 → verificar_entorno()
  ```
  y reportado el resultado en el canal del programa. Si el preflight se hace en clase,
  se van 25 de los 55 minutos de hands-on. Esto no es una recomendación.
- **Plan B por participante:** un `Dockerfile` que también funciona en Codespaces, y
  como último recurso una versión del notebook que corre en Colab instalando las
  dependencias en la primera celda (más lenta, sin el tablero, pero permite seguir el
  hands-on).
- **Plan C del facilitador:** si Docker falla en la máquina que proyecta, el tablero
  corre con `uvicorn` local. Documentado en el README.

---

## Riesgo 5 · Fuga de datos y credenciales

Aplican las prácticas corporativas, no porque los datos sean sintéticos, sino porque
**este repositorio es la plantilla mental con que el equipo va a construir sus
proyectos reales**. Lo que se normalice aquí se repite en producción.

| Control | Requisito |
|---|---|
| Credenciales | `.env` en `.gitignore`. `.env.example` solo con placeholders. La key NO DEBE quedar en la imagen, en `docker-compose.yml`, en el notebook ni en ninguna salida de celda. |
| Serialización | Los eventos se serializan por **lista blanca** de campos, nunca por lista negra. Una lista negra deja pasar el campo que nadie previó. |
| Logs | El logging del backend NO DEBE registrar el valor de variables de entorno. Si se registra un encabezado de petición, se enmascara `Authorization`. |
| Datos | Solo sintéticos en la Sesión 1 (spec 03). El aviso es visible en el tablero y en el notebook. |
| Base de datos | Conexión de solo lectura desde las tools. `ejecutar_sql` con las seis restricciones de la spec 04. |
| Exposición de red | Los puertos se publican **solo en `127.0.0.1`** en el `docker-compose.yml`, no en `0.0.0.0`. `PUT /api/prompts` no tiene autenticación: exponerlo en la red de la oficina sería entregar el prompt del sistema a cualquiera. Documentado en el README. |
| Jupyter | Sin token, y por lo tanto **igualmente restringido a localhost**. |

Estos controles se comentan en voz alta durante la clase, brevemente. Es la primera
vez que el grupo ve un agente y es el mejor momento para plantar que **una tool es una
superficie de ataque**. Se desarrolla en la Sesión 7; aquí solo se siembra.

---

## Riesgo 6 · El modelo no colabora en la demo de N1

El clímax de la clase depende de que el modelo invente una cifra. Puede que se niegue.

**Mitigación: los dos caminos están guionados.** La spec 05 (N1) documenta qué decir
en cada caso. Un modelo que se niega también sirve: *incluso portándose bien, es
inútil para la operación*. Y hay un prompt de reserva («estima un valor típico para
una planta de este tamaño») que normalmente sí produce la cifra.

No se fuerza el resultado con trucos ni se usa una traza de replay haciéndola pasar
por vivo. Si el modelo se porta bien, se enseña con eso.

---

## Checklist previo a la sesión

Para el facilitador. Todo verificado, no asumido:

**Una semana antes:**

- [ ] **Ensayo cronometrado del notebook** por 1–2 personas del núcleo que NO lo
      escribieron, registrando el minuto real de fin de cada nivel y en qué `# TODO` se
      atascaron. Es lo único que puede cambiar el diseño del hands-on — reglas de
      decisión en la spec 01.
- [ ] `python -m backend.db.seed --recrear` pasa su autocomprobación: las cuatro
      anomalías y los identificadores de demo existen en la base (spec 03)
- [ ] `scripts/prueba_humo.py` en verde — ejercita los cinco niveles con un modelo
      guionado, sin gastar cuota. Es lo que se corre tras cualquier cambio de prompt,
      de tool o de dependencia.
- [ ] `scripts/verificar_contrato.py` en verde sobre las trazas de replay
- [ ] `scripts/validar_contraste.py` en verde

**El día anterior:**

- [ ] Modelos habilitados y límites de tasa confirmados en la cuenta de OpenAI de Bios
- [ ] `PRECIO_ENTRADA_POR_1M` / `PRECIO_SALIDA_POR_1M` actualizados con la tarifa
      vigente — **si quedan en 0, el tablero dirá «costo no configurado»**
- [ ] `TOPE_USD` acordado con quien paga la cuenta
- [ ] Key compartida distribuida por canal seguro (no por chat abierto ni correo)
- [ ] Trazas de replay regrabadas con los prompts y el modelo definitivos
- [ ] Los 5 chips de preguntas ejecutados en los 5 niveles, con respuestas revisadas
- [ ] Preflight reportado por los 15 participantes
- [ ] Tablero probado en el proyector real, con zoom al 150%
- [ ] Plan C (uvicorn local) probado en la máquina que proyecta
- [ ] [Guion del facilitador](./10-guion-facilitador.md) leído completo, con los dos
      caminos de N1 presentes
