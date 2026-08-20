#!/usr/bin/env python3
"""Genera el Manual Operativo Grupo Bios (PDF) y el CSV de datos operativos.

Produce dos artefactos para las prácticas de la clase 4:
  1. manual_operativo_grupo_bios.pdf — manual con políticas, manuales y
     procedimientos simulados de Grupo Bios (mismo corpus que documentos.json
     de S3, ampliado y formateado como documento imprimible).
  2. datos_operativos_grupo_bios.csv — datos tabulares simulados (pedidos,
     inventario, fallas, turnos) para subir a Google Sheets y consumirlos
     vía MCP.

TODO es sintético. Ningún dato real de Grupo Bios se procesa.
"""

from __future__ import annotations

import csv
import json
import os
import random
from pathlib import Path

from fpdf import FPDF


HERE = Path(__file__).resolve().parent
IMAGES = HERE.parent / "images"
DOCUMENTOS_JSON = HERE.parents[1] / "clase3-rag" / "n8n" / "documentos.json"

# Fuentes TrueType Unicode (para soportar acentos, em-dash, etc.)
_FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
_FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
_FONT_ITALIC = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"
_FONT_BI = "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf"


# ─────────────────────────────────────────────────────────────────────────────
#  Colores Bios / Cypher (mismos de Clase1.html)
# ─────────────────────────────────────────────────────────────────────────────
BIOS_BG = (10, 48, 51)        # verde petróleo
BIOS_OR1 = (245, 166, 35)     # naranja claro
BIOS_OR2 = (245, 80, 30)      # naranja profundo
BIOS_INK = (255, 255, 255)
BIOS_MUTED = (185, 207, 204)
BIOS_CARD = (247, 250, 249)


class BiosPDF(FPDF):
    """PDF con la identidad visual del programa Cypher · Grupo Bios."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_font("Arial", "", _FONT_REGULAR)
        self.add_font("Arial", "B", _FONT_BOLD)
        self.add_font("Arial", "I", _FONT_ITALIC)
        self.add_font("Arial", "BI", _FONT_BI)
        self.set_fallback_fonts(["Arial"])

    def header(self):
        if self.page_no() == 1:
            return  # la portada dibuja su propio header
        self.set_fill_color(*BIOS_BG)
        self.rect(0, 0, self.w, 28, style="F")
        self.set_text_color(*BIOS_OR1)
        self.set_font("Arial", "B", 9)
        self.cell(0, 14, "GRUPO BIOS  ·  MANUAL OPERATIVO", ln=True, align="L")
        self.set_text_color(*BIOS_MUTED)
        self.set_font("Arial", "", 7)
        self.cell(0, 6, "Documento sintético — Formación en IA · Programa Cypher",
                  ln=True, align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-18)
        self.set_text_color(120, 130, 128)
        self.set_font("Arial", "I", 7)
        self.cell(0, 6, f"Página {self.page_no()}", align="C")
        self.ln(3)
        self.set_font("Arial", "", 6)
        self.set_text_color(150, 160, 158)
        self.cell(0, 4,
                  "Los datos de este manual son sintéticos y no representan "
                  "las operaciones reales de Grupo Bios.",
                  align="C")


def _portada(pdf: BiosPDF):
    pdf.add_page()
    pdf.set_fill_color(*BIOS_BG)
    pdf.rect(0, 0, pdf.w, pdf.h, style="F")
    # Banda naranja
    pdf.set_fill_color(*BIOS_OR2)
    pdf.rect(0, 55, pdf.w, 4, style="F")
    pdf.set_fill_color(*BIOS_OR1)
    pdf.rect(0, 59, pdf.w, 2, style="F")
    # Logos
    if (IMAGES / "grupo-bios.png").exists():
        pdf.image(str(IMAGES / "grupo-bios.png"), x=15, y=20, w=90)
    if (IMAGES / "cypher-logo.png").exists():
        pdf.image(str(IMAGES / "cypher-logo.png"), x=150, y=22, w=35)
    # Título
    pdf.set_text_color(*BIOS_INK)
    pdf.set_font("Arial", "B", 28)
    pdf.set_xy(15, 80)
    pdf.multi_cell(0, 12, "Manual Operativo\nGrupo Bios")
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(*BIOS_MUTED)
    pdf.set_xy(15, 115)
    pdf.multi_cell(0, 7,
                   "Políticas, manuales y procedimientos de las áreas de\n"
                   "Mantenimiento, Compras, Logística y Producción / TD")
    pdf.set_xy(15, 145)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5,
                   "Documento de referencia para las prácticas de la Sesión 4\n"
                   "del programa de Formación en IA — Harness, Skills y MCP.\n\n"
                   "Versión 2026.1 — Sintético. Ningún dato real de Grupo Bios\n"
                   "se procesa en este documento.")
    # Pie de portada
    pdf.set_xy(15, pdf.h - 40)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(*BIOS_MUTED)
    pdf.cell(0, 5, "Programa Cypher · Formación en Inteligencia Artificial",
             ln=True, align="L")
    pdf.set_text_color(*BIOS_OR1)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 5, "GRUPO BIOS", ln=True, align="L")


def _indice(pdf: BiosPDF):
    pdf.add_page()
    pdf.set_text_color(*BIOS_BG)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 12, "Contenido", ln=True)
    pdf.set_draw_color(*BIOS_OR1)
    pdf.set_line_width(1.2)
    pdf.line(15, pdf.get_y() + 2, 60, pdf.get_y() + 2)
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(40, 50, 48)
    items = [
        ("1.  Presentación del manual", 22),
        ("2.  Mantenimiento", 28),
        ("    2.1  Manual de mantenimiento preventivo de planta", 28),
        ("    2.2  Política de criticidad de equipos", 33),
        ("    2.3  Guía de interpretación de lecturas de sensor", 38),
        ("3.  Compras", 44),
        ("    3.1  Política de abastecimiento de materias primas", 44),
        ("    3.2  Manual de planeación de volúmenes a plantas", 49),
        ("    3.3  Reglas de inventario mínimo", 54),
        ("4.  Logística", 60),
        ("    4.1  Manual de despachos a clientes", 60),
        ("    4.2  Reglas de asignación de turnos de muelle", 65),
        ("    4.3  Política de notificación a clientes", 70),
        ("5.  Producción / Transformación Digital", 76),
        ("    5.1  Procedimiento de planeación de demanda", 76),
        ("    5.2  Glosario de indicadores operativos", 81),
        ("    5.3  Instructivo de conexión demanda ↔ producción", 86),
        ("6.  Anexo — Plantas de Grupo Bios", 92),
    ]
    for texto, _ in items:
        pdf.cell(0, 7, texto, ln=True)


def _seccion_titulo(pdf: BiosPDF, numero: str, titulo: str):
    pdf.ln(4)
    pdf.set_fill_color(*BIOS_BG)
    pdf.rect(15, pdf.get_y(), 180, 10, style="F")
    pdf.set_xy(18, pdf.get_y() + 1)
    pdf.set_text_color(*BIOS_OR1)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, f"{numero}  {titulo}", ln=True)
    pdf.ln(4)


def _subtitulo(pdf: BiosPDF, numero: str, titulo: str):
    pdf.ln(2)
    pdf.set_text_color(*BIOS_OR2)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, f"{numero}  {titulo}", ln=True)
    pdf.set_draw_color(*BIOS_OR1)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y() - 1, 195, pdf.get_y() - 1)
    pdf.ln(3)


def _parrafo(pdf: BiosPDF, texto: str):
    # Limpiar caracteres espurios que vienen del corpus original
    texto = texto.replace("胱", "")
    pdf.set_text_color(35, 45, 43)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5.2, texto)
    pdf.ln(2)


def _presentacion(pdf: BiosPDF):
    pdf.add_page()
    _seccion_titulo(pdf, "1", "Presentación del manual")
    _parrafo(pdf,
        "Este manual reúne las políticas, manuales y procedimientos que rigen "
        "la operación de las plantas de Grupo Bios en sus cuatro áreas "
        "principales: Mantenimiento, Compras, Logística y Producción / "
        "Transformación Digital. Es el documento de referencia para los "
        "analistas operativos, coordinadores de planta y líderes de área.")
    _parrafo(pdf,
        "El manual se estructura por dominios. Cada dominio agrupa sus "
        "propios documentos — manuales de operación, políticas internas, "
        "reglas técnicas y guías de interpretación. La numeración es "
        "estable: cada documento tiene un identificador (ej. "
        "mant_manual_preventivo) que se referencia desde los sistemas "
        "operativos y desde los agentes de IA que consultan este corpus.")
    _parrafo(pdf,
        "Grupo Bios opera cinco plantas en Colombia: Itagüí (Antioquia), "
        "Buga (Valle del Cauca), Mosquera (Cundinamarca), Barranquilla "
        "(Atlántico) y Palmira (Valle del Cauca). La planta de Itagüí "
        "concentra la mayor criticidad de la red por su capacidad de "
        "molienda y su operación continua.")
    _parrafo(pdf,
        "Este documento es sintético y fue construido para las prácticas "
        "del programa de Formación en IA de Grupo Bios. Los procedimientos, "
        "umbrales y reglas aquí descritos son verosímiles pero no "
        "corresponden a las políticas reales de Grupo Bios. En un entorno "
        "productivo, este manual sería mantenido por cada área y versionado "
        "en el sistema documental corporativo.")


def _dominio(pdf: BiosPDF, docs: list[dict], numero_dom: str, titulo_dom: str):
    pdf.add_page()
    _seccion_titulo(pdf, numero_dom, titulo_dom)
    for i, doc in enumerate(docs, start=1):
        numero = f"{numero_dom}.{i}"
        _subtitulo(pdf, numero, doc["titulo"])
        for p in doc["parrafos"]:
            _parrafo(pdf, p)


def _anexo_plantas(pdf: BiosPDF):
    pdf.add_page()
    _seccion_titulo(pdf, "6", "Anexo — Plantas de Grupo Bios")
    _parrafo(pdf,
        "Grupo Bios opera cinco plantas en Colombia. Cada planta tiene su "
        "propia capacidad de molienda, configuración de muelles y "
        "clasificación de criticidad. La siguiente tabla resume los datos "
        "de referencia.")
    pdf.ln(2)
    # Tabla de plantas
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(*BIOS_BG)
    pdf.set_text_color(*BIOS_OR1)
    pdf.cell(30, 8, "Código", border=1, fill=True, align="C")
    pdf.cell(45, 8, "Nombre", border=1, fill=True, align="L")
    pdf.cell(40, 8, "Municipio", border=1, fill=True, align="L")
    pdf.cell(35, 8, "Capacidad (t/d)", border=1, fill=True, align="C")
    pdf.cell(25, 8, "Estado", border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(35, 45, 43)
    plantas = [
        ("PL-ITG", "Planta Itagüí", "Itagüí", "420", "Activa"),
        ("PL-BUG", "Planta Buga", "Buga", "280", "Activa"),
        ("PL-MOS", "Planta Mosquera", "Mosquera", "350", "Activa"),
        ("PL-BQT", "Planta Barranquilla", "Barranquilla", "240", "Activa"),
        ("PL-PAL", "Planta Palmira", "Palmira", "200", "Inactiva"),
    ]
    for i, (cod, nom, mun, cap, est) in enumerate(plantas):
        if i % 2 == 0:
            pdf.set_fill_color(240, 244, 243)
        else:
            pdf.set_fill_color(255, 255, 255)
        pdf.cell(30, 7, cod, border="LR", fill=True, align="C")
        pdf.cell(45, 7, nom, border="LR", fill=True, align="L")
        pdf.cell(40, 7, mun, border="LR", fill=True, align="L")
        pdf.cell(35, 7, cap, border="LR", fill=True, align="C")
        pdf.cell(25, 7, est, border="LR", fill=True, align="C")
        pdf.ln()
    pdf.cell(175, 0, "", border="T", ln=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CSV — datos operativos simulados para Google Sheets
# ─────────────────────────────────────────────────────────────────────────────

def _generar_csv(out_path: Path):
    """Genera un CSV con pedidos simulados para subir a Google Sheets.

    El CSV modela un seguimiento de pedidos con campos relevantes para
    Logística, Compras y Producción — los dominios que los Champions van
    a consultar desde el harness + MCP de Google Sheets.
    """
    random.seed(42)
    plantas = [
        ("PL-ITG", "Itagüí"), ("PL-BUG", "Buga"),
        ("PL-MOS", "Mosquera"), ("PL-BQT", "Barranquilla"),
        ("PL-PAL", "Palmira"),
    ]
    clientes = [
        "Almacenes Éxito", "Carulla", "D1", "Ara", "Olímpica",
        "Homecenter", "Jumbo", "Makro", "Farmatodo", "Pombo",
    ]
    productos = ["Concentro Bovino 18%", "Concentro Porcino 16%",
                 "Concentro Avícola 20%", "Concentro Equino 14%",
                 "Premezcla Mineral", "Concentro Piscícola 28%"]
    estados = ["registrado", "programado", "en_produccion", "listo_despacho",
               "en_muelle", "cargado", "en_transito", "entregado"]
    # Pesos: más pedidos en estados avanzados
    pesos = [3, 5, 7, 8, 10, 6, 8, 12]

    filas = []
    for i in range(60):
        numero = f"PD-24-{8700 + i:05d}"
        planta_cod, planta_nom = random.choice(plantas)
        cliente = random.choice(clientes)
        producto = random.choice(productos)
        toneladas = round(random.uniform(15, 120), 1)
        dias_pedido = random.randint(0, 45)
        dias_promesa = dias_pedido + random.randint(2, 14)
        estado = random.choices(estados, weights=pesos, k=1)[0]
        # Turno de muelle si aplica
        if estado in ("en_muelle", "cargado"):
            turno = random.randint(1, 12)
        elif estado == "en_transito":
            turno = random.randint(1, 12)
        else:
            turno = ""
        # Prioridad
        prioridad = random.choice(["VIP", "Perecedero", "Estándar"])
        # SLA
        sla_promesa_horas = (dias_promesa - dias_pedido) * 24
        if estado == "entregado":
            sla_real_horas = sla_promesa_horas + random.randint(-12, 24)
        elif estado in ("en_muelle", "cargado", "en_transito"):
            sla_real_horas = sla_promesa_horas - random.randint(-6, 18)
        else:
            sla_real_horas = ""
        # Notas
        if estado == "en_muelle" and turno and turno > 5:
            notas = "Retraso en turno de muelle — notificar al cliente"
        elif estado == "novedad":
            notas = "Novedad: revisar disponibilidad de materia prima"
        elif prioridad == "Perecedero" and estado in ("en_muelle", "cargado"):
            notas = "Producto perecedero — prioridad de despacho"
        else:
            notas = ""

        filas.append({
            "pedido": numero,
            "cliente": cliente,
            "planta": planta_nom,
            "planta_id": planta_cod,
            "producto": producto,
            "toneladas": toneladas,
            "estado": estado,
            "turno_muelle": turno,
            "prioridad": prioridad,
            "dias_desde_pedido": dias_pedido,
            "dias_promesa": dias_promesa,
            "sla_promesa_horas": sla_promesa_horas,
            "sla_real_horas": sla_real_horas,
            "notas": notas,
        })

    campos = ["pedido", "cliente", "planta", "planta_id", "producto",
              "toneladas", "estado", "turno_muelle", "prioridad",
              "dias_desde_pedido", "dias_promesa", "sla_promesa_horas",
              "sla_real_horas", "notas"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    return len(filas)


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Cargar documentos.json de S3 (mismo corpus)
    with open(DOCUMENTOS_JSON, encoding="utf-8") as f:
        documentos = json.load(f)

    # Agrupar por dominio
    dominios = {}
    for d in documentos:
        dominios.setdefault(d["dominio"], []).append(d)

    orden_dominios = [
        ("mant", "2", "Mantenimiento"),
        ("comp", "3", "Compras"),
        ("logi", "4", "Logística"),
        ("prod", "5", "Producción / Transformación Digital"),
    ]

    # ── PDF ──
    pdf = BiosPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(True, margin=22)
    pdf.set_margins(15, 32, 15)

    _portada(pdf)
    _indice(pdf)
    _presentacion(pdf)
    for key, num, label in orden_dominios:
        _dominio(pdf, dominios[key], num, label)
    _anexo_plantas(pdf)

    pdf_path = HERE.parent / "manual_operativo_grupo_bios.pdf"
    pdf.output(str(pdf_path))
    print(f"✓ PDF generado: {pdf_path}  ({pdf.page_no()} páginas)")

    # ── CSV ──
    csv_path = HERE.parent / "datos_operativos_grupo_bios.csv"
    n = _generar_csv(csv_path)
    print(f"✓ CSV generado: {csv_path}  ({n} filas)")


if __name__ == "__main__":
    main()
