"""Tools de dominio del laboratorio.

`operaciones` trae las 7 tools que usan los niveles 3, 4 y 5.
`sql_seguro` trae `ejecutar_sql`, el escape hatch del reto [NÚCLEO], que NO está
en la lista por defecto: se agrega a mano cuando se quiere discutir en clase que
la tool es la superficie de ataque del agente (spec 04).
"""

from backend.tools.operaciones import (  # noqa: F401
    LIMITE_FILAS,
    POR_NOMBRE,
    TODAS,
    TOOLS_ABASTECIMIENTO,
    TOOLS_OPERACIONES,
    consultar_demanda,
    consultar_inventario,
    consultar_produccion,
    estado_pedido,
    firmas,
    historial_fallas,
    lecturas_sensor,
    turnos_muelle,
)
