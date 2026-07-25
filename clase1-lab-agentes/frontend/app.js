/* ==========================================================================
   Tablero de Agencia — lógica de vista. Spec 07.

   Tres vistas:

     · paso        Un nivel a la vez, con su diagrama encendiéndose conforme
                   corre. Es el modo con el que se explica en clase, y el
                   predeterminado: cinco columnas avanzando a la vez son
                   fantásticas para el cierre y un estorbo para explicar.
     · comparacion Los cinco en paralelo. El momento del minuto 50.
     · detalle     La traza completa y el prompt editable.

   El frontend NO sabe qué nivel está renderizando. Ni el diagrama: lo describe
   el backend en `/api/niveles` y acá se dibuja de forma genérica. Un sexto nivel
   no obliga a tocar este archivo.
   ========================================================================== */

function tablero() {
  return {
    // Motor del diagrama animado (frontend/diagrama.js): geometría, paquetes que
    // recorren las aristas y repetición sin gastar API.
    ...mezclaDiagrama(),

    vista: "paso",
    salud: {},
    gasto: {},
    niveles: [],
    preguntas: [],
    pregunta: "",
    // Modo paso a paso
    nivelActual: "n1",
    // Modo comparación
    seleccion: ["n1", "n2", "n3", "n4", "n5"],
    columnas: {},
    estadoNodos: {},
    corriendo: false,
    enCurso: [],
    runId: null,
    fuente: null,
    bannerReplay: null,
    modoPrevio: null,
    temaOscuro: false,
    nivelDetalle: "n3",
    promptEditado: "",
    promptGuardado: false,
    prompts: {},

    // --- Arranque --------------------------------------------------------

    async iniciar() {
      this.temaOscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
      await this.refrescarSalud();
      this.modoPrevio = this.salud.modo;
      if (this.salud.modo === "replay") {
        this.bannerReplay =
          this.salud.aviso_replay ||
          "Modo replay: lo que ves a continuación son trazas pregrabadas, no ejecución real.";
      }
      const [niveles, preguntas, prompts] = await Promise.all([
        fetch("/api/niveles").then((r) => r.json()),
        fetch("/api/preguntas").then((r) => r.json()),
        fetch("/api/prompts").then((r) => r.json()),
      ]);
      this.niveles = niveles;
      this.preguntas = preguntas.preguntas;
      this.prompts = prompts.vigentes;
      this.pregunta = this.preguntas[0]?.texto || "";
      this.reiniciar();
      this.cargarPrompt();
      setInterval(() => this.refrescarSalud(), 5000);
    },

    async refrescarSalud() {
      try {
        this.salud = await fetch("/api/salud").then((r) => r.json());
        this.gasto = await fetch("/api/gasto").then((r) => r.json());
        // La conmutación automática a replay tiene que ser IMPOSIBLE de ignorar.
        if (this.modoPrevio === "vivo" && this.salud.modo === "replay") {
          this.bannerReplay =
            this.salud.aviso_replay ||
            "Modo replay: lo que ves a continuación son trazas pregrabadas, no ejecución real.";
        }
        this.modoPrevio = this.salud.modo;
      } catch (e) {
        /* el tablero sigue usable aunque falle un sondeo */
      }
    },

    alternarTema() {
      this.temaOscuro = !this.temaOscuro;
      document.documentElement.dataset.tema = this.temaOscuro ? "oscuro" : "claro";
    },

    // --- Metadatos -------------------------------------------------------

    meta(id) {
      return (
        this.niveles.find((n) => n.id === id) || {
          estrellas: "",
          nombre: id,
          patron: "",
          tools: [],
          textos: {},
          diagrama: null,
        }
      );
    },

    nivelesVisibles() {
      return this.niveles.map((n) => n.id).filter((id) => this.seleccion.includes(id));
    },

    // Niveles que se ejecutan según la vista: uno en paso a paso, los marcados
    // en comparación.
    aEjecutar() {
      return this.vista === "paso" ? [this.nivelActual] : this.seleccion;
    },

    col(id) {
      if (!this.columnas[id]) this.columnas[id] = this.columnaVacia();
      return this.columnas[id];
    },

    columnaVacia() {
      return { pasos: [], respuesta: "", metricas: null, avisos: [], eventos: [], terminado: false };
    },

    reiniciar() {
      const cols = {};
      const nodos = {};
      for (const n of this.niveles) {
        cols[n.id] = this.columnaVacia();
        nodos[n.id] = {};
      }
      this.columnas = cols;
      this.estadoNodos = nodos;
      this.limpiarDiagrama();
    },

    // --- Navegación del modo paso a paso ---------------------------------

    irANivel(id) {
      this.nivelActual = id;
      this.vista = "paso";
      // La disposición está memorizada por nivel y la narración es del nivel que
      // se está mirando: las dos se descartan al cambiar.
      this._disp = null;
      this.narracion = [];
      this.paquetes = [];
      this.insignias = [];
    },

    indiceActual() {
      return this.niveles.findIndex((n) => n.id === this.nivelActual);
    },

    avanzar(delta) {
      const i = this.indiceActual() + delta;
      if (i >= 0 && i < this.niveles.length) this.irANivel(this.niveles[i].id);
    },

    // --- Encendido de nodos ----------------------------------------------

    // El id del nodo puede venir de un campo del propio evento: "{dominio}"
    // enciende el nodo del dominio elegido, "llm{n_llamada}" distingue la
    // primera llamada de la segunda. Así N2 y N5 no necesitan lógica propia.
    idNodo(plantilla, evento) {
      return this.plantilla(plantilla, this.camposDe(evento));
    },

    activarNodo(evento) {
      const d = this.meta(evento.nivel).diagrama;
      if (!d || !d.activacion) return;
      const plantilla = d.activacion[evento.tipo];
      if (!plantilla) return;
      const id = this.idNodo(plantilla, evento);
      if (!id) return;
      const estado = this.estadoNodos[evento.nivel] || (this.estadoNodos[evento.nivel] = {});
      // Lo que estaba en curso pasa a hecho: así el diagrama avanza solo.
      for (const k of Object.keys(estado)) if (estado[k] === "activo") estado[k] = "hecho";
      estado[id] = "activo";
    },

    cerrarNodos(nivel) {
      const estado = this.estadoNodos[nivel] || {};
      for (const k of Object.keys(estado)) if (estado[k] === "activo") estado[k] = "hecho";
    },

    // --- Ejecución -------------------------------------------------------

    usarChip(p) {
      this.pregunta = p.texto;
      this.ejecutar();
    },

    async ejecutar() {
      if (this.corriendo || !this.pregunta.trim()) return;
      const niveles = this.aEjecutar();
      if (!niveles.length) return;
      this.cerrarFuente();
      this.reiniciar();
      this.corriendo = true;
      this.enCurso = niveles;

      const r = await fetch("/api/ejecutar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta: this.pregunta, niveles }),
      });
      if (!r.ok) {
        this.corriendo = false;
        this.bannerReplay = `No pude arrancar la ejecución (HTTP ${r.status}).`;
        return;
      }
      this.runId = (await r.json()).run_id;

      this.fuente = new EventSource(`/api/stream/${this.runId}`);
      this.fuente.addEventListener("evento", (m) => this.recibir(JSON.parse(m.data)));
      this.fuente.addEventListener("cerrado", () => {
        this.corriendo = false;
        this.cerrarFuente();
        this.refrescarSalud();
      });
      this.fuente.onerror = () => {
        if (!this.corriendo) this.cerrarFuente();
      };
    },

    async detener() {
      if (this.runId) await fetch(`/api/cancelar/${this.runId}`, { method: "POST" });
      this.corriendo = false;
    },

    cerrarFuente() {
      if (this.fuente) {
        this.fuente.close();
        this.fuente = null;
      }
    },

    async marcarSinFuente() {
      if (!this.runId) return;
      const e = await fetch(`/api/marcar_sin_fuente/${this.runId}?nivel=n1`, {
        method: "POST",
      }).then((r) => r.json());
      if (!this.col("n1").avisos.includes(e.mensaje)) this.recibir(e);
    },

    // --- Traducción de eventos a pasos ----------------------------------

    recibir(e) {
      const c = this.col(e.nivel);
      if (!c) return;
      c.eventos.push(e);
      this.activarNodo(e);
      // El evento no solo se escribe en la traza: también hace viajar un paquete
      // por el diagrama. Es la misma información contada de dos maneras.
      this.despacharFlujo(e);

      switch (e.tipo) {
        case "inicio":
          c.pasos.push({
            marca: "○", clase: "encurso",
            texto: e.desde_cache ? "inicio (desde caché)" : "inicio",
            detalle: ` ${e.modelo}`,
          });
          break;
        case "llm_request":
          c.pasos.push({
            marca: "○", clase: "encurso",
            texto: `llamada ${e.n_llamada} al modelo`,
            detalle: e.tools_declaradas.length
              ? ` · ${e.tools_declaradas.length} herramientas declaradas`
              : " · sin herramientas",
            mensajes: e.mensajes,
          });
          break;
        case "llm_response": {
          const abierto = [...c.pasos].reverse().find((p) => p.clase === "encurso");
          if (abierto) {
            abierto.clase = "completado";
            abierto.marca = "●";
            abierto.detalle += ` · ${e.ms} ms · ${e.tokens_in}+${e.tokens_out} tok`;
          }
          break;
        }
        case "pensamiento":
          c.pasos.push({
            marca: "»", clase: "pensamiento",
            texto: e.texto || "(el modelo no razonó en voz alta)",
            detalle: "",
          });
          break;
        case "ruta":
          c.pasos.push({
            marca: "●", clase: "completado",
            texto: `ruta → ${e.dominio}`, detalle: ` · ${e.motivo}`,
          });
          break;
        case "tool_call":
          c.pasos.push({
            marca: "●", clase: "completado",
            texto: `${e.nombre}(…)`,
            detalle: "",
            argumentos: e.argumentos,
            crudo: e.crudo,
            docstring: this.docDe(e.nombre),
            idLlamada: e.id_llamada,
          });
          break;
        case "tool_result": {
          // Se engancha al paso del tool_call para que la llamada y su respuesta
          // se lean juntas: es la pareja que hay que entender.
          const llamada = [...c.pasos].reverse().find((p) => p.idLlamada === e.id_llamada);
          if (llamada) {
            llamada.resultado = e.resultado;
            llamada.filas = e.filas;
            llamada.msTool = e.ms;
            llamada.errorTool = e.error;
            llamada.resumen = this.resumirResultado(e.resultado);
            if (e.error) {
              llamada.clase = "error";
              llamada.marca = "✕";
            }
          } else {
            c.pasos.push({
              marca: e.error ? "✕" : "●",
              clase: e.error ? "error" : "completado",
              texto: `resultado de ${e.nombre}`,
              detalle: "",
              resultado: e.resultado,
              resumen: this.resumirResultado(e.resultado),
            });
          }
          break;
        }
        case "delegacion":
          c.pasos.push({
            marca: "⇒", clase: "delegacion",
            texto: `delega en ${e.agente}`, detalle: ` «${e.instruccion}»`,
          });
          break;
        case "sub_evento": {
          const d = e.evento;
          if (d.tipo === "llm_request") {
            c.pasos.push({
              marca: "·", clase: "anidado",
              texto: `${e.agente} · llamada ${d.n_llamada} al modelo`, detalle: "",
            });
          } else if (d.tipo === "tool_call") {
            c.pasos.push({
              marca: "·", clase: "anidado",
              texto: `${e.agente} · ${d.nombre}(…)`,
              detalle: "",
              argumentos: d.argumentos,
              crudo: d.crudo,
              docstring: this.docDe(d.nombre),
              idLlamada: d.id_llamada,
            });
          } else if (d.tipo === "tool_result") {
            const llamada = [...c.pasos].reverse().find((p) => p.idLlamada === d.id_llamada);
            if (llamada) {
              llamada.resultado = d.resultado;
              llamada.filas = d.filas;
              llamada.msTool = d.ms;
              llamada.resumen = this.resumirResultado(d.resultado);
            }
          } else if (d.tipo === "respuesta_final") {
            c.pasos.push({
              marca: "·", clase: "anidado",
              texto: `${e.agente} responde`, detalle: ` «${(d.texto || "").slice(0, 140)}»`,
            });
          }
          break;
        }
        case "respuesta_final":
          c.respuesta = e.texto;
          break;
        case "metricas":
          c.metricas = e;
          break;
        case "aviso":
          if (e.gravedad === "alerta") c.avisos.push(e.mensaje);
          else c.pasos.push({ marca: "ℹ", clase: "", texto: e.mensaje, detalle: "" });
          break;
        case "error":
          c.pasos.push({
            marca: e.recuperable ? "⚠" : "✕",
            clase: e.recuperable ? "aviso" : "error",
            texto: e.recuperable ? `reintento ${e.reintento}` : "error",
            detalle: ` ${e.mensaje}`,
          });
          break;
        case "fin":
          c.terminado = true;
          this.cerrarNodos(e.nivel);
          for (const p of c.pasos)
            if (p.clase === "encurso") {
              p.clase = "completado";
              p.marca = "●";
            }
          break;
      }
    },

    docDe(nombre) {
      for (const n of this.niveles) {
        const t = (n.tools || []).find((x) => x.nombre === nombre);
        if (t) return t.docstring;
      }
      return "";
    },

    // Una línea que diga qué trajo la herramienta, sin obligar a leer el JSON.
    // Es lo que permite entender el concepto sin perderse en la estructura.
    resumirResultado(r) {
      if (r === null || r === undefined) return "";
      if (typeof r !== "object") return String(r).slice(0, 160);
      if (r.mensaje) return r.mensaje.slice(0, 200);
      const partes = [];
      if (r.planta) partes.push(r.planta);
      if (Array.isArray(r.items) && r.items.length) {
        const i = r.items[0];
        partes.push(
          `${i.materia_prima}: ${i.cantidad_ton} t` +
            (i.bajo_minimo ? ` ⚠ bajo el mínimo de ${i.stock_minimo_ton} t` : "")
        );
      }
      if (r.total_ton !== undefined) partes.push(`total ${r.total_ton} t`);
      if (r.requerimiento_materia_prima?.toneladas_requeridas !== undefined)
        partes.push(
          `requiere ${r.requerimiento_materia_prima.toneladas_requeridas} t de ` +
            r.requerimiento_materia_prima.materia_prima
        );
      if (r.utilizacion_pct !== undefined) partes.push(`utilización ${r.utilizacion_pct}%`);
      if (r.estado) partes.push(`estado ${r.estado}`);
      if (r.posicion_en_cola) partes.push(`posición ${r.posicion_en_cola} en la cola`);
      if (r.eta_estimada) partes.push(`ETA ${r.eta_estimada}`);
      if (r.en_cola !== undefined) partes.push(`${r.en_cola} camiones en cola`);
      if (r.correctivos !== undefined) partes.push(`${r.correctivos} correctivos`);
      if (r.causa_mas_repetida) partes.push(`causa: ${r.causa_mas_repetida.causa}`);
      if (r.mtbf_dias) partes.push(`MTBF ${r.mtbf_dias} d`);
      if (r.tendencia) partes.push(`tendencia ${r.tendencia.direccion} (${r.tendencia.pendiente} ${r.tendencia.unidad})`);
      if (r.n_lecturas) partes.push(`${r.n_lecturas} lecturas`);
      if (r.truncado) partes.push("resultado truncado");
      return partes.join(" · ").slice(0, 240);
    },

    json(v) {
      try {
        return JSON.stringify(v, null, 2);
      } catch (e) {
        return String(v);
      }
    },

    // --- Métricas --------------------------------------------------------

    costoTexto(m) {
      if (!m) return "";
      if (!m.costo_configurado) return "costo no configurado";
      if (m.desde_cache) return "$0.00 (caché)";
      return `$${(m.costo_usd || 0).toFixed(4)}`;
    },

    porcentajeGasto() {
      const tope = this.salud.tope_usd || 0;
      return tope ? Math.min(100, ((this.gasto.gasto_usd || 0) / tope) * 100) : 0;
    },

    claseGasto() {
      const p = this.porcentajeGasto();
      return p > 90 ? "alto" : p > 70 ? "medio" : "";
    },

    hayMetricas() {
      return this.nivelesVisibles().some((id) => this.col(id).metricas);
    },

    get filasCierre() {
      const m = (id) => this.col(id).metricas;
      const base = () => {
        const n1 = m("n1");
        return n1 && n1.llamadas_llm ? n1 : null;
      };
      return [
        { etiqueta: "Nivel de agencia", valor: (id) => this.meta(id).estrellas },
        { etiqueta: "Llamadas al modelo", valor: (id) => (m(id) ? m(id).llamadas_llm : "—") },
        { etiqueta: "Herramientas usadas", valor: (id) => (m(id) ? m(id).llamadas_tools : "—") },
        {
          etiqueta: "Tokens",
          valor: (id) => (m(id) ? `${m(id).tokens_in}+${m(id).tokens_out}` : "—"),
        },
        {
          etiqueta: "Tiempo",
          valor: (id) => (m(id) ? `${(m(id).ms_total / 1000).toFixed(1)} s` : "—"),
        },
        {
          // En tokens y no en llamadas: los modelos piden varias herramientas en
          // paralelo, así que N3 y N4 pueden empatar en llamadas y diferir 5× en
          // tokens. Lo que crece es el contexto que se reenvía.
          etiqueta: "Costo relativo a N1 (tokens)",
          valor: (id) => {
            const b = base();
            const mi = m(id);
            if (!b || !mi) return "—";
            const unidad = b.tokens_in + b.tokens_out;
            return unidad ? `${((mi.tokens_in + mi.tokens_out) / unidad).toFixed(1)}×` : "—";
          },
        },
        {
          etiqueta: "Cuándo usarlo",
          destacada: true,
          valor: (id) => this.meta(id).textos?.cuando_usarlo || "—",
        },
      ];
    },

    // --- Vista de detalle ------------------------------------------------

    irADetalle() {
      this.vista = "detalle";
      this.cargarPrompt();
    },

    trazaDetalle() {
      return this.col(this.nivelDetalle).eventos || [];
    },

    cargarPrompt() {
      this.promptEditado = this.prompts[this.nivelDetalle] || "";
      this.promptGuardado = false;
    },

    async guardarPrompt() {
      await fetch(`/api/prompts/${this.nivelDetalle}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: this.promptEditado }),
      });
      this.prompts[this.nivelDetalle] = this.promptEditado;
      this.promptGuardado = true;
    },

    async restaurarPrompts() {
      const r = await fetch("/api/prompts/reset", { method: "POST" }).then((x) => x.json());
      this.prompts = r.vigentes;
      this.cargarPrompt();
    },

    // --- Utilidades ------------------------------------------------------

    resaltar(json) {
      const escapado = (json || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return escapado
        .replace(/"([^"]+)":/g, '<span class="clave">"$1"</span>:')
        .replace(/: "((?:[^"\\]|\\.)*)"/g, ': <span class="texto">"$1"</span>')
        .replace(/: (-?\d+\.?\d*)/g, ': <span class="numero">$1</span>');
    },

    copiar(texto) {
      navigator.clipboard?.writeText(texto);
    },
  };
}
