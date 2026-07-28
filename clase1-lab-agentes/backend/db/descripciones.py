"""Qué aporta cada tabla de `bios_ops.db`, en lenguaje de negocio. Spec 11.

Es lo ÚNICO del mapa de la base que se escribe a mano: nombres de tabla, columnas,
conteos y llaves foráneas se leen de la base misma (`PRAGMA`), pero «para qué sirve
esta tabla» no está en la base — hay que decirlo, y hay que decirlo para un no
técnico: *«cuánto hay de cada materia prima en cada planta, y el mínimo aceptable»*,
no *«tabla de hechos de inventario»*.

La prueba de humo verifica que cada tabla descrita acá existe en la base y que no
hay tablas sin describir: si alguien renombra o agrega una tabla, falla el chequeo
antes de la clase, no la demo.
"""

from __future__ import annotations

# Los dominios del laboratorio, en el orden en que se agrupan en el mapa.
# `marca` distingue el dominio por forma ADEMÁS de por color (spec 06: el color
# nunca es el único portador de significado; los proyectores desaturan).
DOMINIOS: dict[str, dict] = {
    "transversal": {
        "nombre": "Transversal",
        "marca": "●",
        "que_responde": "las plantas: de aquí cuelga casi todo",
    },
    "compras": {
        "nombre": "Compras y abastecimiento",
        "marca": "◆",
        "que_responde": "qué materia prima hay y cuánto falta",
    },
    "demanda": {
        "nombre": "Demanda y producción",
        "marca": "▲",
        "que_responde": "cuánto se vende y cuánto se fabrica",
    },
    "mantenimiento": {
        "nombre": "Mantenimiento",
        "marca": "⬢",
        "que_responde": "qué equipo falla y por qué",
    },
    "logistica": {
        "nombre": "Logística y despachos",
        "marca": "■",
        "que_responde": "dónde va cada pedido",
    },
}

# Una línea por tabla, escrita para leerse desde la última fila del salón. Van en
# el nodo del mapa: cortas, concretas y sin jerga de bases de datos.
TABLAS: dict[str, dict] = {
    "plantas": {
        "dominio": "transversal",
        "que_aporta": "Las 5 plantas: municipio y capacidad. Todo cuelga de aquí.",
    },
    "materias_primas": {
        "dominio": "compras",
        "que_aporta": "Las 8 materias primas y su tiempo de entrega de proveedor.",
    },
    "inventario_planta": {
        "dominio": "compras",
        "que_aporta": "Cuánto hay de cada materia prima por planta, y el mínimo.",
    },
    "formulas": {
        "dominio": "compras",
        "que_aporta": "La receta: qué % de cada materia prima lleva cada producto.",
    },
    "demanda_historica": {
        "dominio": "demanda",
        "que_aporta": "Cuánto se vendió, por planta, producto y día.",
    },
    "produccion_diaria": {
        "dominio": "demanda",
        "que_aporta": "Cuánto produjo cada planta por día, con sus paradas.",
    },
    "equipos": {
        "dominio": "mantenimiento",
        "que_aporta": "Las máquinas de cada planta: tipo y criticidad.",
    },
    "ordenes_mantenimiento": {
        "dominio": "mantenimiento",
        "que_aporta": "Cada intervención: tipo, causa, horas de paro y costo.",
    },
    "lecturas_sensor": {
        "dominio": "mantenimiento",
        "que_aporta": "Vibración, temperatura y amperaje de cada equipo, por hora.",
    },
    "pedidos": {
        "dominio": "logistica",
        "que_aporta": "Cada pedido: cliente, producto, toneladas, promesa y estado.",
    },
    "despachos": {
        "dominio": "logistica",
        "que_aporta": "Los camiones: turno de muelle, hora asignada y cargue real.",
    },
}
