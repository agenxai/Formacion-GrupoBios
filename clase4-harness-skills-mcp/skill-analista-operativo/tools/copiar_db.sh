#!/usr/bin/env bash
# Copia bios_ops.db desde la clase 1 al directorio de la Skill.
# No la regenera — la reutiliza (ADR-002 de la spec 02).
set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")/../../../.." && pwd)")"
SRC="$REPO_ROOT/clase1-lab-agentes/bios_ops.db"
DST="$(cd "$(dirname "$0")/.." && pwd)/bios_ops.db"

# Alternativa: si la base está en la clase 2 (mismo archivo, copia de S1).
if [ ! -f "$SRC" ]; then
  SRC="$REPO_ROOT/clase2-como-construir-agente/agente-transparente/bios_ops.db"
fi

if [ ! -f "$SRC" ]; then
  echo "✗ No encontré bios_ops.db en:"
  echo "    $REPO_ROOT/clase1-lab-agentes/bios_ops.db"
  echo "    $REPO_ROOT/clase2-como-construir-agente/agente-transparente/bios_ops.db"
  echo ""
  echo "  Generá la base desde la clase 1:"
  echo "    cd $REPO_ROOT/clase1-lab-agentes"
  echo "    python -m backend.db.seed --recrear"
  echo "  y volvé a correr este script."
  exit 1
fi

cp "$SRC" "$DST"
echo "✓ bios_ops.db copiada a:"
echo "    $DST"
