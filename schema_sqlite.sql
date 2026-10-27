-- ============================================================================
--  SGA · Sistema de Gestión Agrícola
--  Esquema compatible con SQLite (para despliegue gratuito)
-- ============================================================================

-- ---------------------------------------------------------------------------
--  Tabla: trabajadores
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trabajadores (
    id_trabajador  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL,
    documento      TEXT          DEFAULT NULL,
    telefono       TEXT          DEFAULT NULL,
    email          TEXT          DEFAULT NULL,
    cargo          TEXT NOT NULL DEFAULT 'Operario Agrícola',
    estado         TEXT NOT NULL DEFAULT 'Activo',
    fecha_ingreso  DATE          DEFAULT NULL,
    observaciones  TEXT          DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_trabajadores_estado ON trabajadores (estado);
CREATE INDEX IF NOT EXISTS idx_trabajadores_cargo ON trabajadores (cargo);

-- ---------------------------------------------------------------------------
--  Tabla: tareas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tareas (
    id_tarea          INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo            TEXT NOT NULL,
    descripcion       TEXT          DEFAULT NULL,
    id_trabajador     INTEGER       DEFAULT NULL,
    lote              TEXT          DEFAULT NULL,
    cultivo           TEXT          DEFAULT NULL,
    prioridad         TEXT NOT NULL DEFAULT 'Media',
    estado_tarea      TEXT NOT NULL DEFAULT 'PENDIENTE',
    fecha_inicio      DATE          DEFAULT NULL,
    fecha_limite      DATE          DEFAULT NULL,
    fecha_completada  DATE          DEFAULT NULL,
    observaciones     TEXT          DEFAULT NULL,
    FOREIGN KEY (id_trabajador) REFERENCES trabajadores (id_trabajador)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tareas_estado ON tareas (estado_tarea);
CREATE INDEX IF NOT EXISTS idx_tareas_prioridad ON tareas (prioridad);
CREATE INDEX IF NOT EXISTS idx_tareas_limite ON tareas (fecha_limite);

-- ---------------------------------------------------------------------------
--  Tabla: usuarios
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    rol            TEXT NOT NULL DEFAULT 'operario',
    activo         INTEGER NOT NULL DEFAULT 1,
    operario_id    INTEGER          DEFAULT NULL,
    creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios (rol);
