#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────────
#  scripts/verificar_vendor.py
#  Clase 3 · RAG — Verifica que assets/vendor/ contenga SOLO lo permitido.
#
#  Bloqueante para el estándar de curaduría visual (spec 04): no queremos
#  que se cuele una librería de UI genérica, ni que falte Plotly/Alpine.
# ──────────────────────────────────────────────────────────────────────────
"""Verifica contenido de app/frontend/assets/vendor/."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

VENDOR_DIR = (Path(__file__).resolve().parent.parent
              / "app" / "frontend" / "assets" / "vendor")

# Archivos esperados y hashes (sha256) registrados cuando se descargaron.
# Si se vuelve a descargar el vendor con otra versión, **regenerad el
# hash** con `sha256sum app/frontend/assets/vendor/plotly.min.js` y
# actualizad la entrada abajo. Está documentado en COMO-MONTARLO.md.
ESPERADOS = {
    "plotly.min.js": "REGISTRAR_HASH_POST_DOWNLOAD",
    "alpine.min.js": "REGISTRAR_HASH_POST_DOWNLOAD",
}

# BONUS permitidos (silenciosos — no se validan hash porque son opcionales
# como woff2 de Inter/JetBrains): si se incluyen, OK; si no, también OK.
BONUS_PERMITIDOS = {
    "inter.woff2",
    "jetbrains-mono.woff2",
    "ibm-plex-mono.woff2",
}


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not VENDOR_DIR.exists():
        print(f"✗ {VENDOR_DIR} no existe. Descargad los vendors con:")
        print("  cd app/frontend/assets/vendor")
        print("  curl -o plotly.min.js https://cdn.plot.ly/plotly-2.35.2.min.js")
        print("  curl -o alpine.min.js https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js")
        return 1

    archivos = {p.name for p in VENDOR_DIR.iterdir() if p.is_file()}

    # 1) Están los esperados
    faltantes = set(ESPERADOS) - archivos
    if faltantes:
        print(f"✗ Faltan vendors: {sorted(faltantes)}")
        return 1

    # 2) No hay extras no listados
    extras = archivos - set(ESPERADOS) - BONUS_PERMITIDOS
    if extras:
        print(f"✗ Vendors extra no permitidos: {sorted(extras)}")
        print("  Si necesitás uno de verdad, agregalo a BONUS_PERMITIDOS "
              "de este script y justificá por qué.")
        return 1

    # 3) Hashes (si están registrados)
    print("✓ Vendor directory OK:")
    for nombre in sorted(ESPERADOS):
        ruta = VENDOR_DIR / nombre
        size = ruta.stat().st_size
        registrado = ESPERADOS[nombre]
        if registrado.startswith("REGISTRAR"):
            print(f"  · {nombre}  ({size:,} bytes)  ⚠ hash no registrado "
                  f"todavía — actualizad después de download")
        else:
            actual = sha256(ruta)
            if actual == registrado:
                print(f"  ✓ {nombre}  ({size:,} bytes)  hash OK")
            else:
                print(f"  ✗ {nombre}  ({size:,} bytes)  hash NO coincide")
                print(f"      registrado: {registrado}")
                print(f"      actual:     {actual}")
                return 1

    for nombre in sorted(BONUS_PERMITIDOS & archivos):
        size = (VENDOR_DIR / nombre).stat().st_size
        print(f"  · {nombre}  ({size:,} bytes)  bonus permitido")

    return 0


if __name__ == "__main__":
    sys.exit(main())