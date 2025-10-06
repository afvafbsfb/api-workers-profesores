-- IMPORTANTE: Este archivo debe mantenerse en sincronía con models.py.
-- Siempre que se realicen cambios en las tablas, campos, relaciones o formatos de campos,
-- asegúrate de actualizar ambos archivos para evitar inconsistencias.

DROP DATABASE IF EXISTS api_workers;

-- Script para crear la base de datos y las tablas actualizadas

CREATE DATABASE IF NOT EXISTS api_workers CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE api_workers;

-- Tabla Academia (antes Empresa)
CREATE TABLE Academia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

-- Tabla Tarifa
CREATE TABLE Tarifa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    descripcion VARCHAR(255),
    precio_base FLOAT NOT NULL,
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_baja DATETIME,
    fecha_ultima_modificacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (academia_id) REFERENCES Academia(id)
);

-- Tabla Curso (actualizada)
CREATE TABLE Curso (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    anio_academico VARCHAR(20) NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    acepta_nuevos_alumnos BOOLEAN NOT NULL,
    capacidad_maxima INT NOT NULL,
    tarifa_id INT NOT NULL,
    tipo_alumno ENUM('Infantil', 'Juvenil', 'Adultos') NOT NULL,
    estado ENUM('Activo', 'Inactivo', 'Finalizado') NOT NULL,
     -- Nuevo campo para tipo de alumno
    FOREIGN KEY (academia_id) REFERENCES Academia(id),
    FOREIGN KEY (tarifa_id) REFERENCES Tarifa(id)
);

-- Tabla Aula
CREATE TABLE Aula (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    capacidad_maxima INT NOT NULL,
    FOREIGN KEY (academia_id) REFERENCES Academia(id)
);

-- Tabla HorarioCurso
CREATE TABLE HorarioCurso (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curso_id INT NOT NULL,
    aula_id INT NOT NULL,
    dia_semana VARCHAR(20) NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (aula_id) REFERENCES Aula(id)
);

-- Tabla Alumno
CREATE TABLE Alumno (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    dni VARCHAR(20) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    nombre_tutor VARCHAR(100),
    relaccion_tutor_alumno VARCHAR(100),
    telefono_tutor VARCHAR(20),
    email_tutor VARCHAR(120),
    FOREIGN KEY (academia_id) REFERENCES Academia(id)
);

-- Tabla Inscripcion
CREATE TABLE Inscripcion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alumno_id INT NOT NULL,
    curso_id INT NOT NULL,
    tarifa_id INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    motivo_baja VARCHAR(255),
    FOREIGN KEY (alumno_id) REFERENCES Alumno(id),
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (tarifa_id) REFERENCES Tarifa(id)
);

-- Tabla Rol_Usuario
CREATE TABLE Rol_Usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE -- Ejemplos: 'Admin_plataforma', 'Admin_academia', 'Profesor_academia'
);


-- Tabla Usuario
CREATE TABLE Usuario (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL,
    estado ENUM('Activo', 'Bloqueado', 'Baja') NOT NULL DEFAULT 'Activo',
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_baja DATETIME NULL,
    fecha_ultima_modificacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (academia_id) REFERENCES Academia(id),
    FOREIGN KEY (rol_id) REFERENCES Rol_Usuario(id)
);

-- Ensure email is indexed uniquely
CREATE UNIQUE INDEX idx_usuario_email ON Usuario(email);


-- === 1) HISTORIAL DE LOGIN/LOGOUT ===
CREATE TABLE IF NOT EXISTS UserLoginLog (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  login_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  logout_at DATETIME NULL,
  success BOOLEAN NOT NULL,
  fail_reason VARCHAR(100) NULL,           -- BAD_CREDENTIALS | LOCKED | MFA_FAIL | ...
  ip VARBINARY(16) NULL,                   -- IPv4/IPv6 con INET6_ATON/NTON a nivel app
  user_agent VARCHAR(255) NULL,
  device_id VARCHAR(100) NULL,             -- opcional
  client VARCHAR(50) NULL,                  -- web | android | ios | ...
  FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
  INDEX idx_ull_usuario_login (usuario_id, login_at),
  INDEX idx_ull_success_login (success, login_at)
) ENGINE=InnoDB;

-- === 2) REFRESH TOKENS (rotación y revocación) ===
CREATE TABLE IF NOT EXISTS RefreshToken (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL,            -- SHA-256 del refresh token (no guardar el token plano)
  issued_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL,            -- ahora() + 30 días, p. ej.
  revoked_at DATETIME NULL,
  replaced_by_id BIGINT NULL,              -- encadenar rotaciones
  ip VARBINARY(16) NULL,
  user_agent VARCHAR(255) NULL,
  device_id VARCHAR(100) NULL,
  scope VARCHAR(200) NULL,                 -- opcional (p. ej. "offline_access")
  FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
  FOREIGN KEY (replaced_by_id) REFERENCES RefreshToken(id),
  UNIQUE KEY uk_refreshtoken_hash (token_hash),
  INDEX idx_refreshtoken_usuario_exp (usuario_id, expires_at),
  INDEX idx_refreshtoken_revoked (revoked_at)
) ENGINE=InnoDB;

-- === 3) CONTROL GLOBAL DE REVOCACIÓN (token_version) & ANTI-FUERZA BRUTA ===
ALTER TABLE Usuario
  ADD COLUMN token_version INT NOT NULL DEFAULT 0,
  ADD COLUMN failed_login_count INT NOT NULL DEFAULT 0,
  ADD COLUMN last_failed_login_at DATETIME NULL,
  ADD COLUMN locked_until DATETIME NULL,
  ADD INDEX idx_usuario_token_version (token_version);

-- === 4) RECUPERACIÓN DE CONTRASEÑA (password reset) ===
CREATE TABLE IF NOT EXISTS PasswordResetToken (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  token_hash CHAR(64) NOT NULL,            -- SHA-256 del token de reset
  expires_at DATETIME NOT NULL,
  used_at DATETIME NULL,
  ip VARBINARY(16) NULL,
  user_agent VARCHAR(255) NULL,
  FOREIGN KEY (usuario_id) REFERENCES Usuario(id),
  UNIQUE KEY uk_pwdreset_hash (token_hash),
  INDEX idx_pwdreset_usuario_exp (usuario_id, expires_at)
) ENGINE=InnoDB;

-- Tabla Curso_Profesores (nueva)
CREATE TABLE Curso_Profesores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    curso_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_baja DATETIME NULL,
    fecha_ult_modificacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    motivo_baja VARCHAR(255),
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (usuario_id) REFERENCES Usuario(id)
);

-- Tabla Sesion (actualizada sin curso_id redundante)
CREATE TABLE Sesion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aula_id INT NOT NULL,
    curso_profesor_id INT NOT NULL,
    timestamp_alta DATETIME NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    timestamp_baja DATETIME,
    motivo_baja VARCHAR(255),
    notas_sesion TEXT,
    notas_materia TEXT,
    FOREIGN KEY (curso_profesor_id) REFERENCES Curso_Profesores(id),
    FOREIGN KEY (aula_id) REFERENCES Aula(id)
);

-- Tabla Descuentos_tarifa (nueva)
CREATE TABLE Descuentos_tarifa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tarifa_id INT NOT NULL,
    motivo_descuento CHAR(1) NOT NULL, -- 'F' por familiares en el centro, 'M' por periodo menor a 15 dias.
    tipo_descuento CHAR(1) NOT NULL, -- 'P' para porcentaje, 'F' para fijo
    porcentaje_descuento FLOAT,
    importe_descuento FLOAT,
    FOREIGN KEY (tarifa_id) REFERENCES Tarifa(id)
);

-- Tabla familias_alumnos (nueva)
CREATE TABLE familias_alumnos (
    id_familia_alumno INT AUTO_INCREMENT PRIMARY KEY,
    id_alumno1 INT NOT NULL,
    id_alumno2 INT NOT NULL,
    relacion_familiar VARCHAR(100) NOT NULL,
    FOREIGN KEY (id_alumno1) REFERENCES Alumno(id),
    FOREIGN KEY (id_alumno2) REFERENCES Alumno(id)
);

-- Tabla AnotacionesAlumnoSesion (antes AusenciaAlumnoSesion)
CREATE TABLE AnotacionesAlumnoSesion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sesion_id INT NOT NULL,
    inscripcion_id INT NOT NULL,
    curso_id INT NOT NULL,
    curso_profesor_id INT NOT NULL,
    alumno_id INT NOT NULL,
    tipo_anotacion ENUM('Ausencia', 'Evaluacion', 'Comportamiento') NOT NULL,
    texto VARCHAR(255),
    timestamp_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timestamp_baja DATETIME,
    motivo_baja VARCHAR(255),
    FOREIGN KEY (sesion_id) REFERENCES Sesion(id),
    FOREIGN KEY (alumno_id) REFERENCES Alumno(id),
    FOREIGN KEY (inscripcion_id) REFERENCES Inscripcion(id),
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (curso_profesor_id) REFERENCES Curso_Profesores(id)
);

-- Tabla Extractos (nueva)
CREATE TABLE Extractos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscripcion_id INT NOT NULL,
    curso_id INT NOT NULL,
    alumno_id INT NOT NULL,
    numero_extracto INT NOT NULL,
    saldo_ingreso_cuenta_anterior FLOAT,
    estado_liquidacion_extracto ENUM('1', '2') NOT NULL COMMENT '1: Pendiente de liquidación, 2: Liquidado',
    fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_ini_periodo DATE NOT NULL,
    fecha_fin_periodo DATE NOT NULL,
    id_dcto_tarifa_1 INT,
    motivo_dcto1 VARCHAR(255),
    tipo_dcto_1 CHAR(1),
    porcentaje_dcto_1 FLOAT,
    importe_descuento_1 FLOAT,
    id_dcto_tarifa_2 INT,
    motivo_dcto2 VARCHAR(255),
    tipo_dcto_2 CHAR(1),
    porcentaje_dcto_2 FLOAT,
    importe_descuento_2 FLOAT,
    id_dcto_tarifa_3 INT,
    motivo_dcto3 VARCHAR(255),
    tipo_dcto_3 CHAR(1),
    porcentaje_dcto_3 FLOAT,
    importe_descuento_3 FLOAT,
    importe_cuota FLOAT NOT NULL,
    total_descuentos FLOAT NOT NULL,
    importe_cuota_mensual_sin_descuentos FLOAT NOT NULL, -- cuota mensual sin descuentos
    importe_cuota_mensual_con_descuentos FLOAT NOT NULL, -- cuota mensual con descuentos
    importe_exceso_ingresos FLOAT,
    total_importe_a_cobrar FLOAT NOT NULL,
    FOREIGN KEY (inscripcion_id) REFERENCES Inscripcion(id),
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (alumno_id) REFERENCES Alumno(id)
);

-- Tabla Movimientos_Extracto (antes Pago)
CREATE TABLE Movimientos_Extracto (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscripcion_id INT NOT NULL,
    curso_id INT NOT NULL,
    alumno_id INT NOT NULL,
    extracto_id INT NOT NULL,
    fecha_movimiento DATE NOT NULL,
    tipo_movimiento ENUM('Ingreso', 'Anulacion_Ingreso') NOT NULL,
    estado_liquidacion_movimiento ENUM('1', '2') NOT NULL COMMENT '1: Pendiente, 2: Cobrado',
    importe FLOAT NOT NULL,
    descripcion_movimiento VARCHAR(255),
    metodo_pago VARCHAR(50) NOT NULL,
    indicador_movimiento_anulado ENUM('S', 'N') NOT NULL DEFAULT 'N' COMMENT 'S: Anulado, N: No Anulado',
    FOREIGN KEY (inscripcion_id) REFERENCES Inscripcion(id),
    FOREIGN KEY (curso_id) REFERENCES Curso(id),
    FOREIGN KEY (alumno_id) REFERENCES Alumno(id),
    FOREIGN KEY (extracto_id) REFERENCES Extractos(id)
);


-- Tabla TrabajadorVirtual (actualizada)
CREATE TABLE TrabajadorVirtual (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    foto VARCHAR(255), -- URL de la foto almacenada en un servidor de objetos
    descripcion TEXT,
    apikey VARCHAR(255),
    es_administrativo_virtual BOOLEAN NOT NULL, -- Indicador de administrativo virtual
    FOREIGN KEY (academia_id) REFERENCES Academia(id)
);

-- Inserciones en la tabla Rol_Usuario
INSERT INTO Rol_Usuario (id, nombre) VALUES
(1, 'Admin_plataforma'), 
(2, 'Admin_academia'),
(3, 'Profesor_academia');


