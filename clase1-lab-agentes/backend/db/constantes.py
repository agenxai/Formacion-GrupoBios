"""Constantes garantizadas del dataset — contrato con las preguntas de demo.

Spec 03, sección "Constantes garantizadas". Las preguntas precargadas del tablero
(spec 07) y las demos de la spec 05 contienen identificadores literales. Si el
generador produjera otros, las cinco preguntas de la demo dejarían de funcionar y
`estado_pedido` respondería «no encontré ese pedido» en medio de la clase.

Este módulo es la única fuente de verdad: lo importa `seed.py` para fijar las
entidades y lo importa el catálogo de preguntas para construirlas. Nadie escribe
'PD-24-00871' a mano en dos sitios.

AVISO DE FICCIÓN: los municipios son reales; la asignación planta↔municipio es
inventada y no corresponde a la red de operaciones de Grupo Bios.
"""

# --- Plantas -----------------------------------------------------------------
# (id, nombre, municipio, capacidad_ton_dia)
PLANTAS: list[tuple[str, str, str, float]] = [
    ("PL-ITG", "Planta Itagüí", "Itagüí", 620.0),
    ("PL-BUG", "Planta Buga", "Guadalajara de Buga", 900.0),
    ("PL-MOS", "Planta Mosquera", "Mosquera", 480.0),
    ("PL-BAQ", "Planta Barranquilla", "Barranquilla", 350.0),
    ("PL-PAL", "Planta Palmira", "Palmira", 180.0),
]

# --- Materias primas ---------------------------------------------------------
# (id, nombre, unidad, dias_lead_time)
MATERIAS_PRIMAS: list[tuple[str, str, str, int]] = [
    ("MP-MAIZ", "Maíz amarillo", "ton", 21),
    ("MP-SOYA", "Soya en grano", "ton", 30),
    ("MP-TSOY", "Torta de soya", "ton", 25),
    ("MP-SALV", "Salvado de trigo", "ton", 10),
    ("MP-ACEI", "Aceite de palma", "ton", 14),
    ("MP-PREM", "Premezcla vitamínica", "ton", 45),
    ("MP-CARB", "Carbonato de calcio", "ton", 7),
    ("MP-METI", "Metionina", "ton", 60),
]

# Los tres productos terminados que aparecen en demanda y pedidos.
PRODUCTOS: list[str] = [
    "Alimento avícola engorde",
    "Alimento porcícola levante",
    "Alimento bovino lechero",
]

# Clientes ficticios (spec 03: la cartera no representa la de Grupo Bios).
CLIENTES: list[str] = [
    "Avícola El Roble",
    "Porcícola La Esperanza",
    "Ganadería San Isidro",
    "Granjas Villa Nueva",
    "Distribuidora Campoalegre",
    "Agropecuaria Los Nogales",
    "Avícola Santa Marta del Valle",
    "Comercializadora El Pinar",
]

TIPOS_EQUIPO: list[str] = ["Molino", "Peletizadora", "Mezcladora", "Enfriador"]

# --- Máquina de estados de pedidos (spec 03) ---------------------------------
# Ordenada: de aquí sale la interfaz "tipo aeropuerto" del caso de Logística.
FLUJO_PEDIDO: list[str] = [
    "registrado",
    "programado",
    "en_produccion",
    "listo_despacho",
    "en_muelle",
    "cargado",
    "en_transito",
    "entregado",
]
ESTADO_EXCEPCION = "novedad"


# --- Anomalías plantadas a propósito (spec 03) -------------------------------

# Anomalía 1 — inventario bajo mínimo que no cubre la demanda de la semana.
PLANTA_DEFICIT = "PL-ITG"
MATERIA_DEFICIT = "MP-MAIZ"  # 'Maíz amarillo'

# Anomalía 2 — vibración en ascenso monótono + 3 correctivos en 60 días.
EQUIPO_EN_RIESGO = "EQ-ITG-MOL-01"  # Molino, criticidad alta, planta Itagüí

# Anomalía 3 — pedido atascado en 'en_muelle' detrás de una cola de 6 turnos.
PEDIDO_ATASCADO = "PD-24-00871"
PLANTA_PEDIDO = "PL-ITG"  # mismo sitio: habilita la pregunta cruzada de N5
POSICION_COLA_ATASCADO = 6

# Anomalía 4 — día con demanda por encima de la producción.
PLANTA_PICO = "PL-BUG"

# `PEDIDO_ATASCADO` y `EQUIPO_EN_RIESGO` DEBEN pertenecer a la misma planta: es lo
# que hace posible la pregunta cruzada de N5 («¿el retraso es por materia prima o
# por equipos?»), donde el supervisor consulta dos dominios sobre un mismo sitio y
# concluye que la causa es el inventario, no los equipos.
assert PLANTA_PEDIDO == PLANTA_DEFICIT, (
    "El pedido atascado y el déficit de materia prima deben estar en la misma "
    "planta; si no, la pregunta cruzada de N5 no tiene respuesta."
)

# --- Aviso de datos sintéticos (spec 03) -------------------------------------
# Texto único, reusado por el tablero, el notebook y el README.
AVISO_DATOS_SINTETICOS = (
    "Todos los datos de bios_ops.db son sintéticos, generados por "
    "backend/db/seed.py. Los nombres de plantas, productos, equipos y clientes "
    "son ficticios y no representan la red de operaciones, los proveedores ni la "
    "cartera de clientes de Grupo Bios. Ningún dato real de la compañía se "
    "procesa en esta sesión."
)
