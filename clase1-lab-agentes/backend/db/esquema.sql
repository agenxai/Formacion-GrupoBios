-- =============================================================================
--  bios_ops.db — esquema del laboratorio "Niveles de Agencia"
--  Spec 03. Datos 100% SINTÉTICOS generados por backend/db/seed.py.
--
--  Los nombres de plantas, productos, equipos y clientes son FICTICIOS y no
--  representan la red de operaciones, los proveedores ni la cartera de clientes
--  de Grupo Bios. Los municipios son reales; la asignación planta↔municipio es
--  inventada.
--
--  Criterio del diseño: las tablas mínimas para que un agente NECESITE encadenar
--  varias consultas. Si una sola tabla respondiera todo, N4 no se distinguiría
--  de N3.
-- =============================================================================

DROP TABLE IF EXISTS despachos;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS lecturas_sensor;
DROP TABLE IF EXISTS ordenes_mantenimiento;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS produccion_diaria;
DROP TABLE IF EXISTS demanda_historica;
DROP TABLE IF EXISTS formulas;
DROP TABLE IF EXISTS inventario_planta;
DROP TABLE IF EXISTS materias_primas;
DROP TABLE IF EXISTS plantas;

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

-- Participación de cada materia prima en cada producto terminado.
--
-- Añadida sobre las nueve tablas de la spec 03. Razón: la pregunta insignia
-- («¿cuánto maíz queda y me alcanza para la demanda de esta semana?») compara
-- toneladas de MATERIA PRIMA contra toneladas de PRODUCTO. Sin esta tabla, la
-- comparación es una confusión de unidades — y el laboratorio cuyo tema es que
-- inventar datos operativos es el problema no puede sostener su demo insignia
-- sobre una conversión inventada por el modelo.
--
-- Con la tabla, la conversión la hace la tool y queda auditable. Es el mismo
-- principio que la spec 04 exige para `tendencia`: la tool calcula, el modelo
-- razona.
CREATE TABLE formulas (
  producto         TEXT NOT NULL,
  materia_prima_id TEXT NOT NULL REFERENCES materias_primas(id),
  inclusion_pct    REAL NOT NULL,      -- % en peso; suma 100 por producto
  PRIMARY KEY (producto, materia_prima_id)
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
  estado        TEXT NOT NULL          -- máquina de estados: ver constantes.FLUJO_PEDIDO
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

-- Índices de las rutas de consulta que usan las tools. Sin ellos, la consulta de
-- lecturas de sensor sobre 7.200 filas se nota en la demo.
CREATE INDEX idx_inventario_planta   ON inventario_planta(planta_id, materia_prima_id, fecha_corte);
CREATE INDEX idx_demanda_planta      ON demanda_historica(planta_id, fecha);
CREATE INDEX idx_produccion_planta   ON produccion_diaria(planta_id, fecha);
CREATE INDEX idx_equipos_planta      ON equipos(planta_id);
CREATE INDEX idx_ordenes_equipo      ON ordenes_mantenimiento(equipo_id, fecha_apertura);
CREATE INDEX idx_lecturas_equipo_var ON lecturas_sensor(equipo_id, variable, ts);
CREATE INDEX idx_pedidos_planta      ON pedidos(planta_id, estado);
CREATE INDEX idx_despachos_pedido    ON despachos(pedido_numero);
