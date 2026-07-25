"""Laboratorio "Niveles de Agencia" — Sesión 1 del programa Qypher para Grupo Bios.

Un solo paquete compartido por los dos servicios del compose: el tablero
(`backend.main`) y el notebook. El notebook importa exactamente los mismos módulos
que corren detrás del tablero — si el notebook funciona, el tablero funciona. No hay
dos implementaciones que se desincronicen (spec 02).

Orden de lectura recomendado para quien venga a entender el código:

    1. backend/eventos.py     el contrato que hace comparables los cinco niveles
    2. backend/tools/         las 7 tools de dominio; la docstring es el prompt
    3. backend/niveles/n1..n5 un archivo por nivel de agencia
    4. backend/main.py        FastAPI y SSE
"""
