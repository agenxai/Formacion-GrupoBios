/* ==========================================================================
   Diagrama de arquitectura animado.

   Dibuja en SVG el diagrama que describe el backend (`/api/niveles`) y hace
   viajar por él un paquete por cada cosa que ocurre: la pregunta entra al
   modelo, el tool_call sale hacia la herramienta, el dato vuelve, la respuesta
   sale. El objetivo es que se entienda de primerazo, sin leer la traza.

   Nada de esto sabe qué nivel está dibujando. Los nodos, las aristas y el mapeo
   evento → paquete vienen del backend; acá solo hay geometría y animación. Un
   nivel nuevo trae su diagrama y se dibuja solo.
   ========================================================================== */

// Geometría. Un nodo de 168×58 con estas separaciones deja el diagrama de cinco
// columnas en ~1240 px: entra completo en un proyector de 1080p sin encogerse.
const NODO_W = 168;
const NODO_H = 58;
const GAP_X = 96;
const GAP_Y = 30;
const MARGEN = 26;
const MARGEN_BUCLE = 74; // espacio reservado abajo para la flecha de retorno

const DURACION_PAQUETE = 1100; // ms que tarda un paquete en recorrer una arista
const VIDA_INSIGNIA = 1600; // ms que permanece visible un destello sobre un nodo

function mezclaDiagrama() {
  return {
    paquetes: [],
    insignias: [],
    narracion: [],
    animando: false,
    _seq: 0,
    // Se graba el flujo para poder repetir la animación sin volver a llamar a la
    // API. En clase se explica dos y tres veces el mismo paso; hacerlo gratis es
    // la diferencia entre poder repetirlo y no.
    flujoGrabado: {},
    repitiendo: false,

    // --- Geometría -------------------------------------------------------

    // Posiciones de todos los nodos del nivel, calculadas desde las columnas.
    // Memorizado por nivel: se recalcula solo si cambia el diagrama.
    disposicion(nivelId) {
      const d = this.meta(nivelId).diagrama;
      if (!d || !d.columnas) return null;
      if (this._disp && this._disp.nivel === nivelId) return this._disp;

      const columnas = d.columnas;
      const alturas = columnas.map((c) => c.length * NODO_H + (c.length - 1) * GAP_Y);
      const altoUtil = Math.max(...alturas);
      const tieneBucle = (d.aristas || []).some((a) => a.curva);
      const alto = MARGEN * 2 + altoUtil + (tieneBucle ? MARGEN_BUCLE : 0);
      const ancho =
        MARGEN * 2 + columnas.length * NODO_W + (columnas.length - 1) * GAP_X;

      const nodos = {};
      columnas.forEach((columna, ic) => {
        const x = MARGEN + ic * (NODO_W + GAP_X);
        const y0 = MARGEN + (altoUtil - alturas[ic]) / 2;
        columna.forEach((nodo, ifi) => {
          nodos[nodo.id] = {
            ...nodo,
            x,
            y: y0 + ifi * (NODO_H + GAP_Y),
            w: NODO_W,
            h: NODO_H,
          };
        });
      });

      this._disp = { nivel: nivelId, ancho, alto, nodos, aristas: d.aristas || [] };
      return this._disp;
    },

    nodosDe(nivelId) {
      const disp = this.disposicion(nivelId);
      return disp ? Object.values(disp.nodos) : [];
    },

    aristasDe(nivelId) {
      const disp = this.disposicion(nivelId);
      if (!disp) return [];
      return disp.aristas
        .map((a) => ({ ...a, camino: this.camino(disp, a), medio: this.medio(disp, a) }))
        .filter((a) => a.camino);
    },

    // El trazado de una arista. Tres casos, y cada uno tiene su razón:
    //   · misma fila hacia adelante → línea recta, la lectura más directa
    //   · filas distintas → curva en S, para que se vea la bifurcación
    //   · `curva` → vuelta por debajo o por encima, el bucle de N4
    camino(disp, a) {
      const o = disp.nodos[a.desde];
      const t = disp.nodos[a.hasta];
      if (!o || !t) return null;

      if (a.curva) {
        const abajo = a.curva === "abajo";
        const yBorde = abajo ? o.y + o.h : o.y;
        const desvio = abajo ? 52 : -52;
        const x1 = o.x + o.w / 2;
        const x2 = t.x + t.w / 2;
        const yc = yBorde + desvio;
        return `M ${x1} ${yBorde} C ${x1} ${yc}, ${x2} ${yc}, ${x2} ${
          abajo ? t.y + t.h : t.y
        }`;
      }

      const x1 = o.x + o.w;
      const y1 = o.y + o.h / 2;
      const x2 = t.x;
      const y2 = t.y + t.h / 2;
      if (Math.abs(y1 - y2) < 1) return `M ${x1} ${y1} L ${x2} ${y2}`;
      const mx = (x1 + x2) / 2;
      return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
    },

    // Punto medio, para colgar la etiqueta estática de la arista.
    medio(disp, a) {
      const o = disp.nodos[a.desde];
      const t = disp.nodos[a.hasta];
      if (!o || !t) return { x: 0, y: 0 };
      if (a.curva) {
        const abajo = a.curva === "abajo";
        return {
          x: (o.x + o.w / 2 + t.x + t.w / 2) / 2,
          y: (abajo ? o.y + o.h + 44 : o.y - 44),
        };
      }
      return { x: (o.x + o.w + t.x) / 2, y: (o.y + t.y) / 2 + NODO_H / 2 - 9 };
    },

    // --- Construcción del SVG --------------------------------------------

    // El SVG se genera como CADENA y se inyecta con `x-html`, no con
    // `<template x-for>` dentro del <svg>.
    //
    // La razón es del parser, no de gusto: un `<template>` escrito dentro de
    // `<svg>` se crea en el espacio de nombres SVG y deja de ser un
    // HTMLTemplateElement, así que `x-for` no lo reconoce y no renderiza nada.
    // El síntoma es un lienzo con las flechas pero sin ningún nodo. Inyectar la
    // cadena en un <div> sí produce elementos SVG correctos.
    esc(t) {
      return String(t ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    },

    svgDiagrama(nivelId) {
      const disp = this.disposicion(nivelId);
      if (!disp) return "";
      const leyenda = this.esc(this.meta(nivelId).diagrama?.leyenda || "");
      const partes = [];

      partes.push(
        `<svg class="svg-diagrama" width="${disp.ancho}" height="${disp.alto}" ` +
          `viewBox="0 0 ${disp.ancho} ${disp.alto}" role="img" ` +
          `aria-label="Arquitectura de ${nivelId.toUpperCase()}: ${leyenda}">`,
        `<defs><marker id="punta-${nivelId}" viewBox="0 0 10 10" refX="9" refY="5" ` +
          `markerWidth="7" markerHeight="7" orient="auto-start-reverse">` +
          `<path d="M 0 0 L 10 5 L 0 10 z" class="punta-flecha"/></marker></defs>`
      );

      // Aristas primero, para que los nodos queden encima.
      for (const a of this.aristasDe(nivelId)) {
        const clase = this.claseArista(nivelId, a.id, a.tenue);
        partes.push(
          `<path id="arista-${nivelId}-${a.id}" d="${a.camino}" ` +
            `class="arista ${clase}" marker-end="url(#punta-${nivelId})"/>`
        );
        if (a.etiqueta) {
          partes.push(
            `<text x="${a.medio.x}" y="${a.medio.y}" class="etiqueta-arista" ` +
              `text-anchor="middle">${this.esc(a.etiqueta)}</text>`
          );
        }
      }

      for (const n of this.nodosDe(nivelId)) {
        const estado = this.claseNodo(nivelId, n.id);
        const rx = n.tipo === "entrada" || n.tipo === "salida" ? 26 : 8;
        partes.push(
          `<g class="nodo ${n.tipo} ${estado}">`,
          `<rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="${rx}"/>`,
          `<text x="${n.x + n.w / 2}" y="${n.y + (n.nota ? 24 : 34)}" ` +
            `class="nodo-etiqueta" text-anchor="middle">${this.esc(n.etiqueta)}</text>`,
          n.nota
            ? `<text x="${n.x + n.w / 2}" y="${n.y + 42}" class="nodo-nota" ` +
              `text-anchor="middle">${this.esc(n.nota)}</text>`
            : "",
          `</g>`
        );
      }

      for (const i of this.insignias.filter((x) => x.nivel === nivelId)) {
        partes.push(
          `<g class="insignia ${i.clase}">`,
          `<rect x="${i.x - 82}" y="${i.y - 17}" width="164" height="25" rx="12"/>`,
          `<text x="${i.x}" y="${i.y}" text-anchor="middle">${this.esc(i.etiqueta)}</text>`,
          `</g>`
        );
      }

      // Los paquetes se posicionan desde el bucle de animación, con
      // getPointAtLength sobre el trazado real de su arista.
      for (const p of this.paquetes.filter((x) => x.nivel === nivelId)) {
        partes.push(
          `<g id="paquete-${p.id}" class="paquete ${p.clase}" opacity="0">`,
          `<rect x="-72" y="-14" width="144" height="28" rx="14"/>`,
          `<text x="0" y="5" text-anchor="middle">${this.esc(p.etiqueta)}</text>`,
          `</g>`
        );
      }

      partes.push(`</svg>`);
      return partes.join("");
    },

    // --- Estado visual ---------------------------------------------------

    claseNodo(nivel, id) {
      return this.estadoNodos[nivel]?.[id] || "";
    },

    // Una arista se enciende cuando algún paquete la recorrió. Las que nunca se
    // recorren quedan tenues — en N2, los tres dominios que el modelo descartó.
    claseArista(nivel, aristaId, tenue) {
      const usada = this.estadoNodos[nivel]?.["arista:" + aristaId];
      return [usada ? "usada" : "", tenue ? "tenue" : ""].filter(Boolean).join(" ");
    },

    // --- Flujo: convertir un evento en algo que se mueve -----------------

    plantilla(txt, evento) {
      return String(txt || "").replace(/\{(\w+)\}/g, (_, campo) => evento[campo] ?? "");
    },

    // Clave del flujo. Los eventos anidados de N5 llevan el tipo interior, para
    // poder distinguir «el sub-agente usó una herramienta» de «el sub-agente
    // respondió».
    claveFlujo(e) {
      if (e.tipo === "sub_evento" && e.evento?.tipo) {
        return [`sub_evento.${e.evento.tipo}`, "sub_evento"];
      }
      return [e.tipo];
    },

    // Campos disponibles para las plantillas. En un `sub_evento` se mezclan los
    // del interior (nombre de la herramienta) con los del envoltorio (agente),
    // y el envoltorio manda.
    camposDe(e) {
      return e.tipo === "sub_evento" ? { ...(e.evento || {}), ...e } : e;
    },

    despacharFlujo(e, grabar = true) {
      const d = this.meta(e.nivel).diagrama;
      if (!d || !d.flujo) return;
      let regla = null;
      for (const clave of this.claveFlujo(e)) {
        if (d.flujo[clave]) {
          regla = d.flujo[clave];
          break;
        }
      }
      if (!regla) return;

      const campos = this.camposDe(e);
      const etiqueta = this.plantilla(regla.etiqueta, campos);

      if (grabar) {
        (this.flujoGrabado[e.nivel] ||= []).push({ evento: e, ts: e.ts_ms || 0 });
      }

      if (regla.arista) {
        const arista = this.plantilla(regla.arista, campos);
        this.lanzarPaquete(e.nivel, arista, etiqueta, regla.clase || "peticion");
      }
      if (regla.insignia) {
        const nodo = this.plantilla(regla.insignia, campos);
        this.lanzarInsignia(e.nivel, nodo, etiqueta, regla.clase || "peticion");
      }
      this.narrar(etiqueta, regla.clase || "peticion");
    },

    lanzarPaquete(nivel, arista, etiqueta, clase) {
      const disp = this.disposicion(nivel);
      if (!disp || !disp.aristas.some((a) => a.id === arista)) return;
      const estado = this.estadoNodos[nivel] || (this.estadoNodos[nivel] = {});
      estado["arista:" + arista] = "usada";
      this.paquetes.push({
        id: ++this._seq,
        nivel,
        arista,
        etiqueta,
        clase,
        nacido: performance.now(),
        dur: DURACION_PAQUETE,
        x: 0,
        y: 0,
      });
      this.arrancarAnimacion();
    },

    lanzarInsignia(nivel, nodo, etiqueta, clase) {
      const disp = this.disposicion(nivel);
      if (!disp || !disp.nodos[nodo]) return;
      this.insignias.push({
        id: ++this._seq,
        nivel,
        nodo,
        etiqueta,
        clase,
        x: disp.nodos[nodo].x + NODO_W / 2,
        y: disp.nodos[nodo].y - 12,
      });
      const propio = this._seq;
      setTimeout(() => {
        this.insignias = this.insignias.filter((i) => i.id !== propio);
      }, VIDA_INSIGNIA);
    },

    narrar(texto, clase) {
      if (!texto) return;
      this.narracion.push({ n: this.narracion.length + 1, texto, clase });
    },

    // --- Animación -------------------------------------------------------

    arrancarAnimacion() {
      if (this.animando) return;
      this.animando = true;
      requestAnimationFrame(() => this.tick());
    },

    tick() {
      const ahora = performance.now();
      let algunoVivo = false;

      for (const p of this.paquetes) {
        const t = Math.min(1, (ahora - p.nacido) / p.dur);
        if (t < 1) algunoVivo = true;
        const camino = document.getElementById(`arista-${p.nivel}-${p.arista}`);
        const el = document.getElementById(`paquete-${p.id}`);
        if (!camino || !el) continue;
        const punto = camino.getPointAtLength(t * camino.getTotalLength());
        el.setAttribute("transform", `translate(${punto.x},${punto.y})`);
        // Aparece y desaparece con un desvanecido corto: sin esto, el paquete
        // "salta" en los extremos de la arista.
        const opacidad = t < 0.1 ? t / 0.1 : t > 0.9 ? (1 - t) / 0.1 : 1;
        el.style.opacity = String(opacidad);
      }

      // Solo se reasigna el arreglo cuando de verdad murió alguno: reasignarlo
      // en cada fotograma dispararía el re-render de Alpine 60 veces por segundo.
      const vivos = this.paquetes.filter((p) => ahora - p.nacido < p.dur + 200);
      if (vivos.length !== this.paquetes.length) this.paquetes = vivos;

      if (algunoVivo || this.paquetes.length) {
        requestAnimationFrame(() => this.tick());
      } else {
        this.animando = false;
      }
    },

    limpiarDiagrama() {
      this.paquetes = [];
      this.insignias = [];
      this.narracion = [];
      this._disp = null;
    },

    // --- Repetir sin gastar ----------------------------------------------

    // Reproduce el flujo grabado respetando los tiempos originales. Es la misma
    // idea que el modo replay y el caché: la animación tarda lo que tardó de
    // verdad, así que la asimetría entre niveles se conserva.
    async repetirAnimacion() {
      const grabado = this.flujoGrabado[this.nivelActual];
      if (!grabado || !grabado.length || this.repitiendo) return;
      this.repitiendo = true;
      this.paquetes = [];
      this.insignias = [];
      this.narracion = [];
      const estado = (this.estadoNodos[this.nivelActual] = {});
      const t0 = performance.now();
      for (const paso of grabado) {
        const espera = paso.ts - (performance.now() - t0);
        if (espera > 0) await new Promise((r) => setTimeout(r, Math.min(espera, 4000)));
        this.activarNodo(paso.evento);
        this.despacharFlujo(paso.evento, false);
      }
      this.cerrarNodos(this.nivelActual);
      this.repitiendo = false;
    },

    hayGrabacion() {
      return (this.flujoGrabado[this.nivelActual] || []).length > 0;
    },
  };
}
