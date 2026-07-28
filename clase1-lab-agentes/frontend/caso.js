/* ==========================================================================
   Vista «El caso» — el contexto previo a los niveles. Spec 11.

   Responde, antes de que aparezca el primer agente: ¿de qué empresa es esto?,
   ¿qué información hay y dónde vive?, ¿qué puede consultar el agente?, ¿qué hay
   que responder? Cuatro bloques: escenario, datos, herramientas, preguntas.

   Todo el contenido viene del backend (`/api/caso`): conteos, columnas y llaves
   foráneas se leen de la base en vivo; los ejemplos de «Probar» son curados y
   viven en el backend. Acá solo hay geometría e interacción — la misma división
   que el diagrama de niveles (spec 07).

   El SVG se construye como cadena y se inyecta con `x-html`, no con
   `<template x-for>` dentro de `<svg>`: un template escrito dentro de un svg se
   crea en el espacio de nombres SVG, deja de ser un HTMLTemplateElement y Alpine
   no lo renderiza (la misma trampa documentada en la spec 07). El clic en los
   nodos se resuelve por delegación con `data-tabla`.
   ========================================================================== */

// Geometría del mapa. Misma familia de medidas que diagrama.js para que el mapa
// y los diagramas de nivel se sientan el mismo instrumento.
const CASO_NODO_W = 230;
const CASO_NODO_H = 96;
const CASO_CENTRO_W = 200;
const CASO_GAP_X = 110;
const CASO_GAP_Y = 14;
const CASO_LABEL_H = 36;
const CASO_PAD = 14;
const CASO_CLUSTER_GAP = 22;
const CASO_MARGEN = 20;

// Orden de las tablas dentro de cada grupo. La tabla referenciada por las demás
// va EN MEDIO (materias_primas entre formulas e inventario_planta; equipos entre
// ordenes y lecturas): así ninguna flecha foránea interna cruza por encima de
// otra tabla.
const CASO_ORDEN_TABLAS = {
  compras: ["formulas", "materias_primas", "inventario_planta"],
  demanda: ["demanda_historica", "produccion_diaria"],
  transversal: ["plantas"],
  mantenimiento: ["ordenes_mantenimiento", "equipos", "lecturas_sensor"],
  logistica: ["pedidos", "despachos"],
};
// Las columnas del mapa: dos grupos a la izquierda del centro, dos a la derecha.
const CASO_COLUMNA_IZQ = ["compras", "demanda"];
const CASO_COLUMNA_DER = ["mantenimiento", "logistica"];

function mezclaCaso() {
  return {
    caso: null,
    casoError: null,
    tablaSel: null,
    probando: {},

    async cargarCaso() {
      try {
        const r = await fetch("/api/caso");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        this.caso = await r.json();
      } catch (e) {
        this.casoError = `No pude cargar el caso (${e.message}).`;
      }
    },

    dominio(id) {
      return (this.caso?.dominios || []).find((d) => d.id === id) || {
        nombre: id, marca: "·", que_responde: "",
      };
    },

    tabla(id) {
      return (this.caso?.tablas || []).find((t) => t.id === id) || null;
    },

    tablasDe(dominioId) {
      const orden = CASO_ORDEN_TABLAS[dominioId] || [];
      const conocidas = orden.map((id) => this.tabla(id)).filter(Boolean);
      // Cualquier tabla que no esté en el orden declarado aparece al final: el
      // mapa nunca esconde una tabla por un olvido de configuración.
      const restantes = (this.caso?.tablas || []).filter(
        (t) => t.dominio === dominioId && !orden.includes(t.id)
      );
      return [...conocidas, ...restantes];
    },

    herramientasDe(dominioId) {
      return (this.caso?.herramientas || []).filter((h) => h.dominio === dominioId);
    },

    dominiosConHerramientas() {
      return ["compras", "demanda", "mantenimiento", "logistica"].filter(
        (d) => this.herramientasDe(d).length
      );
    },

    // --- Selección de tabla (mapa + chips) --------------------------------

    seleccionarTabla(id) {
      this.tablaSel = this.tablaSel === id ? null : id;
    },

    // Un solo @click en el contenedor: los nodos del SVG se inyectan como
    // cadena y no pueden llevar directivas de Alpine.
    clicMapa(evento) {
      const nodo = evento.target.closest("[data-tabla]");
      if (nodo) this.seleccionarTabla(nodo.getAttribute("data-tabla"));
    },

    // --- El botón «Probar» --------------------------------------------------

    _llave(nombre, i) {
      return `${nombre}:${i}`;
    },

    prueba(nombre, i) {
      return this.probando[this._llave(nombre, i)] || null;
    },

    async probar(nombre, i) {
      const llave = this._llave(nombre, i);
      if (this.probando[llave]?.cargando) return;
      this.probando = { ...this.probando, [llave]: { cargando: true } };
      try {
        const r = await fetch("/api/tools/probar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ herramienta: nombre, ejemplo: i }),
        });
        const datos = await r.json();
        if (!r.ok) throw new Error(datos.detail || `HTTP ${r.status}`);
        this.probando = {
          ...this.probando,
          [llave]: {
            cargando: false,
            resultado: datos.resultado,
            filas: datos.filas,
            ms: datos.ms,
          },
        };
      } catch (e) {
        this.probando = {
          ...this.probando,
          [llave]: { cargando: false, error: e.message },
        };
      }
    },

    argsTexto(argumentos) {
      return Object.entries(argumentos || {})
        .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
        .join(", ");
    },

    // --- El mapa SVG ---------------------------------------------------------

    disposicionMapa() {
      const clusterAlto = (n) =>
        CASO_LABEL_H + CASO_PAD + n * CASO_NODO_H + (n - 1) * CASO_GAP_Y + CASO_PAD;

      const altoIzq =
        CASO_COLUMNA_IZQ.reduce(
          (acc, d) => acc + clusterAlto(this.tablasDe(d).length),
          0
        ) + CASO_CLUSTER_GAP * (CASO_COLUMNA_IZQ.length - 1);
      const altoDer =
        CASO_COLUMNA_DER.reduce(
          (acc, d) => acc + clusterAlto(this.tablasDe(d).length),
          0
        ) + CASO_CLUSTER_GAP * (CASO_COLUMNA_DER.length - 1);
      const altoUtil = Math.max(altoIzq, altoDer, clusterAlto(1));

      const colIzqX = CASO_MARGEN;
      const centroX = colIzqX + CASO_NODO_W + CASO_PAD * 2 + CASO_GAP_X;
      const colDerX = centroX + CASO_CENTRO_W + CASO_PAD * 2 + CASO_GAP_X;
      const ancho = colDerX + CASO_NODO_W + CASO_PAD * 2 + CASO_MARGEN;
      const alto = CASO_MARGEN * 2 + altoUtil;

      const nodos = {};
      const clusters = [];

      const ponerCluster = (dominioId, x, w, y0) => {
        const tablas = this.tablasDe(dominioId);
        const h = clusterAlto(tablas.length);
        clusters.push({ dominio: dominioId, x, y: y0, w, h });
        tablas.forEach((t, i) => {
          nodos[t.id] = {
            tabla: t,
            x: x + CASO_PAD,
            y: y0 + CASO_LABEL_H + CASO_PAD + i * (CASO_NODO_H + CASO_GAP_Y),
            w,
            h: CASO_NODO_H,
          };
        });
        return h;
      };

      let y = CASO_MARGEN;
      for (const d of CASO_COLUMNA_IZQ) {
        y += ponerCluster(d, colIzqX, CASO_NODO_W, y) + CASO_CLUSTER_GAP;
      }
      y = CASO_MARGEN;
      for (const d of CASO_COLUMNA_DER) {
        y += ponerCluster(d, colDerX, CASO_NODO_W, y) + CASO_CLUSTER_GAP;
      }
      // El centro queda centrado en vertical contra la columna más alta.
      const altoCentro = clusterAlto(1);
      ponerCluster(
        "transversal", centroX, CASO_CENTRO_W,
        CASO_MARGEN + (altoUtil - altoCentro) / 2
      );

      // Las aristas son las llaves foráneas reales que mandó el backend.
      const aristas = [];
      const clusterDe = {};
      for (const c of clusters)
        for (const t of this.tablasDe(c.dominio)) clusterDe[t.id] = c.dominio;
      for (const t of this.caso?.tablas || []) {
        for (const ref of t.referencias || []) {
          if (nodos[t.id] && nodos[ref.hacia]) {
            aristas.push({
              desde: t.id,
              hasta: ref.hacia,
              interna: clusterDe[t.id] === clusterDe[ref.hacia],
            });
          }
        }
      }
      return { ancho, alto, nodos, aristas, clusters };
    },

    _borde(nodo, lado) {
      const cx = nodo.x + nodo.w / 2;
      const cy = nodo.y + nodo.h / 2;
      if (lado === "izq") return { x: nodo.x, y: cy };
      if (lado === "der") return { x: nodo.x + nodo.w, y: cy };
      if (lado === "arriba") return { x: cx, y: nodo.y };
      return { x: cx, y: nodo.y + nodo.h };
    },

    _trazo(a, b) {
      // Curva suave con controles horizontales: legible incluso cuando cruza
      // todo el mapa hacia el centro.
      const dx = Math.max(48, Math.abs(b.x - a.x) / 2);
      const sx = b.x >= a.x ? 1 : -1;
      return `M ${a.x} ${a.y} C ${a.x + sx * dx} ${a.y}, ${b.x - sx * dx} ${b.y}, ${b.x} ${b.y}`;
    },

    _lineasAporta(texto) {
      // Dos líneas de ~30 caracteres dentro del nodo; el texto completo queda en
      // el tooltip y en el panel lateral.
      const palabras = (texto || "").split(" ");
      const lineas = [""];
      for (const p of palabras) {
        const ultima = lineas[lineas.length - 1];
        if ((ultima + " " + p).trim().length <= 30) {
          lineas[lineas.length - 1] = (ultima + " " + p).trim();
        } else if (lineas.length < 2) {
          lineas.push(p);
        } else {
          lineas[1] = lineas[1].replace(/[.,;]?$/, "") + "…";
          break;
        }
      }
      return lineas;
    },

    svgMapa() {
      if (!this.caso) return "";
      const d = this.disposicionMapa();
      const partes = [];
      partes.push(
        `<svg viewBox="0 0 ${d.ancho} ${d.alto}" width="${d.ancho}" height="${d.alto}" ` +
          `class="mapa-base" role="img" aria-label="Mapa de la base de datos">`
      );
      partes.push(
        `<defs><marker id="flecha-caso" viewBox="0 0 10 10" refX="9" refY="5" ` +
          `markerWidth="7" markerHeight="7" orient="auto-start-reverse">` +
          `<path d="M 0 1 L 9 5 L 0 9 z" class="arista-punta"/></marker></defs>`
      );

      // Bandas de dominio (fondo) — primero, para que queden bajo las aristas.
      // La etiqueta va en dos líneas: en una sola, «⬢ Mantenimiento · qué equipo
      // falla y por qué» desborda la banda y el viewBox la recorta.
      for (const c of d.clusters) {
        const dom = this.dominio(c.dominio);
        partes.push(
          `<rect x="${c.x}" y="${c.y}" width="${c.w + CASO_PAD * 2}" height="${c.h}" ` +
            `rx="10" class="banda-dominio"/>` +
            `<text x="${c.x + CASO_PAD}" y="${c.y + 18}" class="banda-etiqueta">` +
            `${dom.marca} ${this._esc(dom.nombre)}</text>` +
            `<text x="${c.x + CASO_PAD}" y="${c.y + 33}" class="banda-sub-linea">` +
            `${this._esc(dom.que_responde)}</text>`
        );
      }

      // Aristas foráneas.
      for (const a of d.aristas) {
        const n1 = d.nodos[a.desde];
        const n2 = d.nodos[a.hasta];
        let p1, p2, trazo;
        if (a.interna) {
          // El hijo puede estar arriba o abajo del padre (el orden de las tablas
          // evita que la flecha cruce otra tabla, no que tenga una dirección
          // fija). La curva se proporciona al hueco: con 14px de separación un
          // control fijo de 18px dibujaría un lazo feo.
          const hijoAbajo = n1.y > n2.y;
          p1 = this._borde(n1, hijoAbajo ? "arriba" : "abajo");
          p2 = this._borde(n2, hijoAbajo ? "abajo" : "arriba");
          const salto = Math.min(18, Math.abs(p1.y - p2.y) / 2);
          const s = hijoAbajo ? -1 : 1;
          trazo = `M ${p1.x} ${p1.y} C ${p1.x} ${p1.y + s * salto}, ${p2.x} ${p2.y - s * salto}, ${p2.x} ${p2.y}`;
        } else {
          const haciaDerecha = n2.x > n1.x;
          p1 = this._borde(n1, haciaDerecha ? "der" : "izq");
          p2 = this._borde(n2, haciaDerecha ? "izq" : "der");
          trazo = this._trazo(p1, p2);
        }
        partes.push(`<path d="${trazo}" class="arista" marker-end="url(#flecha-caso)"/>`);
      }

      // Nodos de tabla.
      for (const [id, n] of Object.entries(d.nodos)) {
        const sel = this.tablaSel === id ? " sel" : "";
        const lineas = this._lineasAporta(n.tabla.que_aporta);
        const conteo = String(n.tabla.conteo).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        partes.push(
          `<g class="nodo-tabla${sel}" data-tabla="${id}">` +
            `<title>${this._esc(n.tabla.que_aporta)}</title>` +
            `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="8"/>` +
            `<text x="${n.x + 12}" y="${n.y + 24}" class="nt-nombre">${id}</text>` +
            `<text x="${n.x + 12}" y="${n.y + 44}" class="nt-conteo">${conteo} filas</text>` +
            lineas
              .map(
                (l, i) =>
                  `<text x="${n.x + 12}" y="${n.y + 66 + i * 16}" class="nt-aporta">${this._esc(l)}</text>`
              )
              .join("") +
            `</g>`
        );
      }
      partes.push(`</svg>`);
      return partes.join("");
    },

    _esc(s) {
      return String(s ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    },

    // --- La transición a los niveles -----------------------------------------

    irAN1() {
      // La pregunta insignia ya cargada, como promete el botón.
      if (this.caso?.preguntas?.length) this.pregunta = this.caso.preguntas[0].texto;
      this.irANivel("n1");
    },
  };
}
