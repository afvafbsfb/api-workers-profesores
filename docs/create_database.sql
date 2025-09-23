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
    FOREIGN KEY (academia_id) REFERENCES Academia(id)
);

-- Tabla Curso (actualizada)
CREATE TABLE Curso (
    id INT AUTO_INCREMENT PRIMARY KEY,
    academia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
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

-- rol_id	recurso	  accion
-- 1	       academia	   crear
-- 1	       academia	eliminar
-- 1	       academia	actualizar
-- 1	       academia	leer
-- 2	       curso	crear
-- 2	       curso	eliminar
-- 2	       curso	actualizar
-- 2	       curso	leer
-- 3	       sesion	leer
-- 3	       sesion	actualizar

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

CREATE TABLE PermisosRol (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rol_id INT NOT NULL,
    recurso ENUM('academia', 'tarifa', 'curso', 'aula', 'horario_curso', 'alumno', 'inscripcion', 'rol_usuario', 'usuario', 'permisosrol', 'sesion', 'descuentos_tarifa', 'familias_alumnos', 'anotaciones_alumno_sesion', 'pago', 'trabajador_virtual', '*') NOT NULL,
    accion ENUM('crear', 'leer', 'actualizar', 'eliminar', '*') NOT NULL,
    UNIQUE (rol_id, recurso, accion),
    FOREIGN KEY (rol_id) REFERENCES Rol_Usuario(id)
);


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
    notas_sesion TEXT,
    notas_materia TEXT,
    FOREIGN KEY (curso_profesor_id) REFERENCES Curso_Profesores(id),
    FOREIGN KEY (aula_id) REFERENCES Aula(id)
);

-- Tabla Descuentos_tarifa (nueva)
CREATE TABLE Descuentos_tarifa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tarifa_id INT NOT NULL,
    tipo_descuento CHAR(1) NOT NULL,
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
    alumno_id INT NOT NULL,
    tipo_anotacion ENUM('Ausencia', 'Evaluacion', 'Comportamiento') NOT NULL,
    texto VARCHAR(255),
    FOREIGN KEY (sesion_id) REFERENCES Sesion(id),
    FOREIGN KEY (alumno_id) REFERENCES Alumno(id)
);

-- Tabla Pago
CREATE TABLE Pago (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inscripcion_id INT NOT NULL,
    fecha_pago DATE NOT NULL,
    periodo VARCHAR(50) NOT NULL,
    importe_corresponde_pagar FLOAT NOT NULL,
    importe_pagado FLOAT NOT NULL,
    metodo_pago VARCHAR(50) NOT NULL,
    FOREIGN KEY (inscripcion_id) REFERENCES Inscripcion(id)
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
(1, 'System_Admin'),
(2, 'Company_Admin'),
(3, 'Staff_profesores');

-- Inserciones en la tabla PermisosRol
-- Permisos para System_Admin (ID: 1)
INSERT INTO PermisosRol (rol_id, recurso, accion) VALUES
(1, '*', '*');

-- Permisos para Company_Admin (ID: 2)
INSERT INTO PermisosRol (rol_id, recurso, accion) VALUES
(2, 'academia', 'leer'),
(2, 'academia', 'actualizar'),
(2, 'tarifa', 'crear'),
(2, 'tarifa', 'leer'),
(2, 'tarifa', 'actualizar'),
(2, 'tarifa', 'eliminar'),
(2, 'curso', 'crear'),
(2, 'curso', 'leer'),
(2, 'curso', 'actualizar'),
(2, 'curso', 'eliminar'),
(2, 'aula', 'crear'),
(2, 'aula', 'leer'),
(2, 'aula', 'actualizar'),
(2, 'aula', 'eliminar'),
(2, 'horario_curso', 'crear'),
(2, 'horario_curso', 'leer'),
(2, 'horario_curso', 'actualizar'),
(2, 'horario_curso', 'eliminar'),
(2, 'alumno', 'crear'),
(2, 'alumno', 'leer'),
(2, 'alumno', 'actualizar'),
(2, 'alumno', 'eliminar'),
(2, 'inscripcion', 'crear'),
(2, 'inscripcion', 'leer'),
(2, 'inscripcion', 'actualizar'),
(2, 'inscripcion', 'eliminar'),
(2, 'rol_usuario', 'leer'),
(2, 'usuario', 'crear'),
(2, 'usuario', 'leer'),
(2, 'usuario', 'actualizar'),
(2, 'usuario', 'eliminar'),
(2, 'permisosrol', 'leer'),
(2, 'sesion', 'crear'),
(2, 'sesion', 'leer'),
(2, 'sesion', 'actualizar'),
(2, 'sesion', 'eliminar'),
(2, 'descuentos_tarifa', 'crear'),
(2, 'descuentos_tarifa', 'leer'),
(2, 'descuentos_tarifa', 'actualizar'),
(2, 'descuentos_tarifa', 'eliminar'),
(2, 'familias_alumnos', 'crear'),
(2, 'familias_alumnos', 'leer'),
(2, 'familias_alumnos', 'actualizar'),
(2, 'familias_alumnos', 'eliminar'),
(2, 'anotaciones_alumno_sesion', 'crear'),
(2, 'anotaciones_alumno_sesion', 'leer'),
(2, 'anotaciones_alumno_sesion', 'actualizar'),
(2, 'anotaciones_alumno_sesion', 'eliminar'),
(2, 'pago', 'crear'),
(2, 'pago', 'leer'),
(2, 'pago', 'actualizar'),
(2, 'pago', 'eliminar'),
(2, 'trabajador_virtual', 'leer'),
(2, 'trabajador_virtual', 'actualizar');

-- Permisos para Staff_profesores (ID: 3)
INSERT INTO PermisosRol (rol_id, recurso, accion) VALUES
(3, 'curso', 'leer'),
(3, 'horario_curso', 'leer'),
(3, 'alumno', 'leer'),
(3, 'sesion', 'crear'),
(3, 'sesion', 'leer'),
(3, 'sesion', 'actualizar'),
(3, 'anotaciones_alumno_sesion', 'crear'),
(3, 'anotaciones_alumno_sesion', 'leer'),
(3, 'anotaciones_alumno_sesion', 'actualizar'),
(3, 'anotaciones_alumno_sesion', 'eliminar'),
(3, 'trabajador_virtual', 'leer');

-- Crear usuario administrador de la plataforma para pruebas
INSERT INTO Usuario (id, academia_id, nombre, email, password, rol_id) VALUES
(1, NULL, 'ADMIN', 'afvafbsfb@gmail.com', 'ADMIN', 1);