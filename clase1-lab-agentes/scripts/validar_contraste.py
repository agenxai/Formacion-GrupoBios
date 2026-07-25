#!/usr/bin/env python3
"""Valida los contrastes WCAG de la paleta. Spec 06.

Los ratios que aparecen escritos en la spec son cálculos de referencia; ESTE
SCRIPT es la autoridad. No se afirma accesibilidad sin medirla.

Comprueba tres cosas:
  1. Los hex de marca son exactos (#00657F y #AACF00 no se alteran).
  2. Cada par (texto, fondo) que el diseño usa llega a 4.5:1 — o a 3:1 si es
     texto grande (≥24 px o ≥19 px en negrita).
  3. El lima NO se usa como color de texto sobre fondo claro.

Uso:
    python scripts/validar_contraste.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS = RAIZ / "frontend" / "estilos.css"

MARCA_EXACTA = {"--bios-teal": "#00657f", "--bios-lima": "#aacf00"}

# Pares que el diseño usa de verdad, con el tamaño de texto al que se usan.
# (token_texto, token_fondo, etiqueta, es_texto_grande)
PARES_CLARO = [
    ("--gris-900", "#ffffff", "cuerpo sobre fondo", False),
    ("--gris-900", "--gris-050", "cuerpo sobre fondo hundido", False),
    ("--gris-900", "--teal-050", "cuerpo sobre cabeza de columna", False),
    ("--gris-900", "--lima-400", "texto sobre insignia lima", False),
    ("--gris-900", "--lima-100", "fila destacada de la tabla", False),
    ("--gris-700", "#ffffff", "texto suave sobre fondo", False),
    ("--gris-700", "--gris-050", "pie de métricas", False),
    ("--gris-700", "--teal-050", "texto suave sobre teal-050", False),
    ("--gris-500", "#ffffff", "texto tenue sobre fondo", False),
    ("--gris-500", "--gris-050", "texto tenue sobre hundido", False),
    ("--teal-700", "#ffffff", "acento y enlaces", False),
    ("--teal-700", "--teal-050", "título de panel sobre teal-050", False),
    ("--teal-700", "--gris-050", "acento sobre hundido", False),
    ("--lima-700", "--gris-050", "números del JSON y marca de completado", False),
    ("--lima-700", "#ffffff", "marca de completado sobre blanco", False),
    ("--alerta", "#ffffff", "aviso de alucinación", False),
    ("--error", "#ffffff", "error de tool", False),
    ("--exito", "#ffffff", "estado correcto", False),
    ("#ffffff", "--teal-700", "texto del botón primario", False),
    ("#ffffff", "--alerta", "banner de replay", False),
]

PARES_OSCURO = [
    ("#eaf2f4", "#0b1418", "cuerpo sobre fondo oscuro", False),
    ("#eaf2f4", "#14232a", "cuerpo sobre panel oscuro", False),
    ("#c3d3d8", "#0b1418", "texto suave oscuro", False),
    ("#c3d3d8", "#101d22", "texto suave sobre hundido oscuro", False),
    ("#93a8ae", "#0b1418", "texto tenue oscuro", False),
    ("--teal-300", "#0b1418", "acento en oscuro", False),
    ("--teal-300", "#14232a", "acento sobre panel oscuro", False),
    ("--teal-300", "#10242b", "acento sobre teal-050 oscuro", False),
    ("--gris-900", "--lima-400", "insignia lima en oscuro", False),
    ("#c8e05a", "#101d22", "números del JSON en oscuro", False),
    ("#f28b82", "#0b1418", "error en oscuro", False),
    ("#e5a34a", "#0b1418", "alerta en oscuro", False),
    ("#4bbd8b", "#0b1418", "éxito en oscuro", False),
]

# Pares que DEBEN fallar: si alguno pasara, la regla dejó de tener sentido.
PROHIBIDOS = [
    ("--lima-400", "#ffffff", "lima como texto sobre blanco"),
    ("--bios-lima", "--gris-050", "lima como texto sobre gris claro"),
]


def leer_tokens(css: str) -> dict[str, str]:
    """Extrae las custom properties del primer bloque :root."""
    bloque = re.search(r":root\s*\{(.*?)\}", css, re.DOTALL)
    if not bloque:
        raise SystemExit("✕ No encontré el bloque :root en estilos.css")
    tokens: dict[str, str] = {}
    for nombre, valor in re.findall(
        r"(--[\w-]+)\s*:\s*([^;]+);", bloque.group(1)
    ):
        tokens[nombre] = valor.strip().lower()
    # Resuelve las referencias var(--x) una vez (la paleta no anida más).
    for clave, valor in list(tokens.items()):
        ref = re.match(r"var\((--[\w-]+)\)", valor)
        if ref:
            tokens[clave] = tokens.get(ref.group(1), valor)
    return tokens


def a_rgb(valor: str, tokens: dict[str, str]) -> tuple[int, int, int]:
    if valor.startswith("--"):
        valor = tokens.get(valor, "")
    valor = valor.strip().lstrip("#")
    if len(valor) == 3:
        valor = "".join(c * 2 for c in valor)
    if len(valor) != 6:
        raise ValueError(f"color no reconocido: {valor!r}")
    return tuple(int(valor[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminancia(rgb: tuple[int, int, int]) -> float:
    def canal(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str, tokens: dict[str, str]) -> float:
    la, lb = luminancia(a_rgb(a, tokens)), luminancia(a_rgb(b, tokens))
    claro, oscuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (oscuro + 0.05)


def main() -> int:
    if not CSS.exists():
        print(f"✕ No existe {CSS}")
        return 2
    css = CSS.read_text(encoding="utf-8")
    tokens = leer_tokens(css)
    fallos: list[str] = []

    # 1 · Hex de marca exactos
    print("Colores de marca")
    for token, esperado in MARCA_EXACTA.items():
        real = tokens.get(token, "(ausente)")
        ok = real == esperado
        print(f"  {'✓' if ok else '✕'} {token} = {real}  (debe ser {esperado})")
        if not ok:
            fallos.append(
                f"{token} vale {real} y debe valer exactamente {esperado}: es el "
                "color del logo del cliente, no se ajusta por gusto."
            )

    # 2 · Pares en uso
    for etiqueta_modo, pares in (("claro", PARES_CLARO), ("oscuro", PARES_OSCURO)):
        print(f"\nPares (texto, fondo) — modo {etiqueta_modo}")
        for texto, fondo, nombre, grande in pares:
            minimo = 3.0 if grande else 4.5
            try:
                r = ratio(texto, fondo, tokens)
            except ValueError as exc:
                fallos.append(f"{nombre}: {exc}")
                continue
            ok = r >= minimo
            print(
                f"  {'✓' if ok else '✕'} {r:5.2f}:1  (≥{minimo})  {nombre}"
                f"   [{texto} sobre {fondo}]"
            )
            if not ok:
                fallos.append(
                    f"{nombre}: {r:.2f}:1, por debajo de {minimo}:1 "
                    f"({texto} sobre {fondo})"
                )

    # 3 · El lima no sirve para texto, y hay que comprobar que sigue sin servir
    print("\nReglas de uso del lima (estos pares DEBEN quedar por debajo de 4.5)")
    for texto, fondo, nombre in PROHIBIDOS:
        r = ratio(texto, fondo, tokens)
        ok = r < 4.5
        print(f"  {'✓' if ok else '✕'} {r:5.2f}:1  {nombre}")
        if not ok:
            fallos.append(
                f"{nombre} da {r:.2f}:1. Si el lima ya sirviera para texto, "
                "revisa la regla de la spec 06 en lugar de ignorarla."
            )

    # 4 · Tamaño mínimo de fuente declarado en el CSS
    print("\nTamaños de fuente declarados")
    tamanos = sorted(
        {int(m) for m in re.findall(r"font-size:\s*(\d+)px", css)}
    )
    print(f"  tamaños en px: {tamanos}")
    menores = [t for t in tamanos if t < 14]
    if menores:
        fallos.append(
            f"hay font-size por debajo de 14px: {menores}. Nadie lee 12px desde "
            "la cuarta fila del salón."
        )
        print(f"  ✕ por debajo del mínimo de 14px: {menores}")
    else:
        print("  ✓ ninguno por debajo de 14px")

    print()
    if fallos:
        print(f"✕ {len(fallos)} problema(s) de identidad visual:\n")
        for f in fallos:
            print(f"  · {f}")
        return 1
    print("→ Paleta válida: marca exacta, contrastes medidos, mínimo de 14px.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
