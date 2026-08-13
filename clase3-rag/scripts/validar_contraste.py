#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────
#  scripts/validar_contraste.py
#  Clase 3 · RAG — Verifica WCAG 4.5:1 sobre pares texto/fondo declarados
#  en estilos.css.
#
#  Copiado de la clase 1 con overrides menores (sin alterar la lógica).
#  Ver spec 04 § "Identidad visual — herencia de principios" y
#  § "Candado brutal" del estándar de curaduría.
#
#  Uso:
#      python scripts/validar_contraste.py
# ──────────────────────────────────────────────────────────────────────────
"""Valida contraste WCAG 4.5:1 en tokens CSS de bios teal/lima/gris."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ESTILOS = Path(__file__).resolve().parent.parent / "app" / "frontend" / "estilos.css"


def hex_a_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def luminancia(rgb: tuple[int, int, int]) -> float:
    def L(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (c / 255 for c in rgb)
    return 0.2126 * L(r) + 0.7152 * L(g) + 0.0722 * L(b)


def contraste(fg: str, bg: str) -> float:
    l1 = luminancia(hex_a_rgb(fg))
    l2 = luminancia(hex_a_rgb(bg))
    mayor, menor = max(l1, l2), min(l1, l2)
    return (mayor + 0.05) / (menor + 0.05)


# Pares texto-sobre-fondo que deben pasar la verificación WCAG 4.5:1
# (mismo set que S1 + ajustes de S3). Si añadís un par nuevo, agregadlo
# aquí. Si lo dejás por debajo de 4.5 aunque sea visualmente legible pero no
# accesible, marcadlo con "tolerado" en el comentario — sin aprobación
# verbal del facilitador, no va.
PARES = [
    # Texto sobre fondo blanco
    ("--teal-700", "#ffffff", "Texto teal sobre blanco (cabecera, badges)"),
    ("--teal-900", "#ffffff", "Texto teal-900 sobre blanco (h1)"),
    ("--gris-700", "#ffffff", "Texto gris-700 sobre blanco (body)"),
    ("--gris-900", "#ffffff", "Texto gris-900 sobre blanco"),
    ("--lima-700", "#ffffff", "Texto lima-700 sobre blanco (cita-chip)"),
    # Texto sobre fondo teal claro
    ("--teal-700", "--teal-050", "Texto teal sobre teal-050 (badge)"),
    ("--teal-900", "--teal-050", "Texto teal-900 sobre teal-050"),
    # Texto sobre gris claro
    ("--gris-700", "--gris-100", "Texto gris-700 sobre gris-100"),
    ("--gris-500", "--gris-050", "Texto gris-500 sobre gris-050 (fondo app)"),
    # Chip lima sobre fondo claro
    ("--lima-700", "--lima-100", "Texto lima-700 sobre lima-100 (chip)"),
    # Códigos/badge en fondo teal claro
    ("--teal-700", "--teal-100", "Texto teal sobre teal-100"),
]


def resolver_token(token: str, vars_map: dict[str, str]) -> str:
    """Resuelve un --token a un hex, transitivamente."""
    v = vars_map.get(token, token)
    if v.startswith("--"):
        return resolver_token(v, vars_map)
    return v


def parsear_vars(css: str) -> dict[str, str]:
    """Captura `--var: #xxx` del bloque :root."""
    out: dict[str, str] = {}
    for m in re.finditer(r"--([\w\-]+):\s*(#[0-9a-fA-F]{3,8})", css):
        out[f"--{m.group(1)}"] = m.group(2)
    return out


def main() -> int:
    if not ESTILOS.exists():
        print(f"✗ {ESTILOS} no existe.")
        return 1

    css = ESTILOS.read_text(encoding="utf-8")
    vars_map = parsear_vars(css)

    if not vars_map.get("--bios-teal"):
        print("✗ No se encontró --bios-teal en estilos.css. ¿Se editó y se "
              "rompió el bloque :root?")
        return 1

    fallos = 0
    print(f"Validación WCAG 4.5:1 sobre {len(PARES)} pares texto/fondo\n")
    for fg, bg, desc in PARES:
        fg_hex = resolver_token(fg, vars_map)
        bg_hex = resolver_token(bg, vars_map)
        ratio = contraste(fg_hex, bg_hex)
        pasa = ratio >= 4.5
        marca = "✓" if pasa else "✗"
        print(f"  {marca} {ratio:.2f}  {desc}")
        print(f"      {fg_hex} sobre {bg_hex}")
        if not pasa:
            fallos += 1

    print(f"\n{len(PARES)-fallos}/{len(PARES)} pares pasan 4.5:1")
    if fallos:
        print(f"\n✗ {fallos} pares FALLAN. Revisá antes de la clase.")
        return 1
    print("\n✓ Todos los pares pasan WCAG 4.5:1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())