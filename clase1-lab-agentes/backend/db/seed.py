"""Generador de datos sintéticos de `bios_ops.db`.

Spec 03. Determinista por ADR-005: con `SEMILLA_DATOS` fija la base es idéntica en
toda máquina. Eso da tres cosas: la demo del facilitador coincide con lo que ve el
participante, las respuestas se pueden cachear entre participantes (crítico con key
compartida) y las trazas de replay siguen siendo válidas.

Uso:
    python -m backend.db.seed --recrear

Termina con una autocomprobación que FALLA si alguna de las cuatro anomalías
plantadas o alguno de los identificadores de demo no quedó en la base. Es la clase
de fallo que se descubre en el minuto 12 de la clase si no se verifica antes.
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.config import config
from backend.db import constantes as K

DIAS_DEMANDA = 180
DIAS_INVENTARIO = 30
DIAS_SENSOR = 30
LECTURAS_POR_DIA = 4
HORAS_LECTURA = (2, 8, 14, 20)
DIAS_ORDENES = 365
N_PEDIDOS = 150
PRIMER_PEDIDO = 801  # PD-24-00801 … PD-24-00950 (contiene PD-24-00871)

# Utilización media de la capacidad instalada. Con esto la demanda generada guarda
# una relación creíble con `capacidad_ton_dia` de cada planta.
UTILIZACION = 0.68

# Mezcla de productos en la demanda de cada planta.
MEZCLA = {
    "Alimento avícola engorde": 0.45,
    "Alimento porcícola levante": 0.33,
    "Alimento bovino lechero": 0.22,
}

# Participación de cada materia prima por producto, en % de peso. Suma 100.
# Valores plausibles para alimento balanceado; sintéticos, no de Grupo Bios.
FORMULAS: dict[str, dict[str, float]] = {
    "Alimento avícola engorde": {
        "MP-MAIZ": 60.0, "MP-TSOY": 22.0, "MP-ACEI": 5.0, "MP-SALV": 4.0,
        "MP-CARB": 5.0, "MP-PREM": 2.0, "MP-METI": 1.0, "MP-SOYA": 1.0,
    },
    "Alimento porcícola levante": {
        "MP-MAIZ": 57.0, "MP-TSOY": 18.0, "MP-SALV": 12.0, "MP-ACEI": 3.0,
        "MP-CARB": 6.0, "MP-PREM": 2.0, "MP-METI": 1.0, "MP-SOYA": 1.0,
    },
    "Alimento bovino lechero": {
        "MP-MAIZ": 48.0, "MP-TSOY": 15.0, "MP-SALV": 20.0, "MP-ACEI": 3.0,
        "MP-CARB": 8.0, "MP-PREM": 3.0, "MP-METI": 1.0, "MP-SOYA": 2.0,
    },
}

SIGLA_TIPO = {
    "Molino": "MOL",
    "Peletizadora": "PEL",
    "Mezcladora": "MEZ",
    "Enfriador": "ENF",
}

VARIABLES_SENSOR = {
    # variable: (base, amplitud_ruido, unidad)
    "vibracion_mm_s": (2.6, 0.35, "mm/s"),
    "temperatura_c": (68.0, 4.0, "°C"),
    "amperaje_a": (142.0, 9.0, "A"),
}

CAUSAS_CORRECTIVO = [
    "Rodamiento con desgaste",
    "Correa desalineada",
    "Obstrucción en tolva",
    "Falla de variador de frecuencia",
    "Fuga en sello mecánico",
]
CAUSA_RECURRENTE = "Desbalanceo de rotor con vibración excesiva"

# Vibración del equipo en riesgo: pendiente diaria del ascenso monótono.
PENDIENTE_VIBRACION = 0.11  # mm/s por día
VIBRACION_INICIAL = 3.2

# Anomalía 1 — valores fijados. `320` aparece en los criterios de aceptación de la
# spec 08 y en la maqueta de la spec 07: es un número con contrato, no decorativo.
INVENTARIO_MAIZ_DEFICIT = 320.0

# Anomalía 4 — magnitud del día en que la demanda superó la producción.
BRECHA_PICO_TON = 73.0
DIAS_ATRAS_PICO = 37


def _f(d: date) -> str:
    return d.isoformat()


# ---------------------------------------------------------------------------
#  Generación
# ---------------------------------------------------------------------------


class Generador:
    def __init__(self, semilla: int, fecha_base: date) -> None:
        self.rnd = random.Random(semilla)
        self.hoy = fecha_base
        self.demanda: dict[tuple[str, str, str], float] = {}
        self.consumo_mp: dict[tuple[str, str, str], float] = {}

    # --- catálogos ---------------------------------------------------------

    def plantas(self) -> list[tuple]:
        return [(pid, nombre, mun, cap, 1) for pid, nombre, mun, cap in K.PLANTAS]

    def materias(self) -> list[tuple]:
        return list(K.MATERIAS_PRIMAS)

    def formulas(self) -> list[tuple]:
        filas = []
        for producto, comp in FORMULAS.items():
            total = round(sum(comp.values()), 6)
            if abs(total - 100.0) > 1e-6:
                raise ValueError(
                    f"La fórmula de '{producto}' suma {total}%, debe sumar 100%."
                )
            for mp, pct in comp.items():
                filas.append((producto, mp, pct))
        return filas

    # --- demanda y producción ---------------------------------------------

    def demanda_historica(self) -> list[tuple]:
        """Tendencia + estacionalidad semanal + ruido, por planta y producto."""
        filas = []
        for pid, _, _, capacidad in K.PLANTAS:
            base_dia = capacidad * UTILIZACION
            # Cada planta tiene su propia tendencia suave, entre -8% y +18% anual.
            tendencia_anual = self.rnd.uniform(-0.08, 0.18)
            for i in range(DIAS_DEMANDA):
                d = self.hoy - timedelta(days=DIAS_DEMANDA - 1 - i)
                avance = i / max(DIAS_DEMANDA - 1, 1)
                factor_tendencia = 1 + tendencia_anual * avance
                # Domingo baja fuerte, sábado algo; el resto plano.
                dow = d.weekday()
                factor_semana = {6: 0.55, 5: 0.85}.get(dow, 1.03)
                for producto, peso in MEZCLA.items():
                    ruido = self.rnd.gauss(1.0, 0.07)
                    ton = base_dia * peso * factor_tendencia * factor_semana * ruido
                    ton = max(round(ton, 1), 0.0)
                    self.demanda[(pid, _f(d), producto)] = ton
                    filas.append((pid, _f(d), producto, ton))
        return filas

    def _demanda_dia(self, pid: str, d: date) -> float:
        return round(
            sum(self.demanda.get((pid, _f(d), p), 0.0) for p in MEZCLA), 1
        )

    def produccion_diaria(self) -> list[tuple]:
        """Producción que cubre la demanda, salvo el día del pico plantado.

        Se genera por encima de la demanda a propósito: así la pregunta «¿hubo
        algún día en que la demanda superó la producción?» tiene UNA respuesta
        verificable en lugar de varias por casualidad del ruido.
        """
        dia_pico = self.hoy - timedelta(days=DIAS_ATRAS_PICO)
        filas = []
        for pid, _, _, _ in K.PLANTAS:
            for i in range(DIAS_DEMANDA):
                d = self.hoy - timedelta(days=DIAS_DEMANDA - 1 - i)
                dem = self._demanda_dia(pid, d)
                paradas = 0
                if self.rnd.random() < 0.12:
                    paradas = self.rnd.choice([25, 40, 55, 70, 95, 120])
                if pid == K.PLANTA_PICO and d == dia_pico:
                    # Anomalía 4: la producción se queda corta por una parada larga.
                    ton = round(dem - BRECHA_PICO_TON, 1)
                    paradas = 180
                else:
                    ton = round(dem * self.rnd.uniform(1.01, 1.09), 1)
                filas.append((pid, _f(d), max(ton, 0.0), paradas))
        return filas

    # --- inventario --------------------------------------------------------

    def _consumo_diario_mp(self, pid: str, d: date, mp: str) -> float:
        """Toneladas de una materia prima que consume la planta ese día.

        Es la demanda de cada producto multiplicada por su inclusión en fórmula.
        La misma cuenta que hará `consultar_demanda` — de un solo sitio, para que
        el dato de la tool y el dato del generador no puedan divergir.
        """
        total = 0.0
        for producto, comp in FORMULAS.items():
            ton = self.demanda.get((pid, _f(d), producto), 0.0)
            total += ton * comp.get(mp, 0.0) / 100.0
        return total

    def inventario(self) -> list[tuple]:
        filas = []
        for pid, _, _, _ in K.PLANTAS:
            for mp, _nombre, _unidad, _lead in K.MATERIAS_PRIMAS:
                # Consumo medio diario de los últimos 30 días.
                consumos = [
                    self._consumo_diario_mp(
                        pid, self.hoy - timedelta(days=k), mp
                    )
                    for k in range(DIAS_INVENTARIO)
                ]
                consumo_medio = sum(consumos) / len(consumos)
                # Stock mínimo ≈ 5 días de consumo, redondeado a decena.
                minimo = max(round(consumo_medio * 5, -1), 1.0)

                es_deficit = pid == K.PLANTA_DEFICIT and mp == K.MATERIA_DEFICIT
                if es_deficit:
                    # Anomalía 1: caída sostenida hasta quedar muy bajo el mínimo.
                    inicial = minimo * 1.55
                    final = INVENTARIO_MAIZ_DEFICIT
                else:
                    inicial = minimo * self.rnd.uniform(1.5, 2.6)
                    final = minimo * self.rnd.uniform(1.15, 2.1)

                for i in range(DIAS_INVENTARIO):
                    d = self.hoy - timedelta(days=DIAS_INVENTARIO - 1 - i)
                    avance = i / max(DIAS_INVENTARIO - 1, 1)
                    # Interpolación con ruido: un camino con consumo y reposiciones.
                    cantidad = inicial + (final - inicial) * avance
                    if i < DIAS_INVENTARIO - 1:
                        cantidad *= self.rnd.gauss(1.0, 0.035)
                    else:
                        cantidad = final  # el último corte es el valor fijado
                    filas.append(
                        (pid, mp, _f(d), round(max(cantidad, 0.0), 1), round(minimo, 1))
                    )
        return filas

    # --- equipos y mantenimiento -------------------------------------------

    def equipos(self) -> list[tuple]:
        filas = []
        for pid, _, _, _ in K.PLANTAS:
            sigla_planta = pid.split("-")[1]
            for tipo in K.TIPOS_EQUIPO:
                eid = f"EQ-{sigla_planta}-{SIGLA_TIPO[tipo]}-01"
                if eid == K.EQUIPO_EN_RIESGO:
                    criticidad = "alta"
                else:
                    criticidad = self.rnd.choice(["alta", "media", "media", "baja"])
                antiguedad = self.rnd.randint(400, 4200)
                instalacion = self.hoy - timedelta(days=antiguedad)
                filas.append((eid, pid, tipo, criticidad, _f(instalacion)))
        return filas

    def ordenes(self, equipos: list[tuple]) -> list[tuple]:
        """~200 órdenes en 365 días.

        El equipo en riesgo recibe tres correctivos en los últimos 60 días con la
        misma causa. Los demás equipos quedan limitados a un correctivo en esa
        ventana, para que «¿cuál equipo está en riesgo?» tenga una sola respuesta
        defendible en lugar de un empate.
        """
        filas: list[tuple] = []
        consecutivo = 1

        def nueva(eid: str, apertura: date, tipo: str, causa: str | None) -> None:
            nonlocal consecutivo
            horas = round(self.rnd.uniform(1.5, 9.0), 1) if tipo == "correctivo" else round(
                self.rnd.uniform(0.5, 4.0), 1
            )
            costo = round(horas * self.rnd.uniform(180_000, 900_000), -3)
            dias_abierta = self.rnd.randint(0, 3)
            cierre = apertura + timedelta(days=dias_abierta)
            abierta_aun = cierre > self.hoy
            filas.append(
                (
                    f"OM-{consecutivo:06d}",
                    eid,
                    _f(apertura),
                    None if abierta_aun else _f(cierre),
                    tipo,
                    causa,
                    horas,
                    costo,
                )
            )
            consecutivo += 1

        # Anomalía 2: tres correctivos recurrentes en 60 días, en ascenso de
        # frecuencia (más juntos hacia el presente).
        for dias_atras in (52, 27, 9):
            nueva(
                K.EQUIPO_EN_RIESGO,
                self.hoy - timedelta(days=dias_atras),
                "correctivo",
                CAUSA_RECURRENTE,
            )

        ids = [e[0] for e in equipos]
        objetivo = 200 - len(filas)
        for _ in range(objetivo):
            eid = self.rnd.choice(ids)
            dias_atras = self.rnd.randint(1, DIAS_ORDENES)
            tipo = self.rnd.choices(
                ["preventivo", "correctivo", "predictivo"], weights=[6, 3, 1]
            )[0]
            if tipo == "correctivo" and dias_atras <= 60 and eid != K.EQUIPO_EN_RIESGO:
                # Fuera de la ventana de 60 días para no competir con la anomalía.
                dias_atras = self.rnd.randint(61, DIAS_ORDENES)
            causa = self.rnd.choice(CAUSAS_CORRECTIVO) if tipo == "correctivo" else None
            nueva(eid, self.hoy - timedelta(days=dias_atras), tipo, causa)
        return filas

    def lecturas(self, equipos: list[tuple]) -> list[tuple]:
        """20 equipos × 30 días × 4 lecturas × 3 variables = 7.200 filas.

        En el equipo en riesgo la vibración es estrictamente creciente: el
        incremento por lectura es siempre positivo, así que no hay ruido que pueda
        romper la monotonía y la conclusión del caso de mantenimiento es sólida.
        """
        filas = []
        for eid, _pid, _tipo, _crit, _inst in equipos:
            acumulado = VIBRACION_INICIAL
            paso = PENDIENTE_VIBRACION / LECTURAS_POR_DIA
            for i in range(DIAS_SENSOR):
                d = self.hoy - timedelta(days=DIAS_SENSOR - 1 - i)
                for hora in HORAS_LECTURA:
                    ts = datetime(d.year, d.month, d.day, hora).isoformat(
                        sep=" ", timespec="minutes"
                    )
                    for variable, (base, amplitud, _u) in VARIABLES_SENSOR.items():
                        if variable == "vibracion_mm_s" and eid == K.EQUIPO_EN_RIESGO:
                            acumulado += paso * self.rnd.uniform(0.55, 1.45)
                            valor = round(acumulado, 2)
                        else:
                            valor = round(self.rnd.gauss(base, amplitud / 3), 2)
                        filas.append((eid, ts, variable, valor))
        return filas

    # --- pedidos y despachos ----------------------------------------------

    def _pedidos_delante(self) -> list[str]:
        """Los pedidos que van delante del atascado en la cola del muelle.

        Son los cinco consecutivos anteriores a `PEDIDO_ATASCADO`. Devolverlos en
        orden importa: ese orden es el de los turnos 1 a 5.
        """
        n_atascado = int(K.PEDIDO_ATASCADO.rsplit("-", 1)[1])
        cuantos = K.POSICION_COLA_ATASCADO - 1
        return [f"PD-24-{n:05d}" for n in range(n_atascado - cuantos, n_atascado)]

    def pedidos(self) -> list[tuple]:
        """150 pedidos por todos los estados; PD-24-00871 atascado en muelle.

        Los cinco pedidos inmediatamente anteriores al atascado se fijan en la
        misma planta y en muelle: son los camiones que tiene delante. No se deja
        al azar porque de ahí sale la posición 6 de la cola, que es un número con
        contrato (spec 03) y que al generarse aleatoriamente salía unas veces sí y
        otras no.
        """
        filas = []
        ids_planta = [p[0] for p in K.PLANTAS]
        delante = self._pedidos_delante()
        for n in range(N_PEDIDOS):
            numero = f"PD-24-{PRIMER_PEDIDO + n:05d}"
            es_atascado = numero == K.PEDIDO_ATASCADO
            es_delante = numero in delante
            if es_atascado or es_delante:
                planta = K.PLANTA_PEDIDO
            else:
                planta = self.rnd.choice(ids_planta)
            cliente = (
                K.CLIENTES[0] if es_atascado else self.rnd.choice(K.CLIENTES)
            )
            producto = self.rnd.choice(K.PRODUCTOS)
            toneladas = round(self.rnd.uniform(8, 34), 1)
            if es_atascado:
                estado = "en_muelle"
                dias_pedido = 6
                dias_promesa = -1  # prometido ayer: va retrasado
            elif es_delante:
                estado = "en_muelle"
                dias_pedido = self.rnd.randint(2, 8)
                dias_promesa = self.rnd.randint(0, 3)
            else:
                estado = self.rnd.choices(
                    K.FLUJO_PEDIDO + [K.ESTADO_EXCEPCION],
                    weights=[4, 6, 8, 8, 7, 7, 10, 46, 4],
                )[0]
                dias_pedido = self.rnd.randint(1, 40)
                dias_promesa = self.rnd.randint(-3, 12)
            fecha_pedido = self.hoy - timedelta(days=dias_pedido)
            fecha_promesa = self.hoy + timedelta(days=dias_promesa)
            filas.append(
                (
                    numero,
                    cliente,
                    planta,
                    producto,
                    toneladas,
                    _f(fecha_pedido),
                    _f(fecha_promesa),
                    estado,
                )
            )
        return filas

    def despachos(self, pedidos: list[tuple]) -> list[tuple]:
        """Cola de muelle con turnos consecutivos por planta.

        Dos requisitos que no son cosméticos:

        · `PEDIDO_ATASCADO` queda en la posición 6 de la cola del día de hoy en su
          planta, con cinco camiones delante sin cargar (anomalía 3).
        · Cada planta acumula al menos 5 despachos cerrados con hora de cargue
          real, porque `eta_estimada` necesita la mediana de esos tiempos y sin
          ella devuelve `null` (spec 04).
        """
        filas: list[tuple] = []
        por_planta_hoy: dict[str, int] = {}
        consecutivo = 1
        estados_con_despacho = {"en_muelle", "cargado", "en_transito", "entregado"}

        def placa() -> str:
            letras = "".join(self.rnd.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(3))
            return f"{letras}{self.rnd.randint(100, 999)}"

        # 1. Historial cerrado: 8 despachos por planta en días pasados, con hora de
        #    cargue real. Es lo que alimenta la mediana de tiempo de cargue.
        for pid, _, _, _ in K.PLANTAS:
            for k in range(8):
                d = self.hoy - timedelta(days=self.rnd.randint(2, 20))
                asignada = datetime(d.year, d.month, d.day, self.rnd.randint(6, 15), 0)
                demora = self.rnd.randint(35, 115)
                real = asignada + timedelta(minutes=demora)
                filas.append(
                    (
                        f"DS-{consecutivo:05d}",
                        None,  # se asigna abajo a un pedido entregado de la planta
                        placa(),
                        k + 1,
                        asignada.isoformat(sep=" ", timespec="minutes"),
                        real.isoformat(sep=" ", timespec="minutes"),
                        "cerrado",
                    )
                )
                consecutivo += 1
                por_planta_hoy.setdefault(pid, 0)

        # Los despachos históricos se cuelgan de pedidos entregados de cada planta.
        entregados: dict[str, list[str]] = {}
        for numero, _cli, planta, _prod, _ton, _fp, _fpr, estado in pedidos:
            if estado == "entregado":
                entregados.setdefault(planta, []).append(numero)

        i_hist = 0
        arreglados: list[tuple] = []
        for pid, _, _, _ in K.PLANTAS:
            disponibles = entregados.get(pid, [])
            for k in range(8):
                fila = list(filas[i_hist])
                if k < len(disponibles):
                    fila[1] = disponibles[k]
                    arreglados.append(tuple(fila))
                i_hist += 1
        filas = arreglados

        # 2. Cola de hoy en la planta del pedido atascado. Cinco camiones delante,
        #    ninguno cargado todavía: por eso el pedido no avanza.
        cola_hoy = self._pedidos_delante()

        for turno, numero in enumerate(cola_hoy, start=1):
            asignada = datetime(
                self.hoy.year, self.hoy.month, self.hoy.day, 6 + turno, 0
            )
            filas.append(
                (
                    f"DS-{consecutivo:05d}",
                    numero,
                    placa(),
                    turno,
                    asignada.isoformat(sep=" ", timespec="minutes"),
                    None,
                    "en_espera",
                )
            )
            consecutivo += 1

        asignada = datetime(
            self.hoy.year,
            self.hoy.month,
            self.hoy.day,
            6 + K.POSICION_COLA_ATASCADO,
            0,
        )
        filas.append(
            (
                f"DS-{consecutivo:05d}",
                K.PEDIDO_ATASCADO,
                placa(),
                K.POSICION_COLA_ATASCADO,
                asignada.isoformat(sep=" ", timespec="minutes"),
                None,
                "en_espera",
            )
        )
        consecutivo += 1

        # 3. Resto de despachos: pedidos ya movidos.
        #
        # Dos reglas que salieron de que la autocomprobación fallara:
        #
        # · En la planta del pedido atascado, todos los despachos de este bloque
        #   quedan CERRADOS. Si alguno quedara 'en_espera' con un turno menor a 6,
        #   se sumaría a la cola de hoy y correría la posición del pedido — que es
        #   justamente el número con contrato de la anomalía 3.
        # · Un despacho 'en_espera' con hora asignada en el pasado es incoherente:
        #   un camión no espera turno tres semanas. Los que quedan en espera se
        #   ponen en la cola de HOY, y los de días pasados van cerrados.
        turno_hoy: dict[str, int] = {}
        restantes = [
            (n, planta)
            for n, _c, planta, _p, _t, _fp, _fpr, estado in pedidos
            if estado in estados_con_despacho
            and n != K.PEDIDO_ATASCADO
            and n not in cola_hoy
        ]
        self.rnd.shuffle(restantes)
        for numero, pid in restantes[: 90 - len(filas)]:
            en_planta_del_atascado = pid == K.PLANTA_PEDIDO
            cerrado = en_planta_del_atascado or self.rnd.random() < 0.75
            if cerrado:
                d = self.hoy - timedelta(days=self.rnd.randint(1, 25))
                asignada = datetime(d.year, d.month, d.day, self.rnd.randint(6, 16), 0)
                real = asignada + timedelta(minutes=self.rnd.randint(30, 130))
                turno = self.rnd.randint(1, 9)
            else:
                turno_hoy[pid] = turno_hoy.get(pid, 0) + 1
                turno = turno_hoy[pid]
                asignada = datetime(
                    self.hoy.year, self.hoy.month, self.hoy.day, 6 + turno, 0
                )
                real = None
            filas.append(
                (
                    f"DS-{consecutivo:05d}",
                    numero,
                    placa(),
                    turno,
                    asignada.isoformat(sep=" ", timespec="minutes"),
                    real.isoformat(sep=" ", timespec="minutes") if real else None,
                    "cerrado" if cerrado else "en_espera",
                )
            )
            consecutivo += 1
        return filas


# ---------------------------------------------------------------------------
#  Escritura
# ---------------------------------------------------------------------------


def construir(ruta: Path, semilla: int, fecha_base: date) -> dict[str, int]:
    esquema = (Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8")
    gen = Generador(semilla, fecha_base)

    if ruta.exists():
        ruta.unlink()
    con = sqlite3.connect(ruta)
    try:
        con.executescript(esquema)

        lotes: list[tuple[str, str, list[tuple]]] = []
        lotes.append(("plantas", "?,?,?,?,?", gen.plantas()))
        lotes.append(("materias_primas", "?,?,?,?", gen.materias()))
        lotes.append(("formulas", "?,?,?", gen.formulas()))
        # La demanda va primero: el inventario y la producción se derivan de ella.
        lotes.append(("demanda_historica", "?,?,?,?", gen.demanda_historica()))
        lotes.append(("produccion_diaria", "?,?,?,?", gen.produccion_diaria()))
        lotes.append(("inventario_planta", "?,?,?,?,?", gen.inventario()))

        equipos = gen.equipos()
        lotes.append(("equipos", "?,?,?,?,?", equipos))
        lotes.append(("ordenes_mantenimiento", "?,?,?,?,?,?,?,?", gen.ordenes(equipos)))
        lotes.append(("lecturas_sensor", "?,?,?,?", gen.lecturas(equipos)))

        pedidos = gen.pedidos()
        lotes.append(("pedidos", "?,?,?,?,?,?,?,?", pedidos))
        lotes.append(("despachos", "?,?,?,?,?,?,?", gen.despachos(pedidos)))

        conteos: dict[str, int] = {}
        for tabla, marcas, filas in lotes:
            con.executemany(f"INSERT INTO {tabla} VALUES ({marcas})", filas)
            conteos[tabla] = len(filas)
        con.commit()
    finally:
        con.close()
    return conteos


# ---------------------------------------------------------------------------
#  Autocomprobación — spec 03, "Verificación del contrato de datos"
# ---------------------------------------------------------------------------


def verificar(ruta: Path, conteos: dict[str, int], fecha_base: date) -> bool:
    """Comprueba las cuatro anomalías y los identificadores de demo.

    Si esto no pasa, la base no sirve y el laboratorio no debe arrancar.
    """
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    fallos: list[str] = []
    ok = "✓"

    def q(sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        return con.execute(sql, params).fetchall()

    total = sum(conteos.values())
    print(f"{ok} {len(conteos)} tablas · {total:,} filas".replace(",", "."))

    # --- Anomalía 1 -------------------------------------------------------
    fila = q(
        """SELECT cantidad_ton, stock_minimo_ton, fecha_corte
             FROM inventario_planta
            WHERE planta_id = ? AND materia_prima_id = ?
            ORDER BY fecha_corte DESC LIMIT 1""",
        (K.PLANTA_DEFICIT, K.MATERIA_DEFICIT),
    )
    if not fila:
        fallos.append(
            f"No hay inventario de {K.MATERIA_DEFICIT} en {K.PLANTA_DEFICIT}."
        )
    else:
        cant, minimo, corte = fila[0]["cantidad_ton"], fila[0]["stock_minimo_ton"], fila[0]["fecha_corte"]
        bajo = cant < minimo
        # Requerimiento de la semana según fórmula y demanda de los últimos 7 días.
        req = q(
            """SELECT SUM(d.toneladas * f.inclusion_pct / 100.0) AS req
                 FROM demanda_historica d
                 JOIN formulas f ON f.producto = d.producto
                WHERE d.planta_id = ? AND f.materia_prima_id = ?
                  AND d.fecha > date(?, '-7 day')""",
            (K.PLANTA_DEFICIT, K.MATERIA_DEFICIT, corte),
        )[0]["req"]
        brecha = (req or 0) - cant
        print(
            f"{ok} {K.PLANTA_DEFICIT} existe · inventario {K.MATERIA_DEFICIT} = "
            f"{cant} t · mínimo = {minimo} t · "
            f"{'bajo mínimo ✓' if bajo else '✕ NO está bajo mínimo'}"
        )
        print(
            f"{ok} requerimiento de 7 días = {req:.1f} t · "
            f"{'no alcanza, faltan %.1f t ✓' % brecha if brecha > 0 else '✕ alcanza'}"
        )
        if not bajo:
            fallos.append("El inventario de la anomalía 1 no quedó bajo el mínimo.")
        if brecha <= 0:
            fallos.append("El inventario de la anomalía 1 alcanza para la semana.")

    # --- Anomalía 2 -------------------------------------------------------
    if not q("SELECT 1 FROM equipos WHERE id = ?", (K.EQUIPO_EN_RIESGO,)):
        fallos.append(f"El equipo {K.EQUIPO_EN_RIESGO} no existe.")
    else:
        correctivos = q(
            """SELECT COUNT(*) AS n FROM ordenes_mantenimiento
                WHERE equipo_id = :eq AND tipo = 'correctivo'
                  AND fecha_apertura > date(:hoy, '-60 day')""",
            {"eq": K.EQUIPO_EN_RIESGO, "hoy": fecha_base.isoformat()},
        )[0]["n"]
        serie = [
            r["valor"]
            for r in q(
                """SELECT valor FROM lecturas_sensor
                    WHERE equipo_id = ? AND variable = 'vibracion_mm_s'
                    ORDER BY ts""",
                (K.EQUIPO_EN_RIESGO,),
            )
        ]
        monotona = all(b >= a for a, b in zip(serie, serie[1:]))
        dias = max(DIAS_SENSOR - 1, 1)
        pendiente = (serie[-1] - serie[0]) / dias if serie else 0.0
        print(
            f"{ok} {K.EQUIPO_EN_RIESGO} existe · {correctivos} correctivos en 60 d · "
            f"tendencia vibración = {pendiente:+.2f} mm/s·día · "
            f"{'monótona ✓' if monotona else '✕ no monótona'}"
        )
        if correctivos < 3:
            fallos.append(
                f"El equipo en riesgo tiene {correctivos} correctivos en 60 días, "
                "se esperaban 3."
            )
        if not monotona or pendiente <= 0:
            fallos.append("La vibración del equipo en riesgo no es creciente.")

        # Que sea EL equipo en riesgo, no uno de varios empatados.
        competencia = q(
            """SELECT equipo_id, COUNT(*) AS n FROM ordenes_mantenimiento
                WHERE tipo = 'correctivo' AND fecha_apertura > date(:hoy, '-60 day')
                  AND equipo_id <> :eq
                GROUP BY equipo_id HAVING n >= 3""",
            {"eq": K.EQUIPO_EN_RIESGO, "hoy": fecha_base.isoformat()},
        )
        if competencia:
            fallos.append(
                "Otros equipos empatan en correctivos recientes: "
                + ", ".join(r["equipo_id"] for r in competencia)
            )

    # --- Anomalía 3 -------------------------------------------------------
    ped = q(
        "SELECT estado, planta_id FROM pedidos WHERE numero = ?",
        (K.PEDIDO_ATASCADO,),
    )
    desp = q(
        "SELECT turno_muelle, estado FROM despachos WHERE pedido_numero = ?",
        (K.PEDIDO_ATASCADO,),
    )
    if not ped:
        fallos.append(f"El pedido {K.PEDIDO_ATASCADO} no existe.")
    elif not desp:
        fallos.append(f"El pedido {K.PEDIDO_ATASCADO} no tiene despacho asignado.")
    else:
        delante = q(
            """SELECT COUNT(*) AS n FROM despachos d
                 JOIN pedidos p ON p.numero = d.pedido_numero
                WHERE p.planta_id = ? AND d.estado = 'en_espera'
                  AND d.turno_muelle < ?""",
            (ped[0]["planta_id"], desp[0]["turno_muelle"]),
        )[0]["n"]
        posicion = delante + 1
        print(
            f"{ok} {K.PEDIDO_ATASCADO} existe · estado = {ped[0]['estado']} · "
            f"posición en cola = {posicion} "
            f"{'✓' if posicion == K.POSICION_COLA_ATASCADO else '✕'}"
        )
        if ped[0]["estado"] != "en_muelle":
            fallos.append("El pedido atascado no quedó en estado 'en_muelle'.")
        if posicion != K.POSICION_COLA_ATASCADO:
            fallos.append(
                f"El pedido atascado quedó en posición {posicion}, "
                f"se esperaba {K.POSICION_COLA_ATASCADO}."
            )
        if ped[0]["planta_id"] != K.PLANTA_DEFICIT:
            fallos.append(
                "El pedido atascado no está en la planta del déficit: la pregunta "
                "cruzada de N5 no tendría respuesta."
            )

    # --- Anomalía 4 -------------------------------------------------------
    picos = q(
        """SELECT d.fecha, SUM(d.toneladas) AS dem, pr.toneladas AS prod
             FROM demanda_historica d
             JOIN produccion_diaria pr
               ON pr.planta_id = d.planta_id AND pr.fecha = d.fecha
            WHERE d.planta_id = ?
            GROUP BY d.fecha, pr.toneladas
           HAVING dem > prod
            ORDER BY (dem - prod) DESC""",
        (K.PLANTA_PICO,),
    )
    if not picos:
        fallos.append(f"{K.PLANTA_PICO} no tiene ningún día con demanda > producción.")
    else:
        print(
            f"{ok} {K.PLANTA_PICO} tiene {len(picos)} día(s) con demanda > producción "
            f"({picos[0]['fecha']}, +{picos[0]['dem'] - picos[0]['prod']:.0f} t) ✓"
        )

    # --- Insumo de eta_estimada -------------------------------------------
    faltan_mediana = []
    for pid, _, _, _ in K.PLANTAS:
        n = q(
            """SELECT COUNT(*) AS n FROM despachos d
                 JOIN pedidos p ON p.numero = d.pedido_numero
                WHERE p.planta_id = ? AND d.hora_cargue_real IS NOT NULL""",
            (pid,),
        )[0]["n"]
        if n < 5:
            faltan_mediana.append(f"{pid}={n}")
    if faltan_mediana:
        fallos.append(
            "Plantas sin 5 despachos cerrados para la mediana de cargue "
            "(eta_estimada devolvería null): " + ", ".join(faltan_mediana)
        )
    else:
        print(f"{ok} las 5 plantas tienen ≥5 despachos cerrados · eta_estimada calculable")

    con.close()

    if fallos:
        print("\n✕ La base NO es válida para las preguntas de demo:\n", file=sys.stderr)
        for f in fallos:
            print(f"  · {f}", file=sys.stderr)
        print(
            "\n  Revisa backend/db/seed.py. No arranques el laboratorio con esta "
            "base: las cinco preguntas de la demo fallarían en clase.\n",
            file=sys.stderr,
        )
        return False

    print("→ Base de datos válida para las 5 preguntas de demo.")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Genera bios_ops.db con datos sintéticos deterministas."
    )
    ap.add_argument(
        "--recrear",
        action="store_true",
        help="Borra y regenera la base desde cero (idempotente).",
    )
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--fecha", type=str, default=None, help="YYYY-MM-DD")
    args = ap.parse_args(argv)

    semilla = args.semilla if args.semilla is not None else config.semilla_datos
    fecha_base = (
        datetime.strptime(args.fecha, "%Y-%m-%d").date()
        if args.fecha
        else config.fecha_base
    )
    ruta = config.ruta_db

    if ruta.exists() and not args.recrear:
        print(
            f"La base ya existe en {ruta}. Usa --recrear para regenerarla.",
            file=sys.stderr,
        )
        return 1

    print(f"Generando {ruta.name} · semilla={semilla} · fecha de referencia={fecha_base}")
    conteos = construir(ruta, semilla, fecha_base)
    return 0 if verificar(ruta, conteos, fecha_base) else 1


if __name__ == "__main__":
    raise SystemExit(main())
