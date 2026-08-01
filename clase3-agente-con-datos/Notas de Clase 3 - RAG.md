# Notas de Clase 3 — Cómo darle tus datos a un Agente de IA

> **Formación Grupo Bios en IA · Sesión 3**
> Memoria de largo plazo, RAG y las optimizaciones que separan una demo de un
> sistema de producción.

---

## El arco del programa: dónde estamos

- **Sesión 1** respondió *¿qué es un agente de IA?* — componentes, niveles de
  agencia, patrones, function calling.
- **Sesión 2** respondió *¿cómo se construye?* — el loop ReAct pieza por pieza,
  con memoria conversacional, en tres implementaciones (a mano, LangGraph, n8n).
- **Sesión 3** responde *¿cómo le das tus datos?* — el agente que ya construimos
  sabe responder **cuánto** (la base SQL le da cifras), pero no sabe responder
  **cómo** ni **por qué**. Eso vive en documentos: manuales, procedimientos,
  políticas, fichas técnicas. Hoy le damos esa capacidad.

La tesis de la sesión, dicha de una vez: **RAG no es otra tecnología aparte —
es una herramienta más de su agente.** Y la segunda tesis, que es la que se
llevan a sus proyectos: **el RAG "de tutorial" funciona en la demo y falla en
producción.** Esta clase muestra exactamente dónde falla y qué perilla arregla
cada fallo.

<!-- Visual animado (CSS puro). Vista previa de VS Code o export HTML. Si se necesita imagen estática: images/3-01-arco-programa.png — línea de tiempo de las 7 sesiones con S3 resaltada. -->
<div class="c3v1">
<style>
.c3v1{background:#141a26;border-radius:14px;padding:24px 16px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v1 .fila{display:flex;align-items:center;justify-content:center;gap:6px;flex-wrap:wrap;}
.c3v1 .ses{background:#212b3d;border:2px solid #33415c;border-radius:10px;padding:10px 12px;text-align:center;min-width:100px;}
.c3v1 .ses b{display:block;font-size:13px;color:#8fa3c2;margin-bottom:2px;}
.c3v1 .ses span{font-size:11.5px;}
.c3v1 .hecha{border-color:#4caf7d;}
.c3v1 .hecha b{color:#4caf7d;}
.c3v1 .hoy{border-color:#f5b942;background:#2a2413;animation:c3v1pulso 2s ease-in-out infinite;transform:scale(1.07);}
.c3v1 .hoy b{color:#f5b942;}
@keyframes c3v1pulso{0%,100%{box-shadow:0 0 0 0 rgba(245,185,66,.55);}50%{box-shadow:0 0 0 12px rgba(245,185,66,0);}}
.c3v1 .flecha{color:#54627e;font-size:18px;}
.c3v1 .iconos{text-align:center;margin-top:16px;font-size:14px;color:#f5b942;animation:c3v1flota 3s ease-in-out infinite;}
@keyframes c3v1flota{0%,100%{transform:translateY(0);}50%{transform:translateY(-4px);}}
.c3v1 .pie{text-align:center;margin-top:8px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="fila">
 <div class="ses hecha"><b>S1 ✓</b><span>¿Qué es un agente?</span></div><div class="flecha">→</div>
 <div class="ses hecha"><b>S2 ✓</b><span>¿Cómo se construye?</span></div><div class="flecha">→</div>
 <div class="ses hoy"><b>S3 · HOY</b><span>¿Cómo le das tus datos?</span></div><div class="flecha">→</div>
 <div class="ses"><b>S4</b><span>¿Cómo colaboran?</span></div><div class="flecha">→</div>
 <div class="ses"><b>S5–S7</b><span>Acompañamiento de proyectos</span></div>
</div>
<div class="iconos">📄 manuales &nbsp;·&nbsp; 🔍 búsqueda &nbsp;·&nbsp; 🧠 agente</div>
<div class="pie">Hoy, el agente que construimos en la S2 aprende a leer los documentos del negocio.</div>
</div>

---

## 1 · La memoria en agentes: el puente desde la clase 2

Un LLM, por sí solo, no recuerda nada. Cada llamada al modelo arranca de cero:
lo único que "sabe" en ese momento es lo que trae de su entrenamiento más lo
que va dentro de la ventana de contexto de esa llamada. Todo lo que llamamos
"memoria" en un agente es ingeniería alrededor de esa limitación: decidir qué
información acumular y volver a inyectar en cada llamada.

En la clase 2 ya construimos una memoria — la vimos en `memoria.py`: una lista
de mensajes que se pasa completa al modelo en cada turno. Eso tiene un nombre
técnico.

### Memoria de corto plazo (Short-Term Memory, STM)

Mantiene el contexto inmediato de la conversación actual. Es lo que permitió
que en la clase 2 el agente entendiera «¿y me alcanza para la demanda?» sin que
le repitiéramos "Itagüí" ni "maíz".

- **Función:** coherencia dentro de una sesión.
- **Capacidad:** limitada por la ventana de contexto del modelo.
- **Mecanismo:** un buffer de mensajes que se inyecta en cada llamada al LLM.
- **Variantes:** ventana de últimos N mensajes (lo que configuramos en n8n como
  *Window Buffer Memory* con ventana de 10) y buffers de acumulación de
  entradas (agrupar varios mensajes seguidos del usuario en un solo input).
- **Limitación:** al cerrar la sesión, se pierde. No sirve para personalización
  ni para conocimiento del negocio.

### Memoria de largo plazo (Long-Term Memory, LTM)

Permite almacenar y recordar información **entre sesiones**. Se implementa con
almacenamiento externo: bases de datos relacionales, bases vectoriales o grafos
de conocimiento. Es lo que necesita un agente que deba recordar hechos del
negocio, eventos pasados, preferencias del usuario o habilidades aprendidas.

Dentro de la LTM conviene distinguir dos capas, porque tienen ciclos de vida
distintos:

| | Memoria semántica | Memoria episódica |
|---|---|---|
| **Qué guarda** | Hechos estables y depurados: políticas, catálogos, manuales, perfiles | Cada interacción tal como ocurrió: quién habló, qué tool se llamó, qué pasó |
| **Ejemplo en Bios** | "El procedimiento ante vibración excesiva del molino exige parada programada" | "El 12 de marzo el usuario preguntó 3 veces por el pedido PD-24-00871" |
| **Para qué sirve** | Respuestas fundamentadas (*grounded*) y filtros deterministas | Trazabilidad, depuración, aprendizaje de preferencias implícitas |
| **Naturaleza** | Consistente, versionada, con procedencia | Ruidosa, redundante, historia factual |

La **consolidación** es el puente entre ambas: un proceso periódico recorre
episodios recientes y extrae los hechos que merecen pasar a la memoria
semántica. Es un tema de producción — lo retomamos en el acompañamiento cuando
un proyecto lo necesite.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-02-tipos-memoria.png — la memoria funcionando: conversación que se desliza por la ventana STM y hechos que cristalizan en la memoria de largo plazo. -->
<div class="c3v2">
<style>
.c3v2{background:#141a26;border-radius:14px;padding:22px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v2 .escena{display:flex;justify-content:center;align-items:stretch;gap:14px;flex-wrap:wrap;}
.c3v2 .panel{background:#1a2233;border:1px solid #33415c;border-radius:12px;padding:12px;width:270px;}
.c3v2 .ptitulo{font-size:11px;letter-spacing:1px;color:#8fa3c2;text-align:center;margin-bottom:8px;}
.c3v2 .ptitulo b{color:#4caf7d;}
.c3v2 .ltm .ptitulo b{color:#4da3ff;}
.c3v2 .chatwin{position:relative;height:178px;overflow:hidden;border:2px solid #4caf7d;border-radius:10px;background:#141a26;}
.c3v2 .chatwin::before{content:"";position:absolute;top:0;left:0;right:0;height:34px;background:linear-gradient(#141a26,transparent);z-index:2;}
.c3v2 .chatwin::after{content:"los mensajes viejos salen de la ventana ↑";position:absolute;top:3px;left:0;right:0;text-align:center;font-size:9px;color:#ff9f6b;z-index:3;}
.c3v2 .rollo{animation:c3v2rueda 14s linear infinite;padding:8px;}
@keyframes c3v2rueda{0%{transform:translateY(0);}100%{transform:translateY(-50%);}}
.c3v2 .msj{max-width:82%;font-size:10.5px;border-radius:9px;padding:5px 8px;margin:5px 0;}
.c3v2 .tu{background:#243550;margin-left:auto;text-align:right;}
.c3v2 .ag{background:#20302a;border:1px solid #2c4a3c;}
.c3v2 .vent{font-size:10px;color:#4caf7d;text-align:center;margin-top:6px;}
.c3v2 .puente{display:flex;flex-direction:column;justify-content:center;align-items:center;font-size:10.5px;color:#f5b942;gap:4px;min-width:90px;}
.c3v2 .via{position:relative;width:76px;height:4px;background:#33415c;border-radius:2px;overflow:hidden;}
.c3v2 .via i{position:absolute;top:-2px;left:-8px;width:8px;height:8px;border-radius:50%;background:#f5b942;animation:c3v2fluye 2.4s linear infinite;}
@keyframes c3v2fluye{0%{left:-8px;}100%{left:100%;}}
.c3v2 .hecho{background:#141a26;border:1.5px solid #4da3ff;border-radius:9px;padding:7px 9px;font-size:10.5px;margin:7px 0;color:#c8dcf5;}
.c3v2 .h1{animation:c3v2nace 12s ease-in-out infinite;}
.c3v2 .h2{animation:c3v2nace 12s ease-in-out infinite;animation-delay:6s;opacity:0;}
@keyframes c3v2nace{0%{opacity:0;transform:scale(.6);}6%,96%{opacity:1;transform:scale(1);}100%{opacity:0;}}
.c3v2 .hviejo{opacity:.45;}
.c3v2 .persiste{font-size:10px;color:#4da3ff;text-align:center;margin-top:6px;}
.c3v2 .pie{text-align:center;margin-top:12px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="escena">
 <div class="panel">
  <div class="ptitulo"><b>CORTO PLAZO</b> · la conversación de ahora</div>
  <div class="chatwin"><div class="rollo">
   <div class="msj tu">¿Cuánto maíz queda en Itagüí?</div>
   <div class="msj ag">320 t — bajo el mínimo</div>
   <div class="msj tu">¿Y la demanda de la semana?</div>
   <div class="msj ag">Requiere 1.652 t: no alcanza</div>
   <div class="msj tu">¿Equipos en riesgo?</div>
   <div class="msj ag">EQ-ITG-MOL-01, vibración</div>
   <div class="msj tu">¿Cuánto maíz queda en Itagüí?</div>
   <div class="msj ag">320 t — bajo el mínimo</div>
   <div class="msj tu">¿Y la demanda de la semana?</div>
   <div class="msj ag">Requiere 1.652 t: no alcanza</div>
   <div class="msj tu">¿Equipos en riesgo?</div>
   <div class="msj ag">EQ-ITG-MOL-01, vibración</div>
  </div></div>
  <div class="vent">ventana = últimos N mensajes · se borra al cerrar<br><code>memoria.py</code> · <i>Window Buffer Memory</i> (clase 2)</div>
 </div>
 <div class="puente"><b>consolidación</b><span class="via"><i></i></span><span>los episodios se<br>destilan en hechos</span></div>
 <div class="panel ltm">
  <div class="ptitulo"><b>LARGO PLAZO</b> · lo que merece quedarse</div>
  <div class="hecho hviejo">✦ La planta Itagüí procesa maíz amarillo para 4 líneas</div>
  <div class="hecho h1">✦ Itagüí opera con déficit recurrente de maíz <small>(visto en 3 conversaciones)</small></div>
  <div class="hecho h2">✦ El molino EQ-ITG-MOL-01 falla por desbalanceo de rotor</div>
  <div class="persiste">🗄️ persiste entre sesiones: base de datos · vectorial · grafo<br>los <b>documentos de la empresa</b> ya son esta memoria → <b>RAG</b></div>
 </div>
</div>
<div class="pie">Izquierda: la ventana conversacional que construyeron en la S2 — útil ahora, se pierde al cerrar. Derecha: los hechos estables del negocio. RAG es cómo el agente consulta esa memoria de largo plazo.</div>
</div>

### El insight que abre la clase de hoy

Los documentos internos de una organización — manuales, procedimientos,
políticas — **son su memoria semántica**. Y la técnica estándar para que un
agente la consulte se llama **RAG**. Es decir: hoy no vamos a aprender "otra
cosa"; vamos a darle al agente de la clase 2 su memoria de largo plazo.

**Retos clave de la gestión de memoria** (los verán en sus proyectos):
relevancia contextual (no recuperar basura), gestión de tokens (no exceder la
ventana del modelo), decidir qué merece almacenarse permanentemente, y sesgos
(la memoria puede perpetuar los sesgos de lo que se almacenó).

---

## 2 · Qué es RAG y cuándo usarlo

**RAG (Retrieval-Augmented Generation, generación aumentada por recuperación)**
es una arquitectura que conecta un LLM con bases de conocimiento externas: ante
la pregunta de un usuario, el sistema **recupera** los fragmentos de
información más relevantes y los añade al prompt para que el modelo **genere**
la respuesta fundamentada en esos datos, no en su memoria de entrenamiento.

El principio es simple y ya lo conocen de la clase 2: *lo que entra en el
contexto determina lo que sale*. Las tools de la clase 2 metían filas de SQL al
contexto; RAG mete fragmentos de documentos. Proporcionar los datos correctos
en la entrada es la mitigación más efectiva contra las alucinaciones — con un
matiz de honestidad técnica: RAG las **reduce** notablemente, no las elimina;
por eso al final de estas notas hablamos de evaluación.

### Cuándo usar RAG (los cuatro casos clásicos, en versión Bios)

1. **El LLM no tiene información interna de la empresa.** «¿Cuál es el
   procedimiento de compra de maíz importado?» — ningún modelo lo sabe; está en
   el manual de compras.
2. **Los datos cambian con frecuencia.** «¿Qué dice la política de turnos de
   muelle vigente?» — la política se actualizó hace un mes; el modelo se
   entrenó antes.
3. **La respuesta vive en documentos largos.** «¿Qué hago ante una falla del
   molino?» — el protocolo está en un manual de 50 páginas; nadie lo va a leer
   completo en medio de una parada de planta.
4. **La información está dispersa en fuentes no estructuradas.** PDFs, actas,
   correos, intranet — RAG busca en todas y consolida.

Y el criterio inverso, igual de importante: **si la pregunta es sobre cifras
estructuradas** (¿cuánto inventario queda?), **la respuesta correcta es una
tool SQL como las de la clase 2, no RAG**. Vectorizar una base de datos
relacional para "buscarle parecido" a una cifra es un antipatrón. RAG es para
conocimiento no estructurado. Un buen agente tiene ambas herramientas y decide
cuál usar — a eso llegamos al final de la clase.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-03-sql-vs-rag.png — dos preguntas reales resueltas: una con tabla SQL, otra con fragmento de manual; el agente enruta. -->
<div class="c3v3">
<style>
.c3v3{background:#141a26;border-radius:14px;padding:22px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v3 .agente{margin:0 auto 4px;width:56px;height:56px;border-radius:50%;background:#212b3d;border:2px solid #54627e;display:flex;align-items:center;justify-content:center;font-size:26px;}
.c3v3 .decide{text-align:center;font-size:11px;color:#8fa3c2;margin-bottom:12px;}
.c3v3 .cols{display:flex;justify-content:center;gap:20px;flex-wrap:wrap;}
.c3v3 .carta{flex:1;min-width:250px;max-width:330px;background:#212b3d;border:2px solid #33415c;border-radius:12px;padding:12px;}
.c3v3 .sqlc{animation:c3v3brillaA 8s ease-in-out infinite;}
.c3v3 .ragc{animation:c3v3brillaB 8s ease-in-out infinite;}
@keyframes c3v3brillaA{0%,45%,100%{border-color:#33415c;}8%,35%{border-color:#4caf7d;box-shadow:0 0 14px rgba(76,175,125,.3);}}
@keyframes c3v3brillaB{0%,52%,100%{border-color:#33415c;}58%,88%{border-color:#f5b942;box-shadow:0 0 14px rgba(245,185,66,.3);}}
.c3v3 .preg{font-style:italic;font-size:12.5px;color:#c8d4e6;background:#243550;border-radius:9px;padding:6px 9px;text-align:center;}
.c3v3 .ruta{text-align:center;font-size:11px;margin:7px 0;font-weight:700;}
.c3v3 .sqlc .ruta{color:#4caf7d;}
.c3v3 .ragc .ruta{color:#f5b942;}
.c3v3 .tabla{border-collapse:collapse;margin:0 auto;font-size:10.5px;animation:c3v3apA 8s ease-in-out infinite;}
.c3v3 .tabla td,.c3v3 .tabla th{border:1px solid #3d5945;padding:3px 9px;color:#c9e5d5;}
.c3v3 .tabla th{background:#20302a;color:#4caf7d;}
.c3v3 .alerta{color:#ff6b6b !important;font-weight:700;}
@keyframes c3v3apA{0%,10%{opacity:0;transform:translateY(6px);}16%,100%{opacity:1;transform:translateY(0);}}
.c3v3 .cita{border-left:3px solid #f5b942;background:#241f13;border-radius:0 8px 8px 0;padding:7px 9px;font-size:10.5px;color:#f2e3bd;animation:c3v3apB 8s ease-in-out infinite;}
.c3v3 .cita b{color:#f5b942;}
@keyframes c3v3apB{0%,60%{opacity:0;transform:translateY(6px);}66%,100%{opacity:1;transform:translateY(0);}}
.c3v3 .porque{font-size:10px;color:#8fa3c2;text-align:center;margin-top:7px;}
.c3v3 .pie{text-align:center;margin-top:12px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="agente">🤖</div>
<div class="decide">el agente lee la pregunta y <b>enruta</b> a la herramienta correcta</div>
<div class="cols">
 <div class="carta sqlc">
  <div class="preg">«¿<b>Cuánto</b> maíz queda en Itagüí?»</div>
  <div class="ruta">→ tool SQL (clase 2) consulta bios_ops.db</div>
  <table class="tabla"><tr><th>materia</th><th>disponible</th><th>mínimo</th></tr><tr><td>Maíz amarillo</td><td class="alerta">320 t ⚠</td><td>1.190 t</td></tr></table>
  <div class="porque">una cifra exacta pide una consulta exacta —<br>vectorizar una tabla para "buscarle parecido" es un antipatrón</div>
 </div>
 <div class="carta ragc">
  <div class="preg">«¿<b>Qué hago</b> si el molino vibra?»</div>
  <div class="ruta">→ tool RAG (clase 3) busca en los manuales</div>
  <div class="cita"><b>Manual de mantenimiento §4.2:</b> ante vibración sostenida &gt; 7,1 mm/s, programar parada y verificar balanceo del rotor…</div>
  <div class="porque">un procedimiento vive en texto no estructurado —<br>ninguna tabla de la base lo contiene</div>
 </div>
</div>
<div class="pie"><b>Cuánto</b> → SQL &nbsp;·&nbsp; <b>cómo / por qué</b> → RAG. Un buen agente carga ambas herramientas y decide.</div>
</div>

---

## 3 · Anatomía de un sistema RAG

Un sistema RAG tiene cuatro componentes:

### 3.1 La base de conocimiento (y las bases vectoriales)

El repositorio externo de datos: PDFs, documentos, guías, sitios web. En su
mayoría, **datos no estructurados**. Para poder buscarlos por significado se
almacenan en una **base de datos vectorial**: una base que permite almacenar,
indexar y consultar *embeddings* — representaciones numéricas del contenido —
de forma que la **similitud semántica queda representada por la distancia en
el espacio vectorial**. Contenidos que hablan de lo mismo quedan cerca;
contenidos que no, quedan lejos.

Ejemplos: ChromaDB (local, para desarrollo), Pinecone, Qdrant, Weaviate,
PGVector sobre PostgreSQL (para producción). En n8n: el *Simple Vector Store*
en memoria para probar, y conectores a Pinecone, Qdrant, Supabase, PGVector y
Azure AI Search para producción.

### 3.2 El modelo de embeddings (el vectorizador)

Un modelo de IA que convierte texto en vectores. No es el LLM generativo: es
un modelo aparte, más pequeño y barato, especializado en representar
significado. En nuestro stack: los deployments de embeddings de Azure OpenAI
(`text-embedding-3-small` o similar — **es un deployment distinto al de chat,
hay que pedirlo a TI por separado**).

Dos textos con significado parecido («falla por vibración» y «desbalanceo del
rotor») producen vectores cercanos aunque no compartan ninguna palabra. Esa es
toda la magia — y también, como veremos, su talón de Aquiles.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-04-espacio-vectorial.png — la pregunta "¿por qué tiembla el molino?" cae en el clúster de mantenimiento; el radar top-k enciende a sus 3 vecinos y se los lleva al contexto. -->
<div class="c3v4">
<style>
.c3v4{background:#141a26;border-radius:14px;padding:20px 16px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v4 .plano{position:relative;height:260px;max-width:580px;margin:0 auto;background:linear-gradient(#1a2233 1px,transparent 1px),linear-gradient(90deg,#1a2233 1px,transparent 1px);background-size:28px 28px;border:1px solid #33415c;border-radius:10px;overflow:hidden;}
.c3v4 .p{position:absolute;font-size:10.5px;white-space:nowrap;transform:translate(-50%,-50%);}
.c3v4 .p i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:3px;vertical-align:-1px;}
.c3v4 .man i{background:#4caf7d;} .c3v4 .man{color:#9ed9bb;}
.c3v4 .log i{background:#4da3ff;} .c3v4 .log{color:#a8cef5;opacity:.55;}
.c3v4 .com i{background:#f5b942;} .c3v4 .com{color:#f2d49a;opacity:.55;}
.c3v4 .vecino{animation:c3v4prende 2.8s ease-out infinite;}
@keyframes c3v4prende{0%,25%{text-shadow:none;font-weight:400;}40%,80%{text-shadow:0 0 10px rgba(76,175,125,.9);font-weight:700;}100%{text-shadow:none;}}
.c3v4 .lejano{opacity:.5;}
.c3v4 .preg{position:absolute;left:26%;top:30%;transform:translate(-50%,-100%);background:#243550;border:1px solid #4da3ff;border-radius:9px;padding:4px 8px;font-size:10.5px;font-style:italic;color:#c8dcf5;z-index:3;white-space:nowrap;}
.c3v4 .preg::after{content:"";position:absolute;left:50%;bottom:-5px;width:8px;height:8px;background:#243550;border-right:1px solid #4da3ff;border-bottom:1px solid #4da3ff;transform:translateX(-50%) rotate(45deg);}
.c3v4 .estrella{position:absolute;left:26%;top:36%;transform:translate(-50%,-50%);font-size:16px;z-index:2;animation:c3v4titila 1.6s ease-in-out infinite;}
@keyframes c3v4titila{0%,100%{filter:brightness(1);}50%{filter:brightness(1.8);}}
.c3v4 .radar{position:absolute;left:26%;top:36%;border:2px dashed #f5b942;border-radius:50%;transform:translate(-50%,-50%);animation:c3v4radar 2.8s ease-out infinite;}
@keyframes c3v4radar{0%{width:14px;height:14px;opacity:1;}100%{width:170px;height:170px;opacity:0;}}
.c3v4 .cosecha{position:absolute;right:8px;bottom:8px;background:#20302a;border:1.5px solid #4caf7d;border-radius:9px;padding:6px 10px;font-size:10.5px;color:#c9e5d5;animation:c3v4entrega 2.8s ease-in-out infinite;}
@keyframes c3v4entrega{0%,45%{opacity:0;transform:translateY(6px);}60%,92%{opacity:1;transform:translateY(0);}100%{opacity:0;}}
.c3v4 .nota{position:absolute;left:8px;bottom:8px;font-size:9.5px;color:#54627e;max-width:150px;}
.c3v4 .leyenda{display:flex;justify-content:center;gap:16px;margin-top:12px;font-size:11.5px;color:#8fa3c2;flex-wrap:wrap;}
.c3v4 .leyenda i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;}
.c3v4 .pie{text-align:center;margin-top:8px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="plano">
 <span class="preg">«¿por qué tiembla el molino?»</span>
 <span class="p man vecino" style="left:19%;top:25%;"><i></i>vibración</span>
 <span class="p man vecino" style="left:34%;top:27%;"><i></i>rotor</span>
 <span class="p man vecino" style="left:33%;top:45%;"><i></i>desbalanceo</span>
 <span class="p man lejano" style="left:14%;top:52%;"><i></i>rodamiento</span>
 <span class="p log" style="left:76%;top:26%;"><i></i>muelle</span>
 <span class="p log" style="left:85%;top:38%;"><i></i>despacho</span>
 <span class="p log" style="left:72%;top:45%;"><i></i>turno</span>
 <span class="p com" style="left:56%;top:80%;"><i></i>maíz</span>
 <span class="p com" style="left:68%;top:86%;"><i></i>proveedor</span>
 <span class="p com" style="left:48%;top:90%;"><i></i>importación</span>
 <span class="radar"></span>
 <span class="estrella">⭐</span>
 <span class="cosecha">✅ top-3 al contexto:<br><b>vibración · rotor · desbalanceo</b></span>
 <span class="nota">"tiembla" no aparece en ningún documento — y aun así encuentra</span>
</div>
<div class="leyenda"><span><i style="background:#4caf7d;"></i>mantenimiento</span><span><i style="background:#4da3ff;"></i>logística</span><span><i style="background:#f5b942;"></i>compras</span><span>⭐ la pregunta, vectorizada</span></div>
<div class="pie">Significados parecidos = puntos cercanos. El radar es la búsqueda top-k: enciende a los 3 vecinos y se los lleva al contexto — sin compartir ni una palabra con la pregunta.</div>
</div>

### 3.3 El retriever (la recuperación)

El proceso que, dada la pregunta del usuario, encuentra los fragmentos más
relevantes de la base de conocimiento. El flujo completo:

1. **Consulta del usuario** — la pregunta entra al sistema.
2. **Conversión a vector** — la pregunta pasa por el mismo modelo de embeddings.
3. **Búsqueda** — algoritmos de vecinos más cercanos (ANN) encuentran los
   vectores más similares en la base.
4. **Recuperación** — se traen los fragmentos de texto correspondientes.
5. **Enriquecimiento del prompt** — los fragmentos se añaden al contexto.
6. **Generación** — el LLM responde usando ese contexto.

### 3.4 El generador

El LLM que ya conocen — en nuestro caso, el mismo deployment de Azure OpenAI de
la clase 2. Recibe la pregunta del usuario **más** los fragmentos recuperados,
y genera la respuesta. Si el system prompt lo instruye bien (¡la lección de la
clase 2 sigue viva!), responde *solo* desde esos fragmentos y dice "no tengo
esa información" cuando el contexto no alcanza.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-05-pipeline-rag.png — historia completa: un manual se trocea en chunks de colores que caen como puntos a la base vectorial; luego una pregunta pesca el chunk correcto y la respuesta se escribe sola. -->
<div class="c3v5">
<style>
.c3v5{background:#141a26;border-radius:14px;padding:20px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v5 .acto{display:flex;align-items:center;justify-content:center;gap:14px;flex-wrap:wrap;margin:8px 0;}
.c3v5 .titulo{font-size:11px;letter-spacing:1.5px;color:#8fa3c2;text-align:center;margin:6px 0;}
.c3v5 .doc{width:88px;background:#f0f3f8;border-radius:6px;padding:7px;box-shadow:2px 2px 8px rgba(0,0,0,.4);}
.c3v5 .doc .dtit{font-size:7.5px;color:#334;font-weight:700;text-align:center;margin-bottom:4px;}
.c3v5 .doc .sec{height:13px;border-radius:3px;margin:3px 0;}
.c3v5 .s1{background:#bfe6d2;} .c3v5 .s2{background:#f7e3b0;} .c3v5 .s3{background:#c4dcf7;}
.c3v5 .tijera{font-size:17px;animation:c3v5corta 2s ease-in-out infinite;}
@keyframes c3v5corta{0%,100%{transform:rotate(0);}50%{transform:rotate(-18deg);}}
.c3v5 .chunks{display:flex;flex-direction:column;gap:6px;}
.c3v5 .chunk{border-radius:7px;padding:4px 8px;font-size:9.5px;color:#1c2430;font-weight:600;box-shadow:1px 1px 5px rgba(0,0,0,.35);animation:c3v5suelta 9s ease-in-out infinite;}
.c3v5 .c1{background:#bfe6d2;} .c3v5 .c2{background:#f7e3b0;animation-delay:.25s;} .c3v5 .c3{background:#c4dcf7;animation-delay:.5s;}
@keyframes c3v5suelta{0%{opacity:0;transform:translateX(-18px);}6%,100%{opacity:1;transform:translateX(0);}}
.c3v5 .chunk small{display:block;font-size:8px;font-weight:400;color:#3a4a5e;font-family:monospace;}
.c3v5 .db{position:relative;width:96px;height:104px;}
.c3v5 .db .cuerpo{position:absolute;top:12px;bottom:0;left:0;right:0;background:#212b3d;border:2px solid #a78bfa;border-radius:14px 14px 48px 48px/10px 10px 22px 22px;}
.c3v5 .db .tapa{position:absolute;top:0;left:0;right:0;height:24px;background:#2b2545;border:2px solid #a78bfa;border-radius:50%;}
.c3v5 .db .punto{position:absolute;width:11px;height:11px;border-radius:50%;animation:c3v5cae 9s ease-in-out infinite;}
@keyframes c3v5cae{0%,8%{opacity:0;transform:translateY(-26px);}14%,100%{opacity:1;transform:translateY(0);}}
.c3v5 .p1{background:#4caf7d;left:22%;top:42%;}
.c3v5 .p2{background:#f5b942;left:48%;top:60%;animation-delay:.3s;}
.c3v5 .p3{background:#4da3ff;left:68%;top:38%;animation-delay:.6s;}
.c3v5 .p1.match{animation:c3v5cae 9s ease-in-out infinite,c3v5pesca 9s ease-in-out infinite;}
@keyframes c3v5pesca{0%,40%{box-shadow:none;}48%,70%{box-shadow:0 0 0 7px rgba(76,175,125,.35),0 0 14px #4caf7d;}78%,100%{box-shadow:none;}}
.c3v5 .db .etiq{position:absolute;bottom:-18px;left:0;right:0;text-align:center;font-size:9.5px;color:#a78bfa;}
.c3v5 .flecha{color:#54627e;font-size:16px;}
.c3v5 .vector{font-family:monospace;font-size:8.5px;color:#c9b8f5;background:#251f38;border:1px solid #a78bfa;border-radius:5px;padding:2px 5px;}
.c3v5 .burbuja{background:#243550;border:1px solid #4da3ff;border-radius:11px;padding:7px 10px;font-size:11px;font-style:italic;max-width:150px;}
.c3v5 .prompt{background:#1a2233;border:1.5px dashed #54627e;border-radius:10px;padding:8px;font-size:9.5px;max-width:190px;}
.c3v5 .prompt .ptag{font-size:8.5px;color:#8fa3c2;letter-spacing:1px;}
.c3v5 .prompt .pchunk{background:#bfe6d2;color:#1c2430;border-radius:5px;padding:3px 6px;margin-top:4px;font-weight:600;animation:c3v5llega 9s ease-in-out infinite;}
@keyframes c3v5llega{0%,60%{opacity:0;transform:translateX(-14px);}68%,100%{opacity:1;transform:translateX(0);}}
.c3v5 .resp{background:#20302a;border:1.5px solid #4caf7d;border-radius:11px;padding:7px 10px;font-size:10.5px;max-width:210px;color:#c9e5d5;}
.c3v5 .resp .maquina{display:inline-block;overflow:hidden;white-space:nowrap;vertical-align:bottom;border-right:2px solid #4caf7d;animation:c3v5tipea 9s steps(34) infinite;max-width:100%;}
@keyframes c3v5tipea{0%,72%{width:0;}92%,100%{width:100%;}}
.c3v5 .pie{text-align:center;margin-top:20px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="titulo">ACTO 1 · INDEXAR — una sola vez: el manual se vuelve puntos en el espacio</div>
<div class="acto">
 <div class="doc"><div class="dtit">MANUAL MOLINO</div><div class="sec s1"></div><div class="sec s2"></div><div class="sec s3"></div></div>
 <span class="tijera">✂️</span>
 <div class="chunks">
  <div class="chunk c1">§4.2 Vibración <small>→ [0.12, −0.87, …]</small></div>
  <div class="chunk c2">§5.1 Lubricación <small>→ [0.93, 0.04, …]</small></div>
  <div class="chunk c3">§6.3 Rodamientos <small>→ [−0.41, 0.66, …]</small></div>
 </div>
 <span class="flecha">→</span>
 <div class="db"><div class="tapa"></div><div class="cuerpo"><span class="punto p1 match"></span><span class="punto p2"></span><span class="punto p3"></span></div><div class="etiq">base vectorial</div></div>
</div>
<div class="titulo" style="margin-top:24px;">ACTO 2 · CONSULTAR — cada pregunta: pescar el punto cercano y responder con él</div>
<div class="acto">
 <div class="burbuja">«¿qué hago si el molino vibra?»</div>
 <span class="flecha">→</span>
 <span class="vector">[0.11, −0.85, …]</span>
 <span class="flecha">→</span>
 <div style="text-align:center;font-size:9.5px;color:#4caf7d;">🎣 el punto <b>verde</b><br>es el más cercano<br><span style="color:#54627e">(se enciende arriba)</span></div>
 <span class="flecha">→</span>
 <div class="prompt"><span class="ptag">CONTEXTO DEL PROMPT</span><br>pregunta del usuario +<div class="pchunk">§4.2 Vibración: ante &gt;7,1 mm/s, parada programada…</div></div>
 <span class="flecha">→</span>
 <div class="resp">🤖 <span class="maquina">Según el manual §4.2: programa la parada…</span></div>
</div>
<div class="pie">La pregunta se vectoriza con el <b>mismo</b> modelo que indexó el manual ([0.11, −0.85…] ≈ [0.12, −0.87…]) — por eso la distancia es comparable y el punto verde gana.</div>
</div>

### El paso que faltaba: chunking (troceado)

Antes de vectorizar hay que **partir los documentos en fragmentos** (chunks).
No se vectoriza un manual de 50 páginas como un solo vector — se pierde toda la
resolución. Tampoco se vectoriza frase por frase — se pierde el contexto. El
tamaño y la forma del troceado es **la primera decisión de diseño de un RAG**,
y como veremos en la sección 5, la que más silenciosamente lo daña.

---

## 4 · El RAG ingenuo: 10 líneas que funcionan… en la demo

Con un framework, montar un RAG básico es genuinamente corto: cargar los
documentos, trocearlos a tamaño fijo, vectorizarlos a una base local y exponer
la búsqueda. En la clase lo hacemos en vivo sobre el **corpus sintético de
Bios** (manual de mantenimiento del molino, procedimiento de compras, política
de turnos de muelle, fichas técnicas de fórmulas — uno por dominio, igual que
`bios_ops.db`).

Y la primera pregunta funciona de maravilla:

> «¿Qué se debe hacer ante una vibración excesiva en un molino?»
> → recupera la sección correcta del manual y responde fundamentado. ✅

Esto es lo que llamamos **RAG ingenuo** (*naive RAG*): troceado a tamaño fijo,
una sola búsqueda semántica, top-k fijo, sin filtros, y el resultado directo al
prompt. Recupera **una vez**, sin razonar sobre la calidad de lo recuperado, y
la calidad de la respuesta queda completamente limitada por la calidad de ese
único disparo de búsqueda.

En un tutorial, esto es el final. En producción, es el principio de los
problemas — y la industria lo tiene bien documentado: la mayoría de los
sistemas RAG que decepcionan en producción no fallan por el LLM, fallan por el
**pipeline de recuperación**. Lo que sigue es el corazón de esta clase.

---

## 5 · Donde el RAG ingenuo falla — y qué perilla arregla cada fallo

En la sesión plantamos tres fallos a propósito (igual que las anomalías de
`bios_ops.db` en la clase 1). Cada fallo es real, frecuente en producción, y
tiene una optimización estándar que lo corrige.

### Fallo 1 · El código exacto que la búsqueda semántica no encuentra

> «¿Qué dice el manual sobre el equipo **EQ-ITG-MOL-01**?»
> → el RAG ingenuo trae fragmentos de *otro* equipo parecido. ❌

**Por qué pasa.** Los embeddings representan *significado*, y un código como
`EQ-ITG-MOL-01` casi no tiene significado semántico — es un identificador.
Para el espacio vectorial, `EQ-ITG-MOL-01` y `EQ-BUG-MOL-02` son casi el mismo
punto. Sus retos reales están llenos de estos códigos: equipos, pedidos, SKUs,
lotes. Este fallo **les va a pasar**.

**La perilla: búsqueda híbrida.** Combinar la búsqueda densa (vectores, que
entiende significado) con búsqueda por palabras clave tipo **BM25** (que
encuentra coincidencias exactas). Cada una cubre la debilidad de la otra: la
semántica encuentra "desbalanceo" cuando preguntaste "vibración"; la de
keywords encuentra `EQ-ITG-MOL-01` cuando preguntaste por `EQ-ITG-MOL-01`. Los
resultados de ambas se fusionan (típicamente con *Reciprocal Rank Fusion*).

**La perilla complementaria: metadata y filtrado.** Al indexar, cada chunk
lleva metadata estructurada: `{dominio: mantenimiento, planta: Itagüí,
equipo: EQ-ITG-MOL-01, tipo_doc: manual, vigencia: 2026}`. La búsqueda primero
**filtra** de forma determinista (solo chunks del equipo X) y después busca
semánticamente dentro de ese subconjunto. Menos espacio de búsqueda, más
precisión, y además habilita control de acceso y vigencias — cosas que en una
empresa importan tanto como la relevancia.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-06-busqueda-hibrida.png — la misma pregunta lanzada a tres buscadores: la semántica trae el equipo EQUIVOCADO, la keyword clava el código, la híbrida corrige el ranking. -->
<div class="c3v6">
<style>
.c3v6{background:#141a26;border-radius:14px;padding:22px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v6 .preg{text-align:center;font-size:13px;font-style:italic;background:#243550;border:1px solid #4da3ff;border-radius:10px;padding:7px 12px;max-width:380px;margin:0 auto 14px;}
.c3v6 .preg b{color:#ffd77a;font-style:normal;}
.c3v6 .cols{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;}
.c3v6 .buscador{width:230px;background:#1a2233;border:1px solid #33415c;border-radius:11px;padding:10px;animation:c3v6entra 10s ease-in-out infinite;}
.c3v6 .b2{animation-delay:1.2s;opacity:0;}
.c3v6 .b3{animation-delay:2.6s;opacity:0;border:2px solid #f5b942;}
@keyframes c3v6entra{0%{opacity:0;transform:translateY(10px);}8%,96%{opacity:1;transform:translateY(0);}100%{opacity:0;}}
.c3v6 .btitulo{text-align:center;font-size:11.5px;font-weight:700;margin-bottom:7px;}
.c3v6 .b1 .btitulo{color:#4caf7d;}
.c3v6 .b2 .btitulo{color:#4da3ff;}
.c3v6 .b3 .btitulo{color:#f5b942;}
.c3v6 .res{display:flex;gap:6px;align-items:baseline;background:#212b3d;border:1px solid #33415c;border-radius:7px;padding:5px 7px;margin:5px 0;font-size:10px;color:#c8d4e6;}
.c3v6 .res .pos{color:#54627e;font-weight:700;}
.c3v6 .res code{font-size:9.5px;}
.c3v6 .error{border-color:#ff6b6b;animation:c3v6mal 1.6s ease-in-out infinite;}
@keyframes c3v6mal{0%,100%{background:#212b3d;}50%{background:#3a2026;}}
.c3v6 .acierto{border-color:#4caf7d;background:#20302a;}
.c3v6 .acierto code{color:#7fe0ac;font-weight:700;}
.c3v6 .gana{animation:c3v6oro 2.2s ease-in-out infinite;}
@keyframes c3v6oro{0%,100%{box-shadow:0 0 0 0 rgba(245,185,66,.45);}50%{box-shadow:0 0 0 8px rgba(245,185,66,0);}}
.c3v6 .veredicto{text-align:center;font-size:10px;margin-top:7px;}
.c3v6 .b1 .veredicto{color:#ff9f9f;}
.c3v6 .b2 .veredicto{color:#a8cef5;}
.c3v6 .b3 .veredicto{color:#f2d49a;}
.c3v6 .metadato{text-align:center;font-size:10.5px;color:#c9b8f5;margin-top:12px;}
.c3v6 .pie{text-align:center;margin-top:8px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="preg">«¿Qué dice el manual sobre <b>EQ-ITG-MOL-01</b>?»</div>
<div class="cols">
 <div class="buscador b1">
  <div class="btitulo">solo semántica (vectores)</div>
  <div class="res error"><span class="pos">1.</span><span>§5 Molino <code>EQ-BUG-MOL-02</code> — ¡equipo equivocado!</span></div>
  <div class="res"><span class="pos">2.</span><span>§2 Vibración: generalidades</span></div>
  <div class="res"><span class="pos">3.</span><span>§6 Rodamientos</span></div>
  <div class="veredicto">❌ para el vector, los dos códigos son casi el mismo punto</div>
 </div>
 <div class="buscador b2">
  <div class="btitulo">solo keyword (BM25)</div>
  <div class="res acierto"><span class="pos">1.</span><span>§4.2 <code>EQ-ITG-MOL-01</code> — coincidencia exacta</span></div>
  <div class="res"><span class="pos">2.</span><span>Anexo A: ficha <code>EQ-ITG-MOL-01</code></span></div>
  <div class="res"><span class="pos">3.</span><span style="color:#54627e;">— (no entiende sinónimos)</span></div>
  <div class="veredicto">✅ el código exacto sí aparece — pero es ciega a "tiembla"≈"vibra"</div>
 </div>
 <div class="buscador b3">
  <div class="btitulo">⚡ híbrida — fusión de ambas (RRF)</div>
  <div class="res acierto gana"><span class="pos">1.</span><span>§4.2 <code>EQ-ITG-MOL-01</code> — procedimiento de vibración</span></div>
  <div class="res"><span class="pos">2.</span><span>Anexo A: ficha del equipo</span></div>
  <div class="res"><span class="pos">3.</span><span>§2 Vibración: generalidades</span></div>
  <div class="veredicto">✅ el ranking correcto: exactitud de BM25 + significado de los vectores</div>
 </div>
</div>
<div class="metadato">🔒 y antes de todo, el <b>filtro por metadata</b> ya acotó: solo docs de <code>planta=Itagüí</code>, vigentes</div>
<div class="pie">La misma pregunta, tres buscadores. Sus retos están llenos de códigos (equipos, pedidos, SKUs): la híbrida no es un lujo, es la diferencia entre encontrar y no encontrar.</div>
</div>

### Fallo 2 · La pregunta multi-turno que el retriever no entiende

> Turno 1: «¿Qué mantenimiento preventivo tiene el molino de Itagüí?» ✅
> Turno 2: «¿Y cada cuánto se hace?»
> → el RAG ingenuo busca literalmente "¿y cada cuánto se hace?" y trae basura. ❌

**Por qué pasa.** El agente tiene memoria (la construimos en la clase 2), pero
el **retriever no** — recibe la pregunta cruda, sin el contexto de la
conversación. "¿Y cada cuánto se hace?" no se parece semánticamente a nada del
manual.

**La perilla: reescritura de consulta (query rewriting).** Antes de buscar, un
paso barato de LLM reescribe la pregunta usando el historial: «¿y cada cuánto
se hace?» → «¿con qué frecuencia se realiza el mantenimiento preventivo del
molino de la planta Itagüí?». La búsqueda ahora sí encuentra. Variante
poderosa: **expansión multi-query** — generar 2 o 3 reformulaciones de la
pregunta, buscar con todas y unir los resultados; es de las técnicas con mejor
relación costo/beneficio para cerrar la brecha semántica entre cómo pregunta
la gente y cómo están escritos los documentos.

Este es el momento más bonito de continuidad del programa: **la memoria que
construyeron en la S2 es el insumo que alimenta la reescritura en la S3.**

### Fallo 3 · El chunk que corta la información por la mitad

> «¿Cuál es la tolerancia de vibración del molino en operación normal?»
> → el RAG ingenuo trae la mitad de una tabla; la respuesta cita el
> encabezado pero el valor quedó en el chunk siguiente. ❌

**Por qué pasa.** El troceado a tamaño fijo (p. ej. cada 500 tokens) no sabe
dónde empiezan y terminan las ideas: corta tablas, separa un título de su
contenido, parte un procedimiento en dos. Chunks pequeños fragmentan; chunks
grandes meten ruido irrelevante al contexto.

**La perilla: chunking consciente de la estructura.** Trocear respetando la
estructura del documento — secciones, encabezados, tablas completas — con
solapamiento (*overlap*) entre chunks vecinos. Para dominios densos existe el
chunking semántico (dejar que un modelo decida los cortes por cambio de tema).

**La perilla complementaria: recuperación padre-hijo (parent-document
retrieval).** Lo mejor de dos mundos: se **busca** con chunks pequeños (mejor
precisión de búsqueda) pero al LLM se le **entrega** la sección completa que
contiene al chunk encontrado (mejor contexto para razonar). Buscar fino,
entregar ancho.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-07-chunking-padre-hijo.png — troceado fijo que corta una tabla vs. estructural con recuperación padre-hijo. -->
<div class="c3v7">
<style>
.c3v7{background:#141a26;border-radius:14px;padding:22px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v7 .paneles{display:flex;justify-content:center;gap:22px;flex-wrap:wrap;}
.c3v7 .panel{flex:1;min-width:250px;max-width:330px;}
.c3v7 .titulo{text-align:center;font-size:12.5px;font-weight:700;margin-bottom:8px;}
.c3v7 .malo .titulo{color:#ff6b6b;}
.c3v7 .bueno .titulo{color:#4caf7d;}
.c3v7 .doc{position:relative;background:#212b3d;border:1px solid #33415c;border-radius:8px;padding:12px;}
.c3v7 .linea{height:6px;background:#33415c;border-radius:3px;margin:6px 0;}
.c3v7 .l70{width:70%;} .c3v7 .l90{width:90%;} .c3v7 .l50{width:50%;}
.c3v7 .tabla{border:1px solid #54627e;border-radius:4px;margin:8px 0;}
.c3v7 .tr{display:flex;}
.c3v7 .td{flex:1;border:1px solid #54627e;padding:3px 5px;font-size:9.5px;color:#8fa3c2;text-align:center;}
.c3v7 .corte{position:absolute;left:-4px;right:-4px;top:56%;border-top:3px dashed #ff6b6b;animation:c3v7parpadea 1.4s ease-in-out infinite;}
.c3v7 .corte::after{content:"✂️ corte del chunk a los 500 tokens";position:absolute;right:2px;top:-20px;font-size:10px;color:#ff6b6b;background:#141a26;padding:0 5px;border-radius:4px;}
@keyframes c3v7parpadea{0%,100%{opacity:1;}50%{opacity:.25;}}
.c3v7 .seccion{border:1px solid #54627e;border-radius:6px;padding:7px;margin:7px 0;position:relative;}
.c3v7 .sectag{font-size:9.5px;color:#8fa3c2;}
.c3v7 .padre{border:2px solid transparent;animation:c3v7abraza 4s ease-in-out infinite;}
@keyframes c3v7abraza{0%,25%,100%{border-color:transparent;background:transparent;}45%,80%{border-color:#4caf7d;background:rgba(76,175,125,.07);}}
.c3v7 .padre::after{content:"sección padre → al LLM";position:absolute;right:6px;bottom:-9px;font-size:9.5px;color:#4caf7d;background:#141a26;padding:0 5px;border-radius:4px;opacity:0;animation:c3v7etiqueta 4s ease-in-out infinite;}
@keyframes c3v7etiqueta{0%,25%,100%{opacity:0;}45%,80%{opacity:1;}}
.c3v7 .hijo{background:rgba(245,185,66,.14);border:1px solid #f5b942;border-radius:4px;padding:2px 5px;font-size:9.5px;color:#f2d49a;display:inline-block;animation:c3v7hijo 4s ease-in-out infinite;}
@keyframes c3v7hijo{0%,100%{box-shadow:0 0 0 0 rgba(245,185,66,.5);}12%{box-shadow:0 0 0 7px rgba(245,185,66,0);}}
.c3v7 .veredicto{text-align:center;font-size:11.5px;margin-top:8px;color:#8fa3c2;}
.c3v7 .pie{text-align:center;margin-top:12px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="paneles">
 <div class="panel malo">
  <div class="titulo">Troceado fijo (ingenuo)</div>
  <div class="doc">
   <div class="linea l90"></div><div class="linea l70"></div>
   <div class="tabla">
    <div class="tr"><div class="td"><b>Tolerancias de vibración</b></div></div>
    <div class="tr"><div class="td">operación normal</div><div class="td">alerta</div></div>
    <div class="tr"><div class="td">≤ 4,5 mm/s</div><div class="td">4,5–7,1 mm/s</div></div>
   </div>
   <div class="linea l50"></div><div class="linea l90"></div>
   <div class="corte"></div>
  </div>
  <div class="veredicto">❌ el encabezado queda en un chunk y el valor en otro</div>
 </div>
 <div class="panel bueno">
  <div class="titulo">Estructural + padre-hijo</div>
  <div class="doc">
   <div class="seccion"><span class="sectag">§4.1 Lubricación</span><div class="linea l70"></div></div>
   <div class="seccion padre"><span class="sectag">§4.2 Vibración — completa, tabla incluida</span><div class="linea l90"></div><span class="hijo">chunk hijo: matchea la búsqueda 🔍</span><div class="linea l50"></div></div>
   <div class="seccion"><span class="sectag">§4.3 Rodamientos</span><div class="linea l70"></div></div>
  </div>
  <div class="veredicto">✅ se busca con el chunk chico, se entrega la sección entera</div>
 </div>
</div>
<div class="pie"><b>Buscar fino, entregar ancho:</b> precisión en la búsqueda, contexto completo para razonar.</div>
</div>

### La cuarta perilla: re-ranking (el pulido final)

Con la recuperación ya sana, queda un refinamiento: recuperar más candidatos de
los necesarios (p. ej. top-20) y pasarlos por un **re-ranker** — un modelo
(*cross-encoder*) que lee pregunta y fragmento **juntos** y les da un puntaje
de relevancia mucho más fino que la similitud de vectores — para quedarse solo
con los 3–5 mejores. Mejora la precisión y reduce el ruido que entra al
contexto.

**Advertencia de ingeniería** (respaldada por la experiencia de la industria):
el re-ranking es la **última** perilla, no la primera. Poner un re-ranker
encima de un chunking roto y una búsqueda sin filtros es pulir un pipeline
dañado. El orden de trabajo sano es: (1) chunking y parsing, (2) metadata y
filtrado, (3) búsqueda híbrida, (4) reescritura de consulta, y solo entonces
(5) re-ranking.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-08-escalera-optimizaciones.png — escalera de 5 optimizaciones que se iluminan en secuencia. -->
<div class="c3v8">
<style>
.c3v8{background:#141a26;border-radius:14px;padding:22px 16px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v8 .marco{max-width:520px;margin:0 auto;}
.c3v8 .cima{text-align:right;font-size:12px;color:#4caf7d;font-weight:700;margin-bottom:6px;}
.c3v8 .base{font-size:12px;color:#ff6b6b;font-weight:700;margin-top:6px;}
.c3v8 .peld{background:#212b3d;border:2px solid #33415c;border-radius:9px;padding:8px 12px;margin:6px 0;font-size:12.5px;animation:c3v8luz 10s ease-in-out infinite;}
.c3v8 .peld small{display:block;font-size:10.5px;color:#8fa3c2;}
.c3v8 .p5{margin-left:44%;animation-delay:8s;}
.c3v8 .p4{margin-left:33%;animation-delay:6s;}
.c3v8 .p3{margin-left:22%;animation-delay:4s;}
.c3v8 .p2{margin-left:11%;animation-delay:2s;}
.c3v8 .p1{margin-left:0;animation-delay:0s;}
@keyframes c3v8luz{0%,18%{border-color:#f5b942;background:#2a2413;box-shadow:0 0 12px rgba(245,185,66,.35);}22%,100%{border-color:#33415c;background:#212b3d;box-shadow:none;}}
.c3v8 .pie{text-align:center;margin-top:12px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="marco">
<div class="cima">🏁 RAG de producción</div>
<div class="peld p5"><b>5 · Re-ranking</b> — el pulido final<small>resuelve: ruido en el top-k · cross-encoder reordena y filtra</small></div>
<div class="peld p4"><b>4 · Query rewriting</b><small>resuelve: «¿y cada cuánto se hace?» — reescribe con la memoria de la conversación</small></div>
<div class="peld p3"><b>3 · Búsqueda híbrida</b><small>resuelve: códigos exactos (EQ-ITG-MOL-01) — vectores + BM25</small></div>
<div class="peld p2"><b>2 · Metadata + filtrado</b><small>resuelve: búsqueda sin dirección — planta, equipo, vigencia, acceso</small></div>
<div class="peld p1"><b>1 · Chunking estructural</b><small>resuelve: información cortada por la mitad — secciones, tablas, overlap</small></div>
<div class="base">⚠️ RAG ingenuo</div>
</div>
<div class="pie">Se sube en orden: poner un re-ranker sobre un chunking roto es pulir un pipeline dañado.</div>
</div>

---

## 6 · RAG agéntico: la búsqueda dentro del loop ReAct

Todo lo anterior optimiza **la búsqueda**. Falta optimizar **el uso** de la
búsqueda — y eso ya lo saben hacer, porque es la clase 2.

En el RAG ingenuo, el pipeline es lineal: pregunta → buscar una vez → responder
con lo que salga. En el **RAG agéntico**, la búsqueda es una **tool** dentro
del loop ReAct, y el agente:

- **decide cuándo buscar** (una pregunta de cifras va a la tool SQL; una de
  procedimientos, a la tool de documentos; un saludo, a ninguna);
- **evalúa lo recuperado** y puede **volver a buscar** con otra consulta si el
  primer resultado no le sirvió;
- **combina fuentes** en una misma respuesta.

La pregunta de cierre de la demo une las tres clases:

> «El equipo EQ-ITG-MOL-01 lleva dos correctivos por vibración este mes.
> ¿Qué procedimiento debo seguir según el manual?»

El agente llama `historial_fallas` (tool SQL de la clase 2) para confirmar el
dato, llama `buscar_documentos` (tool RAG de hoy) para traer el procedimiento,
y compone una respuesta que ninguna de las dos fuentes tenía completa. **Eso**
es un agente con sus datos.

El costo de esta flexibilidad es real y hay que decirlo: más llamadas al LLM
por respuesta significa más latencia y más costo por consulta. En sus proyectos
la decisión "¿pipeline RAG fijo o RAG agéntico?" se toma por caso de uso, no
por moda — un chatbot de consulta de políticas puede vivir con un pipeline
fijo; un copiloto de operaciones que cruza cifras y procedimientos necesita el
agente.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-09-rag-agentico.png — el loop ReAct girando junto a una terminal donde la traza real aparece línea por línea: el agente combina la tool SQL y la tool RAG en una misma respuesta. -->
<div class="c3v9">
<style>
.c3v9{background:#141a26;border-radius:14px;padding:22px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v9 .escena{display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap;}
.c3v9 .orbita{position:relative;width:170px;height:170px;flex-shrink:0;}
.c3v9 .aro{position:absolute;inset:20px;border:2px dashed #54627e;border-radius:50%;}
.c3v9 .rotor{position:absolute;inset:20px;animation:c3v9gira 6s linear infinite;}
@keyframes c3v9gira{to{transform:rotate(360deg);}}
.c3v9 .satelite{position:absolute;top:-6px;left:50%;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:#f5b942;box-shadow:0 0 10px rgba(245,185,66,.8);}
.c3v9 .etq{position:absolute;font-size:10px;font-weight:700;background:#212b3d;border:1px solid #33415c;border-radius:12px;padding:2px 7px;}
.c3v9 .thought{top:0;left:50%;transform:translateX(-50%);color:#4da3ff;}
.c3v9 .action{bottom:22%;right:-12px;color:#4caf7d;}
.c3v9 .obs{bottom:22%;left:-16px;color:#a78bfa;}
.c3v9 .centro{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:21px;}
.c3v9 .term{width:430px;max-width:100%;background:#0d1117;border:1px solid #33415c;border-radius:10px;overflow:hidden;box-shadow:0 4px 18px rgba(0,0,0,.4);}
.c3v9 .barra{background:#1a2233;padding:6px 10px;display:flex;gap:5px;align-items:center;}
.c3v9 .barra i{width:9px;height:9px;border-radius:50%;display:inline-block;}
.c3v9 .barra .tit{margin-left:8px;font-size:9.5px;color:#8fa3c2;}
.c3v9 .cuerpo{padding:10px 12px;font-family:'SF Mono',Menlo,monospace;font-size:10px;line-height:1.75;}
.c3v9 .ln{opacity:0;animation:c3v9linea 14s ease-in-out infinite;}
.c3v9 .l1{animation-delay:.3s;} .c3v9 .l2{animation-delay:1.6s;} .c3v9 .l3{animation-delay:2.9s;}
.c3v9 .l4{animation-delay:4.2s;} .c3v9 .l5{animation-delay:5.5s;} .c3v9 .l6{animation-delay:6.8s;}
.c3v9 .l7{animation-delay:8.4s;}
@keyframes c3v9linea{0%{opacity:0;transform:translateY(4px);}4%,92%{opacity:1;transform:translateY(0);}100%{opacity:0;}}
.c3v9 .usr{color:#e6edf3;}
.c3v9 .tht{color:#4da3ff;}
.c3v9 .act{color:#4caf7d;}
.c3v9 .actrag{color:#f5b942;}
.c3v9 .obsv{color:#a78bfa;}
.c3v9 .rsp{color:#7fe0ac;}
.c3v9 .marca{float:right;font-size:8.5px;border-radius:8px;padding:0 6px;font-weight:700;}
.c3v9 .msql{background:#1e3a2c;color:#7fe0ac;}
.c3v9 .mrag{background:#3a3013;color:#ffd77a;}
.c3v9 .pie{text-align:center;margin-top:14px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="escena">
 <div class="orbita">
  <div class="aro"></div>
  <div class="rotor"><div class="satelite"></div></div>
  <span class="etq thought">Thought</span>
  <span class="etq action">Action</span>
  <span class="etq obs">Observation</span>
  <span class="centro">🤖</span>
 </div>
 <div class="term">
  <div class="barra"><i style="background:#ff5f56;"></i><i style="background:#ffbd2e;"></i><i style="background:#27c93f;"></i><span class="tit">agente-con-datos — la demo de cierre, en vivo</span></div>
  <div class="cuerpo">
   <div class="ln l1 usr">tú › EQ-ITG-MOL-01 lleva 2 correctivos por vibración, ¿qué hago?</div>
   <div class="ln l2 tht">[Thought] necesito confirmar el historial y consultar el manual</div>
   <div class="ln l3 act">[Action] historial_fallas("Itagüí") <span class="marca msql">tool SQL · clase 2</span></div>
   <div class="ln l4 obsv">[Observation] 2 correctivos · causa: desbalanceo de rotor</div>
   <div class="ln l5 actrag">[Action] buscar_documentos("procedimiento vibración molino") <span class="marca mrag">tool RAG · hoy</span></div>
   <div class="ln l6 obsv">[Observation] manual §4.2: parada programada + verificar balanceo</div>
   <div class="ln l7 rsp">[Respuesta] Confirmado: 2 correctivos por desbalanceo. El manual<br>§4.2 indica programar parada y verificar el balanceo del rotor. ✔</div>
  </div>
 </div>
</div>
<div class="pie">Una sola pregunta, dos fuentes: la <b>cifra</b> sale de la base SQL (clase 2) y el <b>procedimiento</b> del manual (hoy). Ninguna fuente tenía la respuesta completa — el loop ReAct las combinó. Y si lo recuperado no alcanza, reformula y vuelve a buscar.</div>
</div>

---

## 7 · El mismo RAG en n8n

Como en la clase 2, el concepto vive independiente del medio. En n8n, un RAG
son **dos workflows**:

1. **Ingesta (una vez):** *Document Loader* → *Text Splitter* (¡acá viven las
   decisiones de chunking!) → *Embeddings Azure OpenAI* → *Vector Store* en
   modo insert.
2. **Consulta (cada pregunta):** el **mismo workflow del agente de la clase 2**
   gana un sub-nodo *Vector Store Tool* conectado al *AI Agent* — la búsqueda
   como herramienta, exactamente la lección de la sección 6.

Equivalencias directas con lo que vimos en Python:

| Concepto | Python (LangChain) | n8n |
|---|---|---|
| Troceado | `TextSplitter` | Nodo *Text Splitter* del loader |
| Embeddings | `AzureOpenAIEmbeddings` | Nodo *Embeddings Azure OpenAI* |
| Base vectorial | ChromaDB local | *Simple Vector Store* (pruebas) / Qdrant, Pinecone, PGVector (producción) |
| Búsqueda como tool | `StructuredTool` sobre el retriever | Sub-nodo *Vector Store Tool* del AI Agent |
| Re-ranking | retriever con cross-encoder | Nodo *Reranker* (p. ej. Cohere) sobre el vector store |

**Honestidad técnica para sus proyectos:** n8n cubre muy bien el RAG estándar
(chunking configurable, top-k, metadata, re-ranking según la instancia); las
optimizaciones más finas (búsqueda híbrida a medida, reescritura de consulta
personalizada, padre-hijo) dependen del vector store elegido o piden código.
Ese es justamente el criterio de decisión código-vs-low-code que cada Champion
debe poder argumentar al salir de esta sesión.

<!-- Visual animado (CSS puro). Imagen estática opcional: images/3-10-n8n-rag.png — canvas n8n con workflow de ingesta y el agente de la S2 ganando el Vector Store Tool. -->
<div class="c3v10">
<style>
.c3v10{background:#141a26;border-radius:14px;padding:20px 14px;font-family:-apple-system,'Segoe UI',sans-serif;color:#dbe4f0;}
.c3v10 .canvas{background:radial-gradient(#22293a 1.2px,transparent 1.2px);background-size:16px 16px;border:1px solid #33415c;border-radius:10px;padding:14px;margin:8px 0;}
.c3v10 .wf{font-size:11px;letter-spacing:1.2px;color:#8fa3c2;margin-bottom:8px;}
.c3v10 .fila{display:flex;align-items:center;justify-content:center;gap:0;flex-wrap:wrap;}
.c3v10 .nodo{background:#212b3d;border:2px solid #33415c;border-radius:9px;padding:7px 10px;font-size:11.5px;text-align:center;margin:3px 0;}
.c3v10 .nodo small{display:block;font-size:9.5px;color:#8fa3c2;}
.c3v10 .cx{width:26px;height:3px;margin:0 2px;background:repeating-linear-gradient(90deg,#54627e 0 6px,transparent 6px 12px);animation:c3v10fluye 1.1s linear infinite;flex-shrink:0;}
@keyframes c3v10fluye{to{background-position:12px 0;}}
.c3v10 .sub{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap;}
.c3v10 .subnodo{background:#1a2233;border:1.5px solid #33415c;border-radius:8px;padding:5px 9px;font-size:10.5px;color:#8fa3c2;}
.c3v10 .nuevo{border-color:#4caf7d;color:#9ed9bb;animation:c3v10late 2s ease-in-out infinite;}
@keyframes c3v10late{0%,100%{box-shadow:0 0 0 0 rgba(76,175,125,.55);}50%{box-shadow:0 0 0 9px rgba(76,175,125,0);}}
.c3v10 .tag{font-size:8.5px;background:#4caf7d;color:#141a26;border-radius:7px;padding:0 5px;font-weight:700;vertical-align:1px;}
.c3v10 .compartido{border-color:#a78bfa;}
.c3v10 .puente{text-align:center;font-size:10.5px;color:#a78bfa;margin:2px 0;animation:c3v10titila 2.4s ease-in-out infinite;}
@keyframes c3v10titila{0%,100%{opacity:.9;}50%{opacity:.35;}}
.c3v10 .pie{text-align:center;margin-top:8px;font-size:11.5px;color:#8fa3c2;}
</style>
<div class="canvas">
<div class="wf">WORKFLOW 1 · INGESTA — una vez</div>
<div class="fila">
 <div class="nodo">📂 Document Loader<small>corpus sintético Bios</small></div><span class="cx"></span>
 <div class="nodo">✂️ Text Splitter<small>acá vive el chunking</small></div><span class="cx"></span>
 <div class="nodo">🧮 Embeddings<small>Azure OpenAI</small></div><span class="cx"></span>
 <div class="nodo compartido">🗄️ Vector Store<small>modo insert</small></div>
</div>
</div>
<div class="puente">▼ &nbsp;misma base vectorial&nbsp; ▼</div>
<div class="canvas">
<div class="wf">WORKFLOW 2 · CONSULTA — el agente de la clase 2, con un brazo nuevo</div>
<div class="fila">
 <div class="nodo">💬 Chat Trigger<small>= chat.py</small></div><span class="cx"></span>
 <div class="nodo">🤖 AI Agent<small>= loop.py / create_react_agent</small></div><span class="cx"></span>
 <div class="nodo">📤 Respuesta</div>
</div>
<div class="sub">
 <div class="subnodo">🧠 Window Buffer Memory<small>= memoria.py</small></div>
 <div class="subnodo">📊 4 tools SQL<small>= tools.py</small></div>
 <div class="subnodo nuevo">📄 Vector Store Tool <span class="tag">NUEVO</span><small>la búsqueda como herramienta</small></div>
</div>
</div>
<div class="pie">No es un workflow nuevo: es el mismo agente de la S2 al que se le conecta un sub-nodo más. La lección de la sección 6, en visual.</div>
</div>

---

## 8 · ¿Y cómo sé si mi RAG responde bien? (evaluación, en una probada)

Pregunta obligada antes de llevar cualquier RAG a producción. El marco mental
mínimo son tres preguntas sobre cada respuesta:

1. **¿Recuperó lo correcto?** (precisión del contexto — ¿los chunks traídos
   eran los relevantes?)
2. **¿Respondió desde lo recuperado?** (fidelidad / *groundedness* — ¿o se
   inventó algo que no estaba en el contexto?)
3. **¿Respondió lo que se preguntó?** (relevancia de la respuesta)

Existen frameworks que automatizan estas métricas (RAGAS, DeepEval, las
evaluaciones de LangSmith) y en la industria se acepta que **un RAG sin
evaluación estructurada es un RAG que alucina sin que nadie lo note**. En esta
sesión basta con instalar el marco mental; la implementación de evals entra en
el acompañamiento (S5–S7) cuando cada proyecto lo requiera.

---

## 9 · El candado de siempre: datos sintéticos

Todo lo que este agente recupera **se envía al proveedor del modelo** (Azure
OpenAI) como parte del contexto. Por eso, igual que en las clases 1 y 2:

- El corpus documental de la clase es **sintético**: manuales, procedimientos y
  políticas **ficticios**, escritos para esta formación. No representan la
  operación real de Grupo Bios.
- Conectar el RAG a documentos reales (SharePoint, intranet, contratos) exige
  resolver **antes** el contrato de tratamiento de la información con TI y
  Legal: clasificación de la información, controles de retención del proveedor
  y control de acceso por metadata. En la S3 la tentación de "subir un PDF
  real para probar" va a ser fuerte — no se hace. Ese paso se da en el
  acompañamiento, proyecto por proyecto, con el candado resuelto.

---

## 10 · Síntesis: lo que se llevan de la sesión 3

1. La memoria de un agente tiene capas: la **conversacional** ya la
   construyeron (S2); los **documentos de la organización son su memoria
   semántica**, y RAG es cómo el agente la consulta.
2. RAG = **recuperar + generar**: base de conocimiento vectorizada, embeddings,
   retriever y generador. El chunking es la primera decisión de diseño.
3. El **RAG ingenuo funciona en demos y falla en producción** — y falla de
   formas predecibles: códigos exactos, preguntas multi-turno, información
   cortada por el troceado.
4. Las perillas, en orden: **chunking estructural → metadata y filtrado →
   búsqueda híbrida → reescritura de consulta → re-ranking**. El re-ranking es
   el pulido, no el fundamento.
5. **RAG agéntico**: la búsqueda es una tool dentro del loop ReAct que ya
   construyeron. El agente decide cuándo buscar, reintenta y combina fuentes
   (SQL + documentos). Cuesta más latencia y tokens: se elige por caso de uso.
6. Sin **evaluación** (contexto correcto, fidelidad, relevancia), un RAG
   alucina sin que nadie lo note.
7. **Datos reales solo con el contrato de tratamiento resuelto.** Sintético
   hasta entonces.

**La próxima sesión:** su agente deja de estar solo — Skills, MCP y
arquitecturas multiagente. De un agente con sus datos, a un equipo de agentes.

---

## Referencias

**Material base del programa:**

- IBM — [AI Agent Memory](https://www.ibm.com/think/topics/ai-agent-memory) y
  [Retrieval-Augmented Generation](https://www.ibm.com/think/topics/retrieval-augmented-generation)
- LangChain — [Memory for Agents](https://blog.langchain.com/memory-for-agents/)
- AWS — [What is RAG?](https://aws.amazon.com/es/what-is/retrieval-augmented-generation/)
  y [GraphRAG en Amazon Bedrock](https://aws.amazon.com/es/blogs/machine-learning/improving-retrieval-augmented-generation-accuracy-with-graphrag/)
- Google Cloud — [RAG use cases](https://cloud.google.com/use-cases/retrieval-augmented-generation?hl=es)
  y [What is a vector database?](https://cloud.google.com/discover/what-is-a-vector-database?hl=es)
- Medium (A. Igbokwe) — [Long-Term Memory in AI Agents](https://medium.com/@alozie_igbokwe/ai-101-long-term-memory-in-ai-agents-35f87f2d0ce0)
- Tekne Data Labs — [¿Cuál es la mejor base vectorial para tu agente?](https://teknedatalabs.com/es/cual-es-la-mejor-base-de-datos-vectorial-para-tu-agente-de-ia/)

**Optimizaciones de RAG (sección 5):**

- Wang et al. (2024) — [Searching for Best Practices in Retrieval-Augmented Generation](https://arxiv.org/pdf/2407.01219) (arXiv)
- Tensoria — [How to Optimize a RAG System: 5 Levers That Actually Move the Needle](https://tensoria.fr/en/blog/optimize-rag-system-5-levers)
- StackAI — [RAG Best Practices for Enterprise AI: Chunking, Embeddings, Reranking, Hybrid Search](https://www.stackai.com/insights/retrieval-augmented-generation-(rag)-best-practices-for-enterprise-ai-chunking-embeddings-reranking-and-hybrid-search-optimization)
- Unstructured — [Metadata for RAG: Improve Contextual Retrieval](https://unstructured.io/insights/how-to-use-metadata-in-rag-for-better-contextual-results)
- Towards Data Science — [LangChain's Parent Document Retriever, Revisited](https://towardsdatascience.com/langchains-parent-document-retriever-revisited-1fca8791f5a0/)
- DZone — [Parent Document Retrieval: Useful Technique in RAG](https://dzone.com/articles/parent-document-retrieval-useful-technique-in-rag)

**RAG agéntico (sección 6):**

- Weaviate — [What is Agentic RAG?](https://weaviate.io/blog/what-is-agentic-rag)
- Vellum — [Agentic RAG: Architecture, Use Cases, and Limitations](https://www.vellum.ai/blog/agentic-rag)
- DigitalOcean — [RAG, AI Agents, and Agentic RAG: Comparative Analysis](https://www.digitalocean.com/community/conceptual-articles/rag-ai-agents-agentic-rag-comparative-analysis)

**n8n (sección 7):**

- n8n Docs — [RAG in n8n](https://docs.n8n.io/advanced-ai/rag-in-n8n/)
- n8n — [Workflow: PDF RAG con reranking de Cohere](https://n8n.io/workflows/5734-build-a-pdf-based-rag-system-with-openai-pinecone-and-cohere-reranking/)
