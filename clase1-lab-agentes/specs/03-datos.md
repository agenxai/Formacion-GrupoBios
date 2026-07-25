# 03 · Modelo de datos

## Naturaleza de los datos

> **Aviso que DEBE aparecer en el README, en el tablero y en la primera celda del
> notebook:**
>
> Todos los datos de `bios_ops.db` son **sintéticos**, generados por
> `backend/db/seed.py`. Los nombres de plantas, productos, equipos y clientes son
> **ficticios** y no representan la red de operaciones, los proveedores ni la
> cartera de clientes de Grupo Bios. Ningún dato real de la compañía se procesa en
> esta sesión.

La razón es operativa, no ceremonial: el laboratorio envía el contenido de las tools
a un proveedor externo de LLM. Hacerlo con datos productivos exige antes definir
contrato de tratamiento, clasificación de la información y controles de retención —
trabajo que corresponde a las sesiones 2 y 7. La Sesión 1 no debe normalizar esa
práctica.

Los nombres de municipio se eligen reales para que el contexto resulte familiar, con
la advertencia explícita de que la asignación planta↔municipio es inventada.

## Esquema

Once tablas. El criterio: las mínimas para que un agente **necesite encadenar varias
consultas** — si una sola tabla responde todo, N4 no se distingue de N3.

> **Nota de implementación.** La versión inicial de esta spec listaba diez tablas y las
> llamaba "nueve". Al construir se agregó una más, `formulas`, con la participación de
> cada materia prima en cada producto. Razón: la pregunta insignia compara toneladas de
> MATERIA PRIMA contra toneladas de PRODUCTO, y sin esa tabla la conversión de unidades
> la tendría que improvisar el modelo. Un laboratorio cuya tesis es que inventar datos
> operativos es el problema no puede sostener su demo insignia sobre una conversión
> inventada. Con la tabla, la conversión la hace la tool y queda auditable — el mismo
> principio que esta spec ya exigía para `tendencia`.

```sql
CREATE TABLE plantas (
  id            TEXT PRIMARY KEY,      -- 'PL-ITG'
  nombre        TEXT NOT NULL,         -- 'Planta Itagüí'
  municipio     TEXT NOT NULL,
  capacidad_ton_dia  REAL NOT NULL,
  activa        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE materias_primas (
  id            TEXT PRIMARY KEY,      -- 'MP-MAIZ'
  nombre        TEXT NOT NULL,         -- 'Maíz amarillo'
  unidad        TEXT NOT NULL DEFAULT 'ton',
  dias_lead_time INTEGER NOT NULL      -- para que Compras tenga qué razonar
);

CREATE TABLE inventario_planta (
  planta_id        TEXT NOT NULL REFERENCES plantas(id),
  materia_prima_id TEXT NOT NULL REFERENCES materias_primas(id),
  fecha_corte      TEXT NOT NULL,      -- ISO-8601
  cantidad_ton     REAL NOT NULL,
  stock_minimo_ton REAL NOT NULL,
  PRIMARY KEY (planta_id, materia_prima_id, fecha_corte)
);

CREATE TABLE demanda_historica (
  planta_id     TEXT NOT NULL REFERENCES plantas(id),
  fecha         TEXT NOT NULL,
  producto      TEXT NOT NULL,
  toneladas     REAL NOT NULL,
  PRIMARY KEY (planta_id, fecha, producto)
);

CREATE TABLE produccion_diaria (
  planta_id     TEXT NOT NULL REFERENCES plantas(id),
  fecha         TEXT NOT NULL,
  toneladas     REAL NOT NULL,
  paradas_min   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (planta_id, fecha)
);

CREATE TABLE equipos (
  id            TEXT PRIMARY KEY,      -- 'EQ-ITG-MOL-01'
  planta_id     TEXT NOT NULL REFERENCES plantas(id),
  tipo          TEXT NOT NULL,         -- 'Molino' | 'Peletizadora' | ...
  criticidad    TEXT NOT NULL,         -- 'alta' | 'media' | 'baja'
  fecha_instalacion TEXT NOT NULL
);

CREATE TABLE ordenes_mantenimiento (
  id            TEXT PRIMARY KEY,      -- 'OM-000123'
  equipo_id     TEXT NOT NULL REFERENCES equipos(id),
  fecha_apertura TEXT NOT NULL,
  fecha_cierre  TEXT,
  tipo          TEXT NOT NULL,         -- 'correctivo' | 'preventivo' | 'predictivo'
  causa         TEXT,
  horas_paro    REAL NOT NULL DEFAULT 0,
  costo_cop     REAL NOT NULL DEFAULT 0
);

CREATE TABLE lecturas_sensor (
  equipo_id     TEXT NOT NULL REFERENCES equipos(id),
  ts            TEXT NOT NULL,
  variable      TEXT NOT NULL,         -- 'vibracion_mm_s' | 'temperatura_c' | 'amperaje_a'
  valor         REAL NOT NULL,
  PRIMARY KEY (equipo_id, ts, variable)
);

CREATE TABLE pedidos (
  numero        TEXT PRIMARY KEY,      -- 'PD-24-00871'
  cliente       TEXT NOT NULL,         -- ficticio: 'Avícola El Roble'
  planta_id     TEXT NOT NULL REFERENCES plantas(id),
  producto      TEXT NOT NULL,
  toneladas     REAL NOT NULL,
  fecha_pedido  TEXT NOT NULL,
  fecha_promesa TEXT NOT NULL,
  estado        TEXT NOT NULL          -- ver máquina de estados abajo
);

CREATE TABLE despachos (
  id            TEXT PRIMARY KEY,
  pedido_numero TEXT NOT NULL REFERENCES pedidos(numero),
  placa         TEXT NOT NULL,         -- ficticia
  turno_muelle  INTEGER,               -- posición en la cola
  hora_asignada TEXT,
  hora_cargue_real TEXT,
  estado        TEXT NOT NULL
);
```

### Máquina de estados de `pedidos`

Ordenada, porque de aquí sale la interfaz "tipo aeropuerto" del caso de Logística:

```
registrado → programado → en_produccion → listo_despacho
           → en_muelle → cargado → en_transito → entregado
                                              ↘ novedad
```

`estado_pedido` DEBE devolver, además del estado, **cuántos pasos faltan** y **qué
turno tiene** — es el equivalente al "su vuelo aborda por la puerta 12".

## Reglas del generador

`seed.py` DEBE ser determinista (`random.Random(SEMILLA_DATOS)`, ADR-005) y producir:

| Tabla | Volumen | Regla |
|---|---|---|
| `plantas` | 5 | Capacidades distintas entre 180 y 900 ton/día |
| `materias_primas` | 8 | Maíz, soya, torta de soya, salvado, aceite, premezcla, carbonato, metionina |
| `inventario_planta` | 5 × 8 × 30 días | Camino aleatorio con consumo; **al menos una planta bajo stock mínimo** |
| `demanda_historica` | 5 × 180 días × 3 productos | Tendencia + estacionalidad semanal + ruido |
| `produccion_diaria` | 5 × 180 días | Correlacionada con demanda, con paradas ocasionales |
| `equipos` | 4 por planta = 20 | Mezcla de tipos y criticidades |
| `ordenes_mantenimiento` | ~200 | **Un equipo con patrón de falla recurrente claro** |
| `lecturas_sensor` | 20 equipos × 30 días × 4/día × 3 vars | Vibración creciente en el equipo problemático |
| `pedidos` | ~150 | Distribuidos por todos los estados |
| `despachos` | ~90 | Cola de muelle con turnos consecutivos por planta |

### Anomalías plantadas a propósito

El dataset DEBE contener hallazgos concretos, para que las preguntas de demo tengan
una respuesta correcta y verificable en lugar de un "todo está bien":

1. **Una planta bajo stock mínimo de maíz**, con demanda proyectada que no alcanza a
   cubrir. → Obliga a encadenar `consultar_inventario` + `consultar_demanda`: la
   pregunta insignia de N4.
2. **Un equipo con vibración en ascenso monótono** y tres correctivos en 60 días. →
   El caso de Mantenimiento; `historial_fallas` + `lecturas_sensor`.
3. **Un pedido atascado en `en_muelle`** detrás de una cola de 6 turnos. → El caso de
   Logística.
4. **Un pico de demanda no cubierto** por la producción del mismo período. → El caso
   de Producción/TD.

Estas cuatro anomalías son el guion de las preguntas precargadas del tablero
(spec 07) y su respuesta esperada es un criterio de aceptación (spec 05).

### Constantes garantizadas — contrato con las preguntas de demo

**Requisito crítico.** Las preguntas precargadas del tablero (spec 07) y las demos de
la spec 05 contienen identificadores literales. Si el generador produce otros, **las
cinco preguntas de la demo dejan de funcionar** y `estado_pedido` responde «no encontré
ese pedido» en medio de la clase.

Por lo tanto, `seed.py` **DEBE** producir exactamente estas entidades, con estos
identificadores, y no como resultado del azar sino como valores fijados:

```python
# backend/db/constantes.py — importado por seed.py y por el catálogo de preguntas

PLANTAS = [
    ("PL-ITG", "Planta Itagüí",     "Itagüí",     620.0),
    ("PL-BUG", "Planta Buga",       "Guadalajara de Buga", 900.0),
    ("PL-MOS", "Planta Mosquera",   "Mosquera",   480.0),
    ("PL-BAQ", "Planta Barranquilla","Barranquilla", 350.0),
    ("PL-PAL", "Planta Palmira",    "Palmira",    180.0),
]

# Anomalía 1 — inventario bajo mínimo, no cubre la demanda de la semana
PLANTA_DEFICIT      = "PL-ITG"
MATERIA_DEFICIT     = "MP-MAIZ"        # 'Maíz amarillo'

# Anomalía 2 — vibración en ascenso monótono + 3 correctivos en 60 días
EQUIPO_EN_RIESGO    = "EQ-ITG-MOL-01"  # Molino, criticidad alta, planta Itagüí

# Anomalía 3 — pedido atascado en 'en_muelle' detrás de 6 turnos
PEDIDO_ATASCADO     = "PD-24-00871"
PLANTA_PEDIDO       = "PL-ITG"         # mismo sitio: habilita la pregunta cruzada de N5

# Anomalía 4 — día con demanda por encima de la producción
PLANTA_PICO         = "PL-BUG"
```

`PEDIDO_ATASCADO` y `EQUIPO_EN_RIESGO` DEBEN pertenecer a la **misma planta**: es lo
que hace posible la pregunta cruzada de N5 («¿el retraso es por materia prima o por
equipos?»), donde el supervisor consulta dos dominios sobre un mismo sitio y concluye
que la causa es el inventario, no los equipos.

> **Aviso de ficción (spec 03, apertura):** los municipios son reales; la asignación
> planta↔municipio es **inventada** y no corresponde a la red de operaciones de Grupo
> Bios.

### Verificación del contrato de datos

`seed.py` DEBE terminar ejecutando una autocomprobación que falle el build si alguna
constante no quedó en la base:

```
$ python -m backend.db.seed --recrear
✓ 11 tablas · 12.497 filas
✓ PL-ITG existe · inventario MP-MAIZ = 320.0 t · mínimo = 1190.0 t · bajo mínimo ✓
✓ requerimiento de 7 días = 1651.9 t · no alcanza, faltan 1331.9 t ✓
✓ EQ-ITG-MOL-01 existe · 3 correctivos en 60 d · tendencia vibración = +0.42 mm/s·día ✓
✓ PD-24-00871 existe · estado = en_muelle · posición en cola = 6 ✓
✓ PL-BUG tiene 1 día con demanda > producción (2026-06-18, +73 t) ✓
→ Base de datos válida para las 5 preguntas de demo.
```

Si esto no pasa, la base no sirve y el laboratorio no debe arrancar. Es la clase de
fallo que se descubre en el minuto 12 de la clase si no se verifica antes.

### Fechas

El generador DEBE anclar los datos a una **fecha de referencia fija**
(`FECHA_REFERENCIA`, por defecto la del día de la sesión) y generar hacia atrás. Los
datos así no "envejecen" entre la prueba y la clase, y expresiones como "esta semana"
en las preguntas siguen siendo válidas.

## Ubicación y ciclo de vida

- Se genera en el `docker build` → la imagen ya trae la base lista. Arrancar el
  laboratorio no requiere red para los datos.
- `bios_ops.db` DEBE estar en `.gitignore`. Se versiona el generador, no el binario.
- `python -m backend.db.seed --recrear` DEBE regenerarla de cero, idempotente.
- Se abre en **modo solo lectura** desde las tools. Un agente no escribe en la base
  en esta sesión (ver spec 04, `sql_seguro`).
