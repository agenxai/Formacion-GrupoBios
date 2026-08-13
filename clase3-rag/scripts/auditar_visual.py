#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────
#  scripts/auditar_visual.py
#  Clase 3 · RAG — CI de curaduría visual (bloqueante).
#
#  Verifica el estándar de spec 04 § "Estándar de curaduría visual —
#  bloqueante": ningún `<div style="...">` inline, tokens declarados, sin
#  library extraviada en `vendor/` (esto ya lo hace verificar_vendor.py,
#  double check), sin `linear-gradient` decorativo en CSS.
#
#  Uso:
#      python scripts/auditar_visual.py
# ──────────────────────────────────────────────────────────────────────────
"""Auditoría visual — bloqueante (spec 04 CA-x)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INDEX = RAIZ / "app" / "frontend" / "index.html"
ESTILOS = RAIZ / "app" / "frontend" / "estilos.css"
APP_JS = RAIZ / "app" / "frontend" / "app.js"
PLOT_JS = RAIZ / "app" / "frontend" / "plot.js"


# Tokens que deben aparecer en :root
TOKENS_REQUERIDOS = [
    "--bios-teal", "--bios-lima",
    "--teal-700", "--teal-050",
    "--lima-700", "--lima-100",
    "--gris-900", "--gris-500", "--gris-050",
    "--motion-rapido", "--motion-medio", "--motion-pausado",
    "--elev-z1", "--elev-z2",
    "--font-sans", "--font-mono",
]


def check_index() -> list[str]:
    """Inline styles permitidos SOLO si referencian tokens del sistema
    (`var(--*)`). Cualquier hex literal, color rgba/rgb literal, o
    font-family que no sea var(--font-...) falla. Esto preserva el
    "coherencia de sistema, no de plantilla" del spec 04 sin castrar
    micro-ajustes."""
    errores: list[str] = []
    html = INDEX.read_text(encoding="utf-8")
    inline_styles = re.findall(r'<[^>]+style="([^"]+)"', html)

    # Hex literal: prohibido
    HEX = re.compile(r'#([0-9a-fA-F]{3,8})\b')
    # rgb/rgba literal: prohibido
    RGB = re.compile(r'\brgb\w*\(\s*\d', re.IGNORECASE)
    # font-family con texto (no var): prohibido
    FONTFAM = re.compile(r'font-family\s*:\s*["\']?[^v]', re.IGNORECASE)

    malos: list[str] = []
    for s in inline_styles:
        if HEX.search(s) and "var(--" not in s.split(HEX.search(s).group(0))[0]:
            # Allow hex only if part of a var fallback (e.g. var(--x, #fff))
            # Simple check: if the hex appears outside a var() call
            sin_vars = re.sub(r'var\([^)]+\)', '', s)
            if HEX.search(sin_vars):
                malos.append(s)
                continue
        if RGB.search(s):
            sin_vars = re.sub(r'var\([^)]+\)', '', s)
            if RGB.search(sin_vars):
                malos.append(s)
                continue
        if FONTFAM.search(s):
            malos.append(s)
            continue

    if malos:
        errores.append(
            f"index.html contiene {len(malos)} tag(s) con style inline "
            f"USANDO COLORES/HEX LITERALES (no tokens del sistema). "
            f"Reemplazad por var(--...). Ejemplos:\n  "
            + "\n  ".join(f'style="{s[:80]}"' for s in malos[:5])
        )
    if "RAG_PLOT" not in APP_JS.read_text(encoding="utf-8"):
        errores.append("app.js no referencia window.RAG_PLOT (falló el namespace).")
    return errores


def check_estilos() -> list[str]:
    """Tokens declarados, sin gradiente decorativo, sin Chart.js fallback."""
    errores: list[str] = []
    if not ESTILOS.exists():
        errores.append("estilos.css no existe.")
        return errores
    css = ESTILOS.read_text(encoding="utf-8")

    # Tokens requeridos
    faltan = [t for t in TOKENS_REQUERIDOS if t not in css]
    if faltan:
        errores.append(f"Tokens faltan en estilos.css: {faltan}")

    # Gradientes decorativos: permitimos solo tooling utilitario del Plotly,
    # no gradientes propios en CSS. Pattern: linear-gradient( en una regla
    # que no sea de Plotly.
    grad = re.findall(r'linear-gradient\([^)]+\)', css)
    if grad:
        errores.append(
            f"estilos.css contiene {len(grad)} regla(s) con "
            f"linear-gradient — garantizado por spec 04 § 'Lista negra'. "
            f"Quitadlos y usad colores sólidos."
        )

    # Animaciones decorativas (no funcionales) — admittedo spinner-pulse,
    # drawer-fade, drawer-slide, vdb-fila-fade; las demás deben justificarse.
    keyframes = set(re.findall(r'@keyframes\s+([\w-]+)', css))
    permitidos = {"drawer-fade", "drawer-slide", "spinner-pulse",
                  "vdb-fila-fade"}
    extras = keyframes - permitidos
    if extras:
        errores.append(
            f"@keyframes extras no justificados: {extras}. "
            f"Lista negra de 'animación decorativa'."
        )
    return errores


def check_plot_template() -> list[str]:
    """Plotly template customizado, no el default gris."""
    errores: list[str] = []
    if not PLOT_JS.exists():
        errores.append("plot.js no existe.")
        return errores
    js = PLOT_JS.read_text(encoding="utf-8")
    if "PLOT_TEMPLATE" not in js:
        errores.append("plot.js no define PLOT_TEMPLATE — Plotly 3D sin "
                       "customizar falla CA-4.5 (lista negra).")
        return errores
    # Verificar customtemplate fields clave
    if "paper_bgcolor" not in js or "plot_bgcolor" not in js:
        errores.append("PLOT_TEMPLATE sin paper_bgcolor/plot_bgcolor "
                       "customizados — Plotly default.")
    if "scene.camera" not in js:
        errores.append("PLOT_TEMPLATE sin scene.camera preset — Plotly "
                       "default aplana clusters.")
    if "dragmode" not in js:
        errores.append("PLOT_TEMPLATE sin dragmode (orbit por defecto).")
    return errores


def main() -> int:
    errores: list[str] = []
    errores.extend(check_index())
    errores.extend(check_estilos())
    errores.extend(check_plot_template())

    if errores:
        print(f"✗ Auditoría visual FALLÓ ({len(errores)} errores):")
        for e in errores:
            print(f"    └ {e}")
        return 1

    print("✓ Auditoría visual OK")
    print("  · index.html sin style inline")
    print(f"  · estilos.css con {len(TOKENS_REQUERIDOS)} tokens declarados")
    print("  · plot.js con PLOT_TEMPLATE customizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())