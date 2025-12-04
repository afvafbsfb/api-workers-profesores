-- ================================================================
-- EJEMPLOS DE USO: TB_FAMILIAS_ALUMNOS
-- ================================================================
-- Este archivo muestra cómo usar la tabla familias_alumnos
-- con clave primaria compuesta (id_familia_alumno, id_alumno)
-- ================================================================

-- Supongamos que tenemos estos alumnos matriculados:
-- Alumno(id=101, nombre='Juan Pérez García')
-- Alumno(id=102, nombre='María Pérez García')
-- Alumno(id=103, nombre='Pedro Pérez García')
-- Alumno(id=201, nombre='Ana López Martín')
-- Alumno(id=202, nombre='Luis López Martín')

-- ================================================================
-- FAMILIA 1: Los Pérez (3 hermanos)
-- ================================================================
INSERT INTO familias_alumnos (id_familia_alumno, id_alumno, relacion_familiar) VALUES
(1, 101, 'Hermano'),
(1, 102, 'Hermana'),
(1, 103, 'Hermano');

-- ================================================================
-- FAMILIA 2: Los López (2 hermanos)
-- ================================================================
INSERT INTO familias_alumnos (id_familia_alumno, id_alumno, relacion_familiar) VALUES
(2, 201, 'Hermana'),
(2, 202, 'Hermano');

-- ================================================================
-- CONSULTAS ÚTILES
-- ================================================================

-- 1. Ver todas las familias con sus miembros
SELECT 
    f.id_familia_alumno,
    GROUP_CONCAT(a.nombre ORDER BY a.nombre SEPARATOR ', ') as miembros_familia,
    COUNT(*) as num_hermanos
FROM familias_alumnos f
INNER JOIN Alumno a ON f.id_alumno = a.id
GROUP BY f.id_familia_alumno;

-- Resultado esperado:
-- id_familia_alumno | miembros_familia                                    | num_hermanos
-- ------------------|-----------------------------------------------------|-------------
--         1         | Juan Pérez García, María Pérez García, Pedro Pérez  |      3
--         2         | Ana López Martín, Luis López Martín                 |      2


-- 2. Ver los hermanos de un alumno específico (ej: Juan con id=101)
SELECT 
    a2.id,
    a2.nombre,
    f2.relacion_familiar
FROM familias_alumnos f1
INNER JOIN familias_alumnos f2 ON f1.id_familia_alumno = f2.id_familia_alumno
INNER JOIN Alumno a2 ON f2.id_alumno = a2.id
WHERE f1.id_alumno = 101
  AND f2.id_alumno != 101;  -- Excluir al propio alumno

-- Resultado esperado para Juan (id=101):
-- id  | nombre              | relacion_familiar
-- ----|---------------------|------------------
-- 102 | María Pérez García  | Hermana
-- 103 | Pedro Pérez García  | Hermano


-- 3. Calcular descuentos familiares (ejemplo)
-- Si el descuento es 10% por cada hermano adicional después del primero:
SELECT 
    f.id_familia_alumno,
    a.id as alumno_id,
    a.nombre,
    COUNT(*) OVER (PARTITION BY f.id_familia_alumno) - 1 as num_hermanos_adicionales,
    (COUNT(*) OVER (PARTITION BY f.id_familia_alumno) - 1) * 10 as porcentaje_descuento
FROM familias_alumnos f
INNER JOIN Alumno a ON f.id_alumno = a.id
ORDER BY f.id_familia_alumno, a.nombre;

-- Resultado esperado:
-- id_familia | alumno_id | nombre              | num_hermanos_adicionales | porcentaje_descuento
-- -----------|-----------|---------------------|--------------------------|---------------------
--     1      |    101    | Juan Pérez García   |            2             |         20
--     1      |    102    | María Pérez García  |            2             |         20
--     1      |    103    | Pedro Pérez García  |            2             |         20
--     2      |    201    | Ana López Martín    |            1             |         10
--     2      |    202    | Luis López Martín   |            1             |         10


-- ================================================================
-- VALIDACIONES Y REGLAS DE NEGOCIO
-- ================================================================

-- REGLA 1: Un alumno NO puede pertenecer a múltiples familias
-- Esto se previene con la PK compuesta (id_familia_alumno, id_alumno)
-- El siguiente INSERT fallaría con error de duplicado:
-- INSERT INTO familias_alumnos (id_familia_alumno, id_alumno, relacion_familiar) VALUES
-- (3, 101, 'Primo');  -- ERROR: Duplicate entry '3-101' for key 'PRIMARY'


-- REGLA 2: Para generar nuevos id_familia_alumno automáticamente:
-- Opción A: Usar MAX + 1
INSERT INTO familias_alumnos (id_familia_alumno, id_alumno, relacion_familiar) 
SELECT 
    COALESCE(MAX(id_familia_alumno), 0) + 1,
    301,  -- id del nuevo alumno
    'Hermano'
FROM familias_alumnos;

-- Opción B: Usar una secuencia/tabla auxiliar
CREATE TABLE IF NOT EXISTS familia_sequence (
    next_id INT NOT NULL DEFAULT 1
);

INSERT INTO familia_sequence (next_id) VALUES (1);

-- Al crear una nueva familia:
UPDATE familia_sequence SET next_id = next_id + 1;
SELECT next_id - 1 as nuevo_id_familia FROM familia_sequence;


-- ================================================================
-- LIMPIEZA (solo para testing)
-- ================================================================
-- DELETE FROM familias_alumnos WHERE id_familia_alumno IN (1, 2);
