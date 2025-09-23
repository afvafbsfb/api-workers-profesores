# Estructura DDD del Proyecto

## Introducción
La estructura del proyecto sigue los principios de Domain-Driven Design (DDD), organizando el código en contextos delimitados (bounded contexts) para reflejar las responsabilidades del dominio. Cada contexto delimitado se divide en subcarpetas que representan diferentes capas y componentes del sistema.

## Dominio Principal
**Gestión de academias**: El sistema está enfocado en la gestión de academias, proporcionando herramientas para administrar usuarios, cursos, profesores, alumnos, pagos, y otros aspectos clave.

## Subdominios
1. **Gestión de Academias**: Administración general de las academias. Alta y baja de academias, consultas.
2. **Gestión de Usuarios**: Alta, baja, modificación, consulta, Autenticación, roles, permisos. Encargado de manejar los usuarios para una academia. Estos usuarios pueden ser administradores de la academia o profesores.  IMPORTANTE los usuarios administradores del sistema se dan de alta y mantienen por fuera de la aplicacion, directamente en bbdd. Los roles que existen en el sistema tambien se administran directamente desde la bbdd. Gestion de los permisos de los usuarios,  control de acceso y permisos en el sistema para usar los recursos api disponibles.
3. **Gestión de Cursos/Tarifas/Aulas/Horarios**: Administración de cursos, tarifas, asignación de aulas, horarios y profesores.
4. **Gestión de Profesores**: Asignación a cursos, gestión de sesiones, listas de asistencia, documentación y anotaciones de cada sesión.
5. **Gestión de Alumnos**: Inscripciones, seguimiento académico. Control de pagos.
6. **Gestión de Trabajadores Virtuales**: vinculación con trabajadores virtuales.
7. **Monitoreo y Salud del Sistema**: Verificación del estado del sistema, logs, depuración.

## Contextos Delimitados
Los contextos delimitados identificados en este proyecto son:

1. **Gestión de Academias**: 
   - **Administración de Academias**: Alta, baja y consultas de academias.

2. **Gestión de Usuarios**: 
   - **Autenticación y Autorización**: Manejo de credenciales, roles y permisos.
   - **Gestión de Usuarios de Academia**: Alta, baja y modificación de usuarios asociados a academias.
   - **Gestión de Permisos**: Control de acceso. Gestión de permisos para acceder a recursos específicos del sistema.

3. **Gestión de Cursos/Tarifas/Aulas/Horarios**: 
   - **Gestión de Tarifas**: Configuración de tarifas para cursos.
   - **Gestión de Cursos**: Creación y administración de cursos.  
   - **Gestión de Aulas y Horarios**: Asignación de aulas y horarios a cursos.
   - **Asignación de profesores a Cursos**: Asignación de profesores a cursos específicos.

4. **Gestión de Profesores**: 
   - **Gestión de Sesiones**: Registro de asistencia, documentación y anotaciones de sesiones.

5. **Gestión de Alumnos**: 
   - **Inscripciones**: Registro de alumnos en cursos.
   - **Seguimiento Académico**: Gestión del progreso y desempeño de los alumnos. Pasar lista.
   - **Control de Pagos**: Registro y seguimiento de pagos realizados/pendientes.

6. **Gestión de Trabajadores Virtuales**: 
   - **Automatización de Tareas**: Vinculación y configuración de trabajadores virtuales.

7. **Monitoreo y Salud del Sistema**: 
   - **Logs y Depuración**: Registro de eventos y errores del sistema.
   - **Verificación de Salud**: Endpoints para comprobar el estado del sistema.

## Estructura de Carpetas
La estructura de carpetas sigue las mejores prácticas de DDD y se adapta a las necesidades del proyecto:

```
contexto_delimitado/
    ├── application/       # Servicios de aplicación: coordinan operaciones del dominio.
    ├── domain/            # Lógica de negocio pura: entidades, agregados, repositorios.
    ├── infrastructure/    # Implementaciones técnicas: bases de datos, APIs externas.
    ├── interfaces/        # Controladores y puntos de entrada: exponen los endpoints.
```

## Resumen por Subdominio

### 1 - Gestión de Usuarios
El subdominio de Gestión de Usuarios incluye las siguientes responsabilidades:

- **Alta de Usuario**: Crear un nuevo usuario asignándole un rol (Administrador de Academia o Profesor). El rol de Administrador de Plataforma está reservado y no puede ser asignado.
- **Baja de Usuario**: Eliminar un usuario del sistema.
- **Modificación de Credenciales**: Actualizar el correo electrónico o la contraseña de un usuario.
- **Modificación de Rol**: Cambiar el rol asignado a un usuario.
- **Modificación de nombre**: Cambiar el nombre asignado a un usuario.
- **Modificación de Estado**: Actualizar el estado del usuario (Activo, Bloqueado, Baja).
- **Recordar Credenciales**: Proceso para recuperar credenciales de acceso.

#### 1.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Usuarios se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios de aplicación que actúan como intermediarios entre la capa de interfaces y la lógica del dominio.
  - Ejemplo: `UserService`, que coordina operaciones como la creación, modificación y eliminación de usuarios.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**: `User` (con atributos como `id`, `name`, `email`, `password`, `role`, `status`, `fecha_alta`, `fecha_baja`, `fecha_ultima_modificacion`).
    - **Repositorios**: Interfaces como `UserRepository` para definir las operaciones de persistencia.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**: `SQLUserRepository`, que implementa las operaciones definidas en `UserRepository` y utiliza SQL para interactuar con la base de datos.
    - **Integraciones**: Configuración de conexiones a la base de datos o servicios externos relacionados con usuarios.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de usuarios.
  - Ejemplo:
    - **Controladores**: `UserController`, que maneja las solicitudes HTTP para operaciones como crear, modificar y eliminar usuarios.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 1.2 - Relación con los Endpoints
##### 1.2.1 - Listado

  - `/users` (POST, GET)
  - `/users/{id}` (GET, DELETE, PUT)
  - `/users/{id}/credentials` (PUT)
  - `/users/{id}/role` (PUT)
  - `/users/{id}/status` (PUT)
  - `/users/recover` (GET)

##### 1.2.2 - Detalles
- **Crear Usuario**:
  - Método: `POST`
  - Ruta: `/users`
  - Parámetros:
    - `name` (string, requerido): Nombre del usuario.
    - `email` (string, requerido): Correo electrónico del usuario.
    - `password` (string, requerido): Contraseña del usuario.
    - `role` (string, requerido): Rol del usuario (`admin_academia` o `profesor`).

- **Modificar Usuario**:
  - Método: `PUT`
  - Ruta: `/users/{id}`
  - Parámetros:
    - `name` (string, opcional): Nuevo nombre del usuario.
    - `email` (string, opcional): Nuevo correo electrónico.
    - `password` (string, opcional): Nueva contraseña.
    - `role` (string, opcional): Nuevo rol del usuario.
    - `status` (string, opcional): Nuevo estado (`Activo`, `Bloqueado`, `Baja`).

- **Eliminar Usuario**:
  - Método: `DELETE`
  - Ruta: `/users/{id}`
  - Parámetros:
    - `id` (int, requerido): Identificador del usuario.

- **Actualizar Credenciales**:
  - Método: `PUT`
  - Ruta: `/users/{id}/credentials`
  - Parámetros:
    - `email` (string, opcional): Nuevo correo electrónico.
    - `password` (string, opcional): Nueva contraseña.

- **Actualizar Rol**:
  - Método: `PUT`
  - Ruta: `/users/{id}/role`
  - Parámetros:
    - `role` (string, requerido): Nuevo rol del usuario.

- **Actualizar Estado**:
  - Método: `PUT`
  - Ruta: `/users/{id}/status`
  - Parámetros:
    - `status` (string, requerido): Nuevo estado (`Activo`, `Bloqueado`, `Baja`).

- **Recordar Credenciales**:
  - Método: `GET`
  - Ruta: `/users/recover`
  - Parámetros:
    - `email` (string, requerido): Correo electrónico asociado al usuario.

### 2 - Gestión de Cursos
El subdominio de Gestión de Cursos incluye las siguientes responsabilidades:

- **Gestión de Tarifas**: Configurar tarifas y sus posibles descuentos.
- **Creación de Cursos**: Permitir la creación de nuevos cursos con información como nombre, descripción, duración y la vinculación con una tarifa.
- **Creacion de aulas y Asignación de Aulas y Horarios a los cursos**: Asignar aulas y horarios específicos a cada curso.
- **Asignación de Profesores**: Vincular profesores a cursos específicos de manera independiente al horario.
- **Consulta de Cursos**: Listar y obtener detalles de los cursos existentes, sus tarifas, horarios, aulas y profesores vinculados.

#### 2.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Cursos se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `CourseService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `CourseService`: Gestiona la creación, modificación y eliminación de cursos.
    - `ScheduleService`: Coordina la asignación de horarios a cursos.
    - `ProfessorAssignmentService`: Gestiona la asignación de profesores a cursos.

- **domain/**:
  - Definirá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Course` (con atributos como `id`, `name`, `description`, `duration`, `tariff_id`).
      - `Tariff` (con atributos como `id`, `description`, `price`, `discount`).
      - `Schedule` (con atributos como `id`, `course_id`, `classroom_id`, `day_of_week`, `start_time`, `end_time`).
    - **Repositorios**:
      - `CourseRepository`: Define las operaciones de persistencia para cursos.
      - `ScheduleRepository`: Define las operaciones de persistencia para horarios.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLCourseRepository`: Implementa las operaciones definidas en `CourseRepository` utilizando SQL.
      - `SQLScheduleRepository`: Implementa las operaciones definidas en `ScheduleRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de cursos.
  - Ejemplo:
    - **Controladores**:
      - `CourseController`: Maneja las solicitudes HTTP para operaciones como crear, modificar y eliminar cursos.
      - `ScheduleController`: Maneja las solicitudes HTTP para asignar horarios a cursos.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 2.2 - Relación con los Endpoints
##### 2.2.1 - Listado
  - `/tariffs` (GET): Listar tarifas.
  - `/tariffs/{id}` (GET): Obtener detalles de una tarifa.
  - `/tariffs` (POST): Crear una nueva tarifa.
  - `/tariffs/{id}` (PUT): Actualizar una tarifa existente.
  - `/tariffs/{id}` (DELETE): Eliminar una tarifa.
  - `/tariffs/{id}/discounts` (POST): Crear un descuento para una tarifa.
  - `/tariffs/{id}/discounts/{discount_id}` (DELETE): Eliminar un descuento de una tarifa.
  - `/tariffs/{id}/discounts` (GET): Listar todos los descuentos de una tarifa.
  - `/tariffs/{id}/discounts/{discount_id}` (PUT): Modificar un descuento de una tarifa.

  - `/courses` (GET): Listar cursos.
  - `/courses/{id}` (GET): Obtener detalles de un curso.
  - `/courses` (POST): Crear un nuevo curso.
  - `/courses/{id}` (PUT): Actualizar un curso existente.
  - `/courses/{id}` (DELETE): Eliminar un curso.

  - `/classrooms` (GET): Listar aulas.
  - `/classrooms/{id}` (GET): Obtener detalles de un aula.
  - `/classrooms` (POST): Crear una nueva aula.
  - `/classrooms/{id}` (PUT): Actualizar un aula existente.
  - `/classrooms/{id}` (DELETE): Eliminar un aula.

  - `/courses/{id}/schedules` (POST): Asignar un aula, dia de la semana y hora inicio y fin para el horario del curso.
  - `/courses/{id}/schedules/{schedule_id}` (DELETE): Eliminar un horario.
  - `/courses/{id}/schedules` (GET): Consultar todos los horarios de un curso.
  - `/courses/{id}/schedules/{schedule_id}` (PUT): Modificar un horario por su ID.
  - `/courses/{id}/professors` (POST): Asignar un profesor a un curso.
  - `/courses/{id}/professors/{professor_id}` (DELETE): Eliminar a un profesor de un curso.

##### 2.2.2 - Detalles
- **Crear Tarifa**:
  - Método: `POST`
  - Ruta: `/tariffs`
  - Parámetros:
    - `description` (string, requerido): Descripción de la tarifa.
    - `price` (float, requerido): Precio base de la tarifa.

- **Crear Descuento para una Tarifa**:
  - Método: `POST`
  - Ruta: `/tariffs/{id}/discounts`
  - Parámetros:
    - `type` (string, requerido): Tipo de descuento (`percentage` o `fixed`).
    - `value` (float, requerido): Valor del descuento.

- **Crear Aula**:
  - Método: `POST`
  - Ruta: `/classrooms`
  - Parámetros:
    - `name` (string, requerido): Nombre del aula.
    - `capacity` (int, requerido): Capacidad máxima del aula.

- **Asignar Aula a un Curso para un Horario**:
  - Método: `POST`
  - Ruta: `/courses/{id}/classrooms`
  - Parámetros:
    - `classroom_id` (int, requerido): Identificador del aula.
    - `day_of_week` (string, requerido): Día de la semana.
    - `start_time` (string, requerido): Hora de inicio (formato HH:mm).
    - `end_time` (string, requerido): Hora de fin (formato HH:mm).

- **Asignar Profesor a un Curso**:
  - Método: `POST`
  - Ruta: `/courses/{id}/professors`
  - Parámetros:
    - `professor_id` (int, requerido): Identificador del profesor.
    - `start_date` (string, requerido): Fecha de inicio de la asignación (formato YYYY-MM-DD).
    - `end_date` (string, opcional): Fecha de fin de la asignación (formato YYYY-MM-DD).

- **Listar Descuentos de una Tarifa**:
  - Método: `GET`
  - Ruta: `/tariffs/{id}/discounts`
  - Parámetros:
    - `id` (int, requerido): Identificador de la tarifa.

- **Modificar un Descuento de una Tarifa**:
  - Método: `PUT`
  - Ruta: `/tariffs/{id}/discounts/{discount_id}`
  - Parámetros:
    - `type` (string, opcional): Tipo de descuento (`percentage` o `fixed`).
    - `value` (float, opcional): Valor del descuento.

- **Eliminar un Aula de un Curso para un Horario**:
  - Método: `DELETE`
  - Ruta: `/courses/{id}/schedules/{schedule_id}/classrooms/{classroom_id}`
  - Parámetros:
    - `schedule_id` (int, requerido): Identificador del horario.
    - `classroom_id` (int, requerido): Identificador del aula.

- **Consultar Horarios de un Curso**:
  - Método: `GET`
  - Ruta: `/courses/{id}/schedules`
  - Parámetros:
    - `id` (int, requerido): Identificador del curso.

- **Modificar un Horario por su ID**:
  - Método: `PUT`
  - Ruta: `/courses/{id}/schedules/{schedule_id}`
  - Parámetros:
    - `classroom_id` (int, opcional): Nuevo identificador del aula.
    - `day_of_week` (string, opcional): Nuevo día de la semana.
    - `start_time` (string, opcional): Nueva hora de inicio (formato HH:mm).
    - `end_time` (string, opcional): Nueva hora de fin (formato HH:mm).

- **Eliminar a un Profesor de un Curso**:
  - Método: `DELETE`
  - Ruta: `/courses/{id}/professors/{professor_id}`
  - Parámetros:
    - `professor_id` (int, requerido): Identificador del profesor.

### 3 - Gestión de Profesores
#### 3.1 - Estructura de Carpetas
- **application/**:
  - `SessionService`: Gestiona la creación, modificación y anotaciones de sesiones.
- **domain/**:
  - **Entidades**:
    - `Session` (con atributos como `id`, `course_id`, `classroom_id`, `start_time`, `end_time`, `notes`).
    - `Annotation` (con atributos como `id`, `session_id`, `type`, `text`).
  - **Repositorios**:
    - `SessionRepository`: Define las operaciones de persistencia para sesiones.
    - `AnnotationRepository`: Define las operaciones de persistencia para anotaciones.
- **infrastructure/**:
  - `SQLSessionRepository`: Implementa las operaciones definidas en `SessionRepository` utilizando SQL.
  - `SQLAnnotationRepository`: Implementa las operaciones definidas en `AnnotationRepository` utilizando SQL.
- **interfaces/**:
  - `SessionController`: Maneja las solicitudes HTTP para sesiones y anotaciones.

#### 3.2 - Relación con los Endpoints
##### 3.2.1 - Listado
- `/teachers/{id}/sessions` (GET): Obtener todas las sesiones asociadas a un profesor específico.
- `/teachers/{id}/annotations` (GET): Obtener todas las anotaciones realizadas por un profesor.
- `/teachers` (GET): Listar todos los profesores registrados en el sistema (si no se elimina por redundancia).
- `/sessions/{id}` (PUT): Modificar los detalles de una sesión existente.
- `/sessions/{session_id}/annotations/{id}` (PUT): Modificar los detalles de una anotación existente.

##### 3.2.2 - Detalles
- **Abrir una Sesión**:
  - Método: `POST`
  - Ruta: `/sessions`
  - Parámetros:
    - `course_id` (int, requerido): Identificador del curso.
    - `classroom_id` (int, requerido): Identificador del aula.
    - `start_time` (string, requerido): Hora de inicio (formato HH:mm).
    - `end_time` (string, requerido): Hora de fin (formato HH:mm).
    - `notes` (string, opcional): Notas iniciales de la sesión.

- **Modificar una Sesión**:
  - Método: `PUT`
  - Ruta: `/sessions/{id}`
  - Parámetros:
    - `start_time` (string, opcional): Nueva hora de inicio (formato HH:mm).
    - `end_time` (string, opcional): Nueva hora de fin (formato HH:mm).
    - `notes` (string, opcional): Nuevas notas de la sesión.

- **Modificar una Anotación**:
  - Método: `PUT`
  - Ruta: `/sessions/{session_id}/annotations/{id}`
  - Parámetros:
    - `type` (string, opcional): Nuevo tipo de anotación (`Ausencia`, `Evaluación`, `Comportamiento`).
    - `text` (string, opcional): Nuevo texto de la anotación.

- **Añadir Anotaciones a una Sesión**:
  - Método: `POST`
  - Ruta: `/sessions/{id}/annotations`
  - Parámetros:
    - `type` (string, requerido): Tipo de anotación (`Ausencia`, `Evaluación`, `Comportamiento`).
    - `text` (string, requerido): Texto de la anotación.

### 4 - Gestión de Alumnos
#### 4.1 - Estructura de Carpetas
#### 4.2 - Relación con los Endpoints
##### 4.2.1 - Listado
  - `/students` (GET): Listar alumnos.
  - `/students/{id}/progress` (GET): Ver progreso académico.
  - `/students/payments` (GET): Listar pagos.
  - `/students/payments/{id}` (GET): Obtener detalles de un pago.
##### 4.2.2 - Detalles
----------------------------------------------------------------

### 7 - Monitoreo y salud del sistema
#### 7.1 - Estructura de Carpetas
#### 7.2 - Relación con los Endpoints
##### 7.2.1 - Listado
- `/health` (GET): Verificar el estado del sistema.
##### 7.2.2 - Detalles








## Guía para la Implementación
1. **Mantener la Cohesión**:
   - Cada contexto delimitado debe ser autónomo y contener todo lo necesario para cumplir su propósito.

2. **Evitar Dependencias Circulares**:
   - Las dependencias entre contextos deben ser mínimas y bien definidas.

3. **Documentar el Código**:
   - Cada módulo debe incluir comentarios claros sobre su propósito y uso.

4. **Pruebas Unitarias**:
   - Implementar pruebas unitarias para cada componente del dominio y servicios de aplicación.

5. **Revisar y Refactorizar**:
   - Realizar revisiones periódicas para garantizar que la estructura sigue siendo adecuada a medida que el proyecto crece.