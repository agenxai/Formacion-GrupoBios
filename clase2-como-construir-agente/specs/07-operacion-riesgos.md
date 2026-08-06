# 07 · Operación y riesgos — Clase 2

Esta spec existe porque la clase se ejecuta **una sola vez, en vivo, delante de 15
personadas**. No hay segunda oportunidad. Cada riesgo listado abajo tiene una
mitigación implementada (en `.env`, en el contrato de tools, en el checklist), no un
plan de contingencia verbal.

La clase 2 es más simple que la clase 1 (no hay app web, no hay 15 personas
corriendo en paralelo), pero tiene riesgos nuevos que la clase 1 no tenía:
dependencia de Azure, dependencia de la instancia n8n de Bios, y **demo guiada** —
si falla algo en la pantalla del facilitador, no hay 14 backups distributed.

---

## Riesgo 1 · Conectividad con Azure OpenAI (el más probable)

**Qué va a pasar sin mitigación:** el facilitador ejecuta `python -m chat` en la
Parte 1a, la llamada a Azure tarda diez segundos, cae con `401 Unauthorized` o
`ConnectionError` y la primera demo se cae. Ya no hay vuelta atrás: la Parte 1b
depende de que 1a funcione, y la Parte 2 también usa Azure.

### Mitigaciones

1. **El facilitador corre la conversación insignia completa, 24-48 h antes, desde la
   misma máquina y la misma red que va a usar en clase.** Si la red de Bios está
   detrás de un proxy, el `try/except` de `loop.py` no resuelve el problema —hay que
   confirmar que el endpoint de Azure es alcanzable desde el sitio físico.
2. `.env` validado por `cliente.py` al arrancar: si falta `AZURE_OPENAI_ENDPOINT`,
   `AZURE_OPENAI_API_KEY` o `AZURE_OPENAI_DEPLOYMENT`, el script no arranca y dice
   cuál falta. No se descubre el fallo en el minuto 10.
3. Verificar con TI de Bios que el deployment existe y está en estado `succeeded`,
   no en `creating` o `failed`. Lilst en el checklist.
4. **Plan C:** si la API está abajo en vivo, el facilitador dice *"se nos cayó
   Azure,eso va a pasar en sus proyectos también"*, y proyecta una transcripción
   pre-armada de la conversación esperada, marcada claramente como *"ejecución
   grabada, no en vivo"*. Es el equivalente del modo replay de la clase 1 —pero
   manual, sin pretender que es en vivo. **Nunca** se presenta una traza
   pre-armada como si fuera la ejecución actual: pierde la credibilidad de todo el
   programa (misma regla que el modo replay de la clase 1).

---

## Riesgo 2 · Acceso al repositorio para los técnicos

**Decisión (spec 01):** los técnicos pueden montar el agente a la par si quieren,
con acceso al repo de la clase 2. **Bloqueante.**

**Qué va a pasar sin mitigación:** si no todos tienen acceso al repo al iniciar la
clase, los técnicos se quedan mirando sin poder correr. La Participación del núcleo
sepierde y la dinámica se vuelve pasiva.

### Mitigaciones

1. **Gestionar el acceso con José / líder del equipo, mínimo una semana antes.**
   Confirmar que los 4 del núcleo y todos los Champions con base de software tienen
   su usuario / credencial.
2. **Alternativa:** si Bios no permite acceso al repo, entregar el `.zip` con la
   carpeta `agente-transparente/` + `agente-framework/` vía un canal interno de Bios
   (SharePoint, drive de Bios, un repo interno de ellos). El `.zip` no contiene
   secrets (`.env` está en `.gitignore`).
3. **Plan C:** si nadie puede acceder, la clase es puramente demo y las preguntas se
   responden con el facilitador proyectando. El `.md` de "cómo montarlo" queda para
   que lo reproduzcan después. **No es ideal, pero no es fallo** — la lección está
   en verlo construir.

---

## Riesgo 3 · Acceso a la instancia n8n de Bios (bloqueante de la Parte 2)

**Qué va a pasar sin mitigación:** la Parte 2 empieza en el minuto 53, el
facilitador abre el navegador, pide credenciales y descubre que nadie le dio acceso,
o que el workflow no está importado, o que la credencial Azure no está registrada.
No hay plan C razonable en 25 minutos.

### Mitigaciones

1. **Acceso gestionado con TI de Bios, mínimo una semana antes.** El facilitador
   necesita un usuario con permisos para **importar workflows** y **ejecutarlos**.
2. **El workflow se importa 24-48 h antes** y se ejecuta el turno 1 de la
   conversación insignia desde la misma red. Si la credencial Azure no está
   configurada, **no se da la Parte 2** —se plantea la transcripción pre-armada.
3. **Plan C:** video pre-grabado de la ejecución del workflow en la instancia de
   Bios, marcado claramente como grabación. Último recurso; el episodic value de la
   Parte 2 cae sustancialmente. Es el plan de fallo menos deseable.

---

## Riesgo 4 · Latencia del LLM en la conversación multi-turno

**Qué va a pasar sin mitigación:** la conversación insignia tiene 4 turnos. Cada
turno del ReAct puede implicar 2-3 llamadas al modelo (decisión de tool, ejecución,
respuesta). En total, 8-12 llamadas. Con `gpt-4o-mini` son ~20-40 s por turno. Si
hay rate limiting, más. El grupo espera ~2 min en silencio mirando el cursor, y la
dinámica se enfría.

### Mitigaciones

1. **Imprimir `[Thought]`, `[Action]`, `[Observation]` en tiempo real mientras el
   loop corre** —no esperar a que termine para mostrar la traza. La salida
   progresiva del terminal mantiene la atención. Es el correspondiente visual del
   diagrama animado del tablero de la clase 1, pero en texto.
2. **El facilitador narra lo que se está imprimiendo mientras aparece.** "Miren: ya
   decidió que necesita la tool. Está esperando la respuesta de la base. Ya la tiene;
   ahora compara con la demanda." El silencio se llena con explicación, no con
   espera pasiva.
3. **Mantener las tools síncronas y rápidas** — cada tool consulta SQLite local
   (<10 ms). El cuello es el LLM, no las tools. Si se cambia a HTTP externo, se
   agrega latencia al ciclo sin ganancia pedagógica.
4. **Plan C:** si Azure está lento en vivo, ejecutar solo los turnos 1 y 2 (los que
   muestran el encadenamiento) y dejar 3 y 4 para que los prueben en casa. La lección
   está en el turno 2; los demás refuerzan.

---

## Riesgo 5 · El agente decide mal (alucina una tool, ignora memoria)

**Qué va a pasar sin mitigación:** en el turno 2 el agente, en vez de llamar
`consultar_demanda`, responde "no tengo esa información" o inventa un número. La
memoria del turno 1 no se usa. La lección pedagógica se pierde y hay que improvisar.

### Mitigaciones

1. **El system prompt prohíbe explícitamente inventar cifras operativas.** Mismo
   principio que la clase 1 (N1 que inventa vs N4 que no). El prompt se proyecta al
   explicar `agente.py` y se discute en clase —es contenido, no solo mitigación.
2. **La docstring de `consultar_demanda` referencia `consultar_inventario`** ("para
   saber cuánto se NECESITA, usa `consultar_demanda`"). El modelo tiene orientación
   para elegir.
3. **El facilitador ejecuta la conversación completa 24-48 h antes** y registra qué
   turnos respondió correctamente. Si alguno falla sistemáticamente, se afina el
   system prompt o el `MAX_ITERACIONES` antes de la clase —no se prueba en vivo.
4. **En vivo, si el agente se equivoca:** *"miren, se equivocó. Eso va a pasar en
   sus proyectos. La culpa suele ser el prompt o la docstring. Vamos a cambiarlo en
   vivo y ver."* Editar el system prompt en `agente.py`, volver a ejecutar. Es
   material didáctico: la recuperación de un fallo es mejor lección que una demo
   perfecta. (Mismo principio de la clase 1, spec 10.)

---

## Riesgo 6 · Cargar datos reales de Bios en la base

**Qué va a pasar sin mitigación:** un Champion, motivado, copia una tabla real de
Bios en `bios_ops.db`. Las tools la envían a Azure OpenAI. Se expone información
productiva sin contrato de tratamiento.

### Mitigaciones

1. **El avisio de datos sintéticos se muestra al arrancar la conversación** (spec 03),
   en el README y `COMO-MONTARLO.md`. Recordar verbalmente al inicio de la Parte 1a.
2. **`tools.py` abre `bios_ops.db` en modo solo lectura.** No es que no se pueda
   escribir; es que se elige no poder. El permiso se reduce en la conexión.
3. Se explicita el candado en clase: *"esto es sintético; en sus proyectos reales
   hay que resolver primero el contrato de tratamiento de la información con TI y
   con Legal. Eso no se hace en la clase 2; se hace cuando un proyecto lo amerite, en
   el acompañamiento."*

---

## Riesgo 7 · Exposición de la API key

**Qué va a pasar sin mitigación:** el facilitador proyecta su `.env` (o el grupo lo
ve si alguien monta el repo) y la key de Azure queda visible.

### Mitigaciones

1. **`.env` está en `.gitignore`** y nunca se proyecta. Si hay que mostrar el
   formato, se proyecta `.env.example` con valores ficticios.
2. **`cliente.py` carga las variables con `python-dotenv`** —no se pasan como
   argumentos ni se imprimen. El script solo dice "cliente cargado: deployment
   `gpt-4o-mini`" sin revelar la key.
3. Si un técnico monta el repo a la par, recibe `.env.example` y pega SU key o una
   que Bios le asigne. **No recibe la key del facilitador.** Si Bios prefiere, se
   entrega una key individual por Champion; si es compartida, `MAX_CONCURRENCIA` no
   aplica acá (no hay 15 personas corriendo en paralelo — solo el facilitador corre
   en la demo), pero queda documentado para el acompañamiento.

---

## Checklist 24-48 h antes

**Para el facilitador.** Verification, no setup — el setup ya está hecho.

### Repo y código

- [ ] `agente-transparente/` está completo y `python -m chat` arranca sin error.
- [ ] Ejecutada la conversación insignia completa (4 turnos), con respuestas
      correctas en los 4.
- [ ] `agente-framework/agente.py` corre la misma conversación con resultados
      equivalentes.
- [ ] `.env` configurado con credenciales Azure válidas (testeado con una llamada).
- [ ] `bios_ops.db` copiada desde `clase1-lab-agentes/` y abre en modo lectura.
- [ ] `COMO-MONTARLO.md` revisado y exportado a PDF o markdown para distribución.

### n8n

- [ ] Acceso confirmado a la instancia n8n de Bios (usuario + permisos de import).
- [ ] `plantilla-agente-bios-react.json` importado.
- [ ] Credencial Azure OpenAI registrada y seleccionada en el nodo AI Agent.
- [ ] Turno 1 de la conversación insignia ejecutado desde el navegador, respuesta
      correcta.

### Acceso de participantes

- [ ] José / líder confirmó acceso al repo para todos los técnicos (o canal
      alternativo de entrega preparado).
- [ ] Los 4 del núcleo saben que su rol es desbloquear a su mesa.
- [ ] Confirmado con TI de Bios: deployment de Azure OpenAI en estado `succeeded`.

### Hardware

- [ ] Laptop del facilitador probada en el proyector real, con zoom al 125-150%.
- [ ] Terminal con fuente legible desde el fondo del salón (`Monaco` 18pt o
      equivalente).
- [ ] Segundo navegador o pestaña con el workflow de n8n ya abierto.

### Plan C

- [ ] Transcripción de la conversación esperada (Partes 1a/1b) lista para proyectar
      si Azure falla. Marcada claramente como "ejecución pre-grabada".
- [ ] Capturas de pantalla del workflow de n8n ya ejecutado (Parte 2) en caso de
      caída de la instancia.

Si cualquier item no pasa, no se da la clase. Se reprograma o se ajusta —no se
improvisa en vivo.