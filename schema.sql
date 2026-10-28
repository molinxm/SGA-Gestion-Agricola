-- ============================================================================
--  SGA · Sistema de Gestión Agrícola
--  Esquema para la base de datos REAL del proyecto: gestion_agricola
--  MySQL 8 / MariaDB 10.4+  ·  Proyecto académico - UNIMINUTO
--
--  IMPORTANTE
--  ----------
--  Este archivo es IDEMPOTENTE y NO DESTRUCTIVO:
--    * No contiene sentencias DROP ni TRUNCATE.
--    * Todas las tablas se crean con "CREATE TABLE IF NOT EXISTS".
--  Se puede ejecutar tantas veces como haga falta (flask --app app init-db)
--  sin perder la información que ya existe en tu base de datos.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS gestion_agricola
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gestion_agricola;

-- ---------------------------------------------------------------------------
--  Tabla: Trabajadores  (personal de campo)
--  Columnas base del proyecto + columnas que consume el frontend.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trabajadores (
    id_trabajador  INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    documento      VARCHAR(30)           DEFAULT NULL,
    telefono       VARCHAR(30)           DEFAULT NULL,
    email          VARCHAR(150)          DEFAULT NULL,
    cargo          VARCHAR(80)  NOT NULL DEFAULT 'Operario Agrícola',
    estado         VARCHAR(20)  NOT NULL DEFAULT 'Activo',
    fecha_ingreso  DATE                  DEFAULT NULL,
    observaciones  VARCHAR(255)          DEFAULT NULL,
    INDEX idx_trabajadores_estado (estado),
    INDEX idx_trabajadores_cargo  (cargo)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
--  Tabla: Tareas  (labores agrícolas asignadas)
--  estado_tarea guarda los valores en MAYÚSCULAS:
--      PENDIENTE | EN PROCESO | COMPLETADA | INCOMPLETA
--  El backend los traduce a su forma presentable para la interfaz.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tareas (
    id_tarea          INT AUTO_INCREMENT PRIMARY KEY,
    titulo            VARCHAR(150) NOT NULL,
    descripcion       TEXT                  DEFAULT NULL,
    id_trabajador     INT                   DEFAULT NULL,
    lote              VARCHAR(60)           DEFAULT NULL,
    cultivo           VARCHAR(80)           DEFAULT NULL,
    prioridad         VARCHAR(10)  NOT NULL DEFAULT 'Media',
    estado_tarea      VARCHAR(20)  NOT NULL DEFAULT 'PENDIENTE',
    fecha_inicio      DATE                  DEFAULT NULL,
    fecha_limite      DATE                  DEFAULT NULL,
    fecha_completada  DATE                  DEFAULT NULL,
    observaciones     VARCHAR(255)          DEFAULT NULL,
    -- Si se elimina el trabajador, la tarea se conserva como histórica
    CONSTRAINT fk_tareas_trabajador
        FOREIGN KEY (id_trabajador) REFERENCES trabajadores (id_trabajador)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    INDEX idx_tareas_estado    (estado_tarea),
    INDEX idx_tareas_prioridad (prioridad),
    INDEX idx_tareas_limite    (fecha_limite)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
--  Tabla: usuarios  (acceso al sistema con RBAC)
--  rol: admin | supervisor | operario
--  Las cuentas iniciales se crean con:  flask --app app init-db
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    email          VARCHAR(150) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    telefono       VARCHAR(30)           DEFAULT NULL,
    rol            ENUM('admin', 'supervisor', 'operario') NOT NULL DEFAULT 'operario',
    activo         TINYINT(1)   NOT NULL DEFAULT 1,
    operario_id    INT                   DEFAULT NULL,
    creado_en      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usuarios_rol (rol)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
