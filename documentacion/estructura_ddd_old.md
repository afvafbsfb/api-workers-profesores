# Estructura DDD del Proyecto

## Introducción
La estructura del proyecto sigue los principios de Domain-Driven Design (DDD), organizando el código en contextos delimitados (bounded contexts) para reflejar las responsabilidades del dominio. Cada contexto delimitado se divide en subcarpetas que representan diferentes capas y componentes del sistema.

## Dominio Principal
**Gestión de academias**: El sistema está enfocado en la gestión de academias, proporcionando herramientas para administrar usuarios, cursos, profesores, alumnos, pagos, y otros aspectos clave.

## Subdominios
1. **Gestión de Academias**: Administración general de las academias. Alta y baja de academias, consultas.
2. **Gestión de Usuarios**: Alta, baja, modificación, consulta, Autenticación, roles, permisos. Encargado de manejar los usuarios para una academia. Estos usuarios pueden ser administradores de la academia o profesores.  IMPORTANTE los usuarios administradores del sistema se dan de alta y mantienen por fuera de la aplicacion, directamente en bbdd. Los roles que existen en el sistema tambien se administran directamente desde la bbdd. Gestion de los permisos de los usuarios,  control de acceso y permisos en el sistema para usar los recursos api disponibles tambien se gestionan por fuera del api, directamente en la bbdd.
3. **Gestión de Cursos/Tarifas/Aulas/Horarios**: Administración de cursos, tarifas, asignación de aulas, horarios y profesores.
4. **Gestión de Profesores**: Asignación a cursos, gestión de sesiones, listas de asistencia, documentación y anotaciones de cada sesión.
5. **Gestión de Alumnos**: Altas, Inscripciones, seguimiento académico. Control de pagos.
6. **Gestión de liquidacion de cuotas**: liquidacion mensual de cuotas
7. **Gestión de Trabajadores Virtuales**: vinculación con trabajadores virtuales.
8. **Monitoreo y Salud del Sistema**: Verificación del estado del sistema, logs, depuración.

## Contextos Delimitados
Cada contexto delimitado encapsula una parte del dominio y define un espacio donde las reglas, conceptos y términos tienen un significado bien definido. 

Cada contexto delimitado se enfoca en una parte específica del dominio, como la gestión de usuarios, cursos, o tarifas.

Los contextos delimitados son independientes entre sí, lo que significa que pueden evolucionar y cambiar sin afectar a otros contextos.

Cuando un contexto necesita interactuar con otro, se hace a través de interfaces bien definidas, como eventos, APIs o servicios.

Los contextos delimitados identificados en este proyecto son:

1. **Gestión de Academias**: 
   - **Administración de Academias**: Alta, baja y consultas de academias.

2. **Gestión de Usuarios**: 
   - **Gestión de Usuarios de Academia**: Alta, baja y modificación de usuarios asociados a academias.
   - **Autenticación y Autorización**: Manejo de credenciales, roles y permisos.
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

6. **Gestión de Liquidación de Cuotas**: Liquidación mensual de cuotas, simulación de liquidaciones y cancelaciones para inscripciones específicas.

7. **Gestión de Trabajadores Virtuales**: 
   - **Automatización de Tareas**: Vinculación y configuración de trabajadores virtuales.

8. **Monitoreo y Salud del Sistema**: 
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

### 1 - Gestión de Academias
El subdominio de Gestión de Academias incluye las siguientes responsabilidades:

- **Alta de Academia**: Crear una nueva academia en el sistema.
- **Modificación de Academia**: Actualizar los datos de una academia existente.
- **Baja de Academia**: Eliminar o desactivar una academia del sistema.
- **Consulta de Academias**: Listar todas las academias registradas.

#### 1.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Academias se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `AcademyService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `AcademyService`: Gestiona la creación, modificación y eliminación de academias.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Academy` (con atributos como `id`, `name`, `address`, `status`).
    - **Repositorios**:
      - `AcademyRepository`: Define las operaciones de persistencia para academias.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLAcademyRepository`: Implementa las operaciones definidas en `AcademyRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de academias.
  - Ejemplo:
    - **Controladores**:
      - `AcademyController`: Maneja las solicitudes HTTP para operaciones como listar, crear y modificar academias.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 1.2 - Relación con los Endpoints
##### 1.2.1 - Listado
- `/academies` (POST): Crear una nueva academia.
- `/academies/{academyId}` (PUT): Modificar una academia existente.
- `/academies/{academyId}` (DELETE): Dar de baja una academia.
- `/academies` (GET): Listar todas las academias.
- `/academies/{academyId}/schedule` (GET): Listar horario completo de una academia.

##### 1.2.2 - Detalles
- **Crear Academia**:
  - Método: `POST`
  - Ruta: `/academies`
  - Parámetros:
    - `name` (string, requerido): Nombre de la academia.
    - `address` (string, requerido): Dirección de la academia.
    - `status` (string, opcional): Estado inicial de la academia (`Activo`, `Inactivo`).

- **Modificar Academia**:
  - Método: `PUT`
  - Ruta: `/academies/{academyId}`
  - Parámetros:
    - `name` (string, opcional): Nuevo nombre de la academia.
    - `address` (string, opcional): Nueva dirección de la academia.
    - `status` (string, opcional): Nuevo estado de la academia (`Activo`, `Inactivo`).

- **Dar de Baja una Academia**:
  - Método: `DELETE`
  - Ruta: `/academies/{academyId}`
  - Parámetros:
    - `id` (int, requerido): Identificador de la academia.

- **Listar Academias**:
  - Método: `GET`
  - Ruta: `/academies`
  - Parámetros: Ninguno.

- **Listar horario completo de una Academia**:
  - Método: `GET`
  - Ruta: `/academies/{academyId}/schedule`
  - Parámetros: Ninguno.

### 2 - Gestión de Usuarios
El subdominio de Gestión de Usuarios incluye las siguientes responsabilidades:

- **Alta de Usuario**: Crear un nuevo usuario asignándole un rol (Administrador de Academia o Profesor). El rol de Administrador de Plataforma está reservado y no puede ser asignado.
- **Modificación de Credenciales**: Actualizar el correo electrónico o la contraseña de un usuario.
- **Modificación de Rol**: Cambiar el rol asignado a un usuario.
- **Modificación de nombre**: Cambiar el nombre asignado a un usuario.
- **Modificación de Estado**: Actualizar el estado del usuario (Activo, Bloqueado, Baja).
- **Recordar Credenciales**: Proceso para recuperar credenciales de acceso.

#### 2.1 - Estructura de Carpetas
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

  - `/users` (POST)
  - `/users` (GET)
  - `/users/{userId}` (PUT)
  - `/users/{userId}/credentials` (PUT)
  - `/users/{userId}/role` (PUT)
  - `/users/{userId}/status` (PUT)
  - `/users/recover` (GET)
  - `/academies/{academyId}/users` (GET): Listar todos los usuarios registrados en la academia. opcional listar solo los que sean "in" algun rol que le pasemos de entrada.

##### 1.2.2 - Detalles
- **Crear Usuario**:
  - Método: `POST`
  - Ruta: `/users`
  - Parámetros:
    - `name` (string, requerido): Nombre del usuario.
    - `email` (string, requerido): Correo electrónico del usuario.
    - `password` (string, requerido): Contraseña del usuario.
    - `role` (string, requerido): Rol del usuario (`Admin_plataforma`, `Admin_academia`, `Profesor_academia`, `Admin_y_profesor_academia`).
    - `academia_id` (int, requerido): Identificador de la academia asociada al usuario.

- **Leer Usuario**:
  - Método: `GET`
  - Ruta: `/users`
  - Parámetros:
    - `email` (string, requerido): Correo electrónico asociado al usuario.

- **Modificar Usuario**:
  - Método: `PUT`
  - Ruta: `/users/{id}`
  - Parámetros:
    - `name` (string, opcional): Nuevo nombre del usuario.
    - `email` (string, opcional): Nuevo correo electrónico.
    - `password` (string, opcional): Nueva contraseña.
    - `role` (string, opcional): Nuevo rol del usuario.
    - `status` (string, opcional): Nuevo estado (`Activo`, `Bloqueado`, `Baja`).
    - `academia_id` (int, opcional): Nuevo identificador de la academia asociada al usuario.

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
  - `/academies/{academyId}/tariffs` (GET): Listar tarifas de una academia.
  - `/tariffs/{tariffId}` (GET): Obtener detalles de una tarifa.
  - `/academies/{academyId}/tariffs` (POST): Crear una nueva tarifa.
  - `/tariffs/{tariffId}` (PUT): Actualizar una tarifa existente, tambien darla de baja.

  - `/academies/{academyId}/courses` (GET): Listar cursos.
  
  - `/courses/{courseId}` (GET): Obtener detalles de un curso.

  - `/courses/{courseId}/schedule` (GET): Obtener horario de 1 curso
 
  - `/academies/{academyId}/courses` (POST): Crear un nuevo curso.

  - `/courses/{courseId}` (PUT): Actualizar un curso existente, darlo de baja.

  - `/academies/{academyId}/classrooms` (GET): Listar aulas.
  - `/classrooms/{classroomId}` (GET): Obtener detalles de un aula.
  - `/academies/{academyId}/classrooms` (POST): Crear una nueva aula.
  - `/classrooms/{classroomId}` (PUT): Actualizar un aula existente.
  - `/classrooms/{classroomId}` (DELETE): Eliminar un aula.

##### 2.2.2 - Detalles
- **Crear Tarifa**:
  - Método: `POST`
  - Ruta: `/academies/{id}/tariffs`
  - Parámetros:
    - `description` (string, requerido): Descripción de la tarifa.
    - `price` (float, requerido): Precio base de la tarifa.

- **Crear Descuento para una Tarifa**:
  - Método: `POST`
  - Ruta: `tariffs/{tariff_id}/discounts`
  - Parámetros:
    - `type` (string, requerido): Tipo de descuento (`percentage` o `fixed`).
    - `value` (float, requerido): Valor del descuento.

- **Modificar un Descuento de una Tarifa**:
  - Método: `PUT`
  - Ruta: `tariffs/{tariff_id}/discounts/{discount_id}`
  - Parámetros:
    - `type` (string, opcional): Tipo de descuento (`percentage` o `fixed`).
    - `value` (float, opcional): Valor del descuento.

- **Listar Descuentos de una Tarifa**:
  - Método: `GET`
  - Ruta: `tariffs/{tariff_id}/discounts`
  - Parámetros:
    - `id` (int, requerido): Identificador de la tarifa.

- **Crear Aula**:
  - Método: `POST`
  - Ruta: `/academies/{id}/classrooms`
  - Parámetros:
    - `name` (string, requerido): Nombre del aula.
    - `capacity` (int, requerido): Capacidad máxima del aula.

- **Crear horario, Asignar Aula a un Curso para un Horario**:
  - Método: `POST`
  - Ruta: `/courses/{course_id}/schedule`
  - Parámetros:
    - `classroom_id` (int, requerido): Identificador del aula.
    - `day_of_week` (string, requerido): Día de la semana.
    - `start_time` (string, requerido): Hora de inicio (formato HH:mm).
    - `end_time` (string, requerido): Hora de fin (formato HH:mm).

- **Asignar Profesor a un Curso**:
  - Método: `POST`
  - Ruta: `/courses/{course_id}/professors`
  - Parámetros:
    - `professor_id` (int, requerido): Identificador del profesor.
    - `start_date` (string, requerido): Fecha de inicio de la asignación (formato YYYY-MM-DD).
    - `end_date` (string, opcional): Fecha de fin de la asignación (formato YYYY-MM-DD).


- **Eliminar un registro de Horario**:
  - Método: `DELETE`
  - Ruta: `/courses/{id}/schedules/{schedule_id}`
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

- **Eliminar a un Profesor de un Curso, marcarlo dado de baja**:
  - Método: `PUT`
  - Ruta: `/courses/{id}/d/{professor_id}`
  - Parámetros:
    - `professor_id` (int, requerido): Identificador del profesor.

- **Obtener el Profesor Vigente de un Curso**:
  - Método: `GET`
  - Ruta: `/courses/{id}/current-professor`
  - Descripción: Devuelve el profesor vigente vinculado al curso (aquel que no tiene fecha de baja).

- **Obtener Todos los Profesores de un Curso**:
  - Método: `GET`
  - Ruta: `/courses/{id}/professors`
  - Descripción: Devuelve todos los profesores que han estado vinculados al curso, incluyendo los dados de baja.

- **Obtener Todos los Cursos de un Profesor**:
  - Método: `GET`
  - Ruta: `/professors/{id}/courses`
  - Descripción: Devuelve todos los cursos en los que el profesor ha estado vinculado, tanto vigentes como históricos.

### 3 - Gestión de Profesores
El subdominio de Gestión de Profesores incluye las siguientes responsabilidades:

- **Gestión de Sesiones**: Crear y modificar sesiones para los cursos asignados.
- **Registro de Asistencia**: Marcar la asistencia de los alumnos en las sesiones.
- **Gestión de Anotaciones**: Crear y modificar anotaciones relacionadas con las sesiones.
- **Consulta de Sesiones y Anotaciones**: Permite a los profesores consultar las sesiones y anotaciones registradas.

#### 3.1 - Subdominios Funcionales
- **Gestión de Sesiones**: Permite a los profesores crear, modificar y gestionar sesiones asociadas a cursos.
- **Gestión de Anotaciones**: Facilita la creación, modificación y consulta de anotaciones relacionadas con las sesiones.
- **Consulta de Sesiones y Anotaciones**: Proporciona a los profesores acceso a las sesiones y anotaciones registradas.

#### 3.2 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Profesores se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `SessionService` para gestionar las operaciones relacionadas con las sesiones y anotaciones de los profesores.
  - Ejemplo:
    - `SessionService`: Gestiona la creación, modificación y eliminación de sesiones.
    - `AnnotationService`: Gestiona la creación, modificación y consulta de anotaciones.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Session` (con atributos como `id`, `course_id`, `classroom_id`, `start_time`, `end_time`, `notes`).
      - `Annotation` (con atributos como `id`, `session_id`, `type`, `text`).
    - **Repositorios**:
      - `SessionRepository`: Define las operaciones de persistencia para sesiones.
      - `AnnotationRepository`: Define las operaciones de persistencia para anotaciones.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLSessionRepository`: Implementa las operaciones definidas en `SessionRepository` y utiliza SQL para interactuar con la base de datos. La configuración de conexión se adapta según el entorno (producción o desarrollo).
      - `SQLAnnotationRepository`: Similar al anterior, pero enfocado en las anotaciones.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de sesiones y anotaciones.
  - Ejemplo:
    - **Controladores**:
      - `SessionController`: Maneja las solicitudes HTTP para operaciones como crear, modificar y eliminar sesiones.
      - `AnnotationController`: Maneja las solicitudes HTTP para operaciones como crear, modificar y eliminar anotaciones.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 3.3 - Relación con los Endpoints
##### 3.3.1 - Listado

- `/professors/{professorId}/schedule` (GET): --> consultar los horarios de un profesor

- `/professors/{professorId}/courses/{courseId}/sessions` (POST): Crear una nueva sesión.

- `/sessions/{sessionId}` (GET): Obtener detalles de una sesión.

- `/sessions/{sessionId}` (PUT): Modificar los detalles de una sesión existente, incluso darla de baja.

- `/professors/{professorId}/courses/{courseId}/sessions` (GET): Obtener todas las sesiones asociadas a un profesor específico.  Una sesion es una clase realizada.

- `/sessions/{sessionId}/students/{studentId}/annotations` (POST): Crear una anotación para un alumno en una sesión.

- `/professors/{professorId}/courses/{courseId}/annotations` (GET): Obtener todas las anotaciones realizadas por un profesor en un curso. y que se pueda filtrar por el tipo de anotacion.

- `/professors/{professorId}/courses/{courseId}/students/{studentId}/annotations` (GET) : Obtener todas las anotaciones realizadas por un profesor sobre un alumno en un curso.  Y que se pueda filtrar por el tipo de anotacion.

- `/courses/{courseId}/students/{studentId}/annotations` (GET) : Obtener todas las anotaciones realizadas sobre un alumno en un curso.  Y que se pueda filtrar por el tipo de anotacion.

- `/annotations/{annotationId}` (GET): Obtener detalles de una anotación.

- `/annotations/{annotationsId}` (PUT): Modificar los detalles de una anotación existente.


##### 3.3.2 - Detalles
- **Crear Sesión**:
  - Método: `POST`
  - Ruta: `/professors/{professorId}/courses/{courseId}/sessions`
  - Parámetros (Body):
    ```json
    {
      "classroomId": "A-101",
      "startTime": "2025-09-25T17:00:00Z",
      "endTime": "2025-09-25T18:30:00Z",
      "sessionNotes": "Repaso examen",
      "subjectNotes": "Funciones lineales"
    }
    ```
  - Respuestas:
    - `201 Created`: Sesión creada exitosamente. Location: `/sessions/{sessionId}`.
    - `404 Not Found`: El profesor no imparte ese curso.
    - `409 Conflict`: Solape de horario en el aula o profesor.

- **Detalle Sesión**:
  - Método: `GET`
  - Ruta: `/sessions/{sessionId}`
  - Respuestas:
    - `200 OK`: Devuelve los detalles de la sesión.
    - `404 Not Found`: Sesión no encontrada.

- **Crear Anotación**:
  - Método: `POST`
  - Ruta: `/sessions/{sessionId}/students/{studentId}/annotations`
  - Parámetros (Body):
    ```json
    {
      "type": "Ausencia",      // Ausencia | Evaluacion | Comportamiento
      "text": "Faltó sin avisar"
    }
    ```
  - Respuestas:
    - `201 Created`: Anotación creada exitosamente. Location: `/annotations/{annotationId}`.
    - `404 Not Found`: El alumno no pertenece a la sesión.
    - `409 Conflict`: Anotación incompatible (p. ej., duplicada de ausencia).

- **Detalle Anotación**:
  - Método: `GET`
  - Ruta: `/annotations/{annotationId}`
  - Respuestas:
    - `200 OK`: Devuelve los detalles de la anotación.
    - `404 Not Found`: Anotación no encontrada.

### 4 - Gestión de Alumnos

#### 4.1 - Subdominios Funcionales
- **Inscripciones**: Registro de alumnos en cursos.
- **Seguimiento Académico**: Gestión del progreso y desempeño de los alumnos, incluyendo asistencia y calificaciones.
- **Control de Pagos**: Registro y seguimiento de movimientos y extractos relacionados con los pagos realizados o pendientes.

#### 4.2 - Estructura de Carpetas
- **application/**:
  - Contendrá servicios como `EnrollmentService`, `ProgressService` y `ExtractManagementService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `EnrollmentService`: Gestiona la inscripción de alumnos en cursos.
    - `ProgressService`: Coordina el seguimiento académico de los alumnos.
    - `ExtractManagementService`: Gestiona los movimientos y extractos relacionados con los pagos de los alumnos.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Student` (con atributos como `id`, `name`, `email`, `status`).
      - `Enrollment` (con atributos como `id`, `student_id`, `course_id`, `enrollment_date`).
      - `Extract` (con atributos como `id`, `student_id`, `total_amount`, `status`, `creation_date`).
      - `Movement` (con atributos como `id`, `extract_id`, `amount`, `type`, `movement_date`).
    - **Repositorios**:
      - `StudentRepository`: Define las operaciones de persistencia para alumnos.
      - `EnrollmentRepository`: Define las operaciones de persistencia para inscripciones.
      - `ExtractRepository`: Define las operaciones de persistencia para extractos.
      - `MovementRepository`: Define las operaciones de persistencia para movimientos.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLStudentRepository`: Implementa las operaciones definidas en `StudentRepository` utilizando SQL.
      - `SQLEnrollmentRepository`: Implementa las operaciones definidas en `EnrollmentRepository` utilizando SQL.
      - `SQLExtractRepository`: Implementa las operaciones definidas en `ExtractRepository` utilizando SQL.
      - `SQLMovementRepository`: Implementa las operaciones definidas en `MovementRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de alumnos.
  - Ejemplo:
    - **Controladores**:
      - `StudentController`: Maneja las solicitudes HTTP para operaciones como listar, crear y modificar alumnos.
      - `EnrollmentController`: Maneja las solicitudes HTTP para inscripciones.
      - `ExtractController`: Maneja las solicitudes HTTP para extractos y movimientos.

#### 4.3 - Relación con los Endpoints
##### 4.3.1 - Listado
- `/academy/{academyId}/students` (POST): Crear un nuevo alumno.
- `/students/{studentId}` (GET): Obtener detalles de un alumno.
- `/academy/{academyId}/students` (GET): Listar alumnos.
- `/students/{studentId}` (PUT): Modificar un alumno existente o darlo de baja.

- `/students/{studentId}/inscripcions` (POST): Inscribir a un alumno en un curso.
- `/students/{studentId}/inscripcions` (GET): Listar todos los cursos en los que un alumno está inscrito (activos e históricos).

- `/inscripcions/{inscripcionId}` (GET): Ver detalles de la inscripción de un alumno en un curso.

- `/inscripcions/{inscripcionId}` (PUT): modificar y Dar de baja la inscripción de un alumno en un curso (cambiar estado a inactiva).

- `/inscripcions/{inscripcionId}/movements` (GET): Listar todos los movimientos de pagos de un alumno en un curso o inscripción.

- `/inscripcions/{inscripcionId}/extract` (GET): Listar extractos de movimientos de pagos de un alumno en una inscripción o curso.

- `/inscripcions/{inscripcionId}/progress` (GET): Ver progreso académico de un alumno en un curso específico, puede ser anotaciones o faltas de asistencia.

- `/inscripcions/{inscripcionId}/movements` (POST): Añadir un movimiento a un extracto. Puede ser un movimiento de ingreso o de anulación de ingreso, siempre asociado a una inscripción a un curso.

- `/movements/{inscripcionId}` (PUT): MODIFICAR un movimiento DE un extracto. UN MOVIMIENTO de ingreso se puede anular


##### 4.3.2 - Detalles
- **Crear Alumno**:
  - Método: `POST`
  - Ruta: `/students`
  - Parámetros:
    - `name` (string, requerido): Nombre del alumno.
    - `email` (string, requerido): Correo electrónico del alumno.
    - `status` (string, opcional): Estado inicial del alumno (`Activo`, `Inactivo`).

- **Modificar Alumno, darlo de baja**:
  - Método: `PUT`
  - Ruta: `/students/{id}`
  - Parámetros:
    - `name` (string, opcional): Nuevo nombre del alumno.
    - `email` (string, opcional): Nuevo correo electrónico.
    - `status` (string, requerido): Cambiar el estado a `Inactivo`.
 

- **Registrar Inscripción**:
  - Método: `POST`
  - Ruta: `/students/{id}/inscripcions`
  - Parámetros:
    - `course_id` (int, requerido): Identificador del curso.
    - `tariff_id` (int, requerido): Identificador de la tarifa asociada.
    - `inscription_date` (string, opcional): Fecha de inscripción (formato YYYY-MM-DD).

- **Dar de Baja una Inscripción**:
  - Método: `PUT`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}`
  - Parámetros:
    - `status` (string, requerido): Cambiar el estado a `Inactiva`.

- **Ver Detalles de una Inscripción**:
  - Método: `GET`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}`
  - Parámetros:
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.

- **Ver Progreso Académico**:
  - Método: `GET`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}/progress`
  - Parámetros:
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.
    - `annotation_type` (string, opcional): Tipo de anotación a consultar (`Asistencia`, `Comportamiento`, `Evaluación`, `Todas`).

- **Listar Movimientos (pagos) de una inscripcion**:
  - Método: `GET`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}/movements`
  - Parámetros:
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.

- **Añadir Movimiento a una inscripcion (pagos)**:
  - Método: `POST`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}/movements`
  - Parámetros:
    - `amount` (float, requerido): Monto del movimiento.
    - `type` (string, requerido): Tipo de movimiento (`Ingreso`, `Anulación`).
    - `movement_date` (string, opcional): Fecha del movimiento (formato YYYY-MM-DD).

- **Listar Extractos de pagos**:
  - Método: `GET`
  - Ruta: `/students/{id}/inscripcions/{inscripcion_id}/extract`
  - Parámetros:
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.

### 5 - Gestión de liquidaciones de cuotas 

El subdominio de Gestión de Liquidaciones de Cuotas incluye las siguientes responsabilidades:

- **Liquidación Mensual**: Generar la liquidación mensual de cuotas para un curso.
- **Simulación de Liquidación**: Simular la liquidación de cuotas para una inscripción específica.
- **Simulación de Cancelación**: Simular la cancelación de cuotas para una inscripción específica.

#### 5.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Liquidaciones de Cuotas se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `LiquidationService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `LiquidationService`: Gestiona la generación y simulación de liquidaciones de cuotas.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Liquidation` (con atributos como `id`, `course_id`, `total_amount`, `status`, `creation_date`).
    - **Repositorios**:
      - `LiquidationRepository`: Define las operaciones de persistencia para liquidaciones.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLLiquidationRepository`: Implementa las operaciones definidas en `LiquidationRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de liquidaciones de cuotas.
  - Ejemplo:
    - **Controladores**:
      - `LiquidationController`: Maneja las solicitudes HTTP para operaciones como generar y simular liquidaciones.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 5.2 - Relación con los Endpoints
##### 5.2.1 - Listado
- `/courses/{courseId}/liquidacionMensual` (POST): Generar la liquidación mensual de cuotas para un curso.
- `/inscripcion/{inscripcionId}/simulacionLiquidacion` (GET): Simular la liquidación de cuotas para una inscripción específica.
- `/inscripcion/{inscripcionId}/simulacionCancelacion` (GET): Simular la cancelación de cuotas para una inscripción específica.
- `/inscripcion/{inscripcionId}/Cancelación` (GET): cancelación de cuotas para una inscripción específica. Si el alumno no debe nada, se cerrar el extracto abierto, si tiene deuda se informará de la deuda.

##### 5.2.2 - Detalles
- **Generar Liquidación Mensual**:
  - Método: `POST`
  - Ruta: `/courses/{course_id}/liquidacion_mensual`
  - Parámetros:
    - `course_id` (int, requerido): Identificador del curso.
    - `month` (string, requerido): Mes para el cual se genera la liquidación (formato YYYY-MM).

- **Simular Liquidación**:
  - Método: `POST`
  - Ruta: `/courses/{course_id}/inscripcion/{inscripcion_id}/simulacion_liquidacion`
  - Parámetros:
    - `course_id` (int, requerido): Identificador del curso.
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.
    - `simulation_date` (string, opcional): Fecha de simulación (formato YYYY-MM-DD).

- **Simular Cancelación**:
  - Método: `POST`
  - Ruta: `/courses/{course_id}/inscripcion/{inscripcion_id}/simulacion_cancelacion`
  - Parámetros:
    - `course_id` (int, requerido): Identificador del curso.
    - `inscripcion_id` (int, requerido): Identificador de la inscripción.
    - `cancellation_date` (string, opcional): Fecha de cancelación (formato YYYY-MM-DD).

### 6 - Gestión de Trabajadores Virtuales
El subdominio de Gestión de Trabajadores Virtuales incluye las siguientes responsabilidades:

- **Vinculación de Trabajadores Virtuales**: Proceso de asociar un trabajador virtual a una academia.
- **Desvinculación de Trabajadores Virtuales**: Proceso de eliminar la asociación de un trabajador virtual con una academia.


#### 6.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Gestión de Trabajadores Virtuales se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `VirtualWorkerService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `VirtualWorkerService`: Gestiona la vinculación, desvinculación y configuración de tareas para trabajadores virtuales.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `VirtualWorker` (con atributos como `id`, `name`, `email`, `status`).
      - `Task` (con atributos como `id`, `description`, `frequency`, `virtual_worker_id`).
    - **Repositorios**:
      - `VirtualWorkerRepository`: Define las operaciones de persistencia para trabajadores virtuales.
      - `TaskRepository`: Define las operaciones de persistencia para tareas.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLVirtualWorkerRepository`: Implementa las operaciones definidas en `VirtualWorkerRepository` utilizando SQL.
      - `SQLTaskRepository`: Implementa las operaciones definidas en `TaskRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con la gestión de trabajadores virtuales.
  - Ejemplo:
    - **Controladores**:
      - `VirtualWorkerController`: Maneja las solicitudes HTTP para operaciones como listar, crear y modificar trabajadores virtuales.
      - `TaskController`: Maneja las solicitudes HTTP para tareas automatizadas.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 6.2 - Relación con los Endpoints
##### 6.2.1 - Listado
- `/academy/{academyId}/virtualworkers` (GET): Listar trabajadores virtuales.
- `/academy/{academyId}/virtualworkers` (POST): Crear un nuevo trabajador virtual.
- `/virtualworkers/{virtualWorkerId}` (GET): Obtener detalles de un trabajador virtual.
- `/virtualworkers/{virtualWorkerId}` (PUT): Modificar un trabajador virtual existente.
- `/virtual-workers/{virtualWorkerId}` (DELETE): Eliminar un trabajador virtual.

##### 6.2.2 - Detalles
- **Crear Trabajador Virtual**:
  - Método: `POST`
  - Ruta: `/virtual-workers`
  - Parámetros:
    - `name` (string, requerido): Nombre del trabajador virtual.
    - `email` (string, requerido): Correo electrónico del trabajador virtual.
    - `status` (string, opcional): Estado del trabajador virtual (`Activo`, `Inactivo`).

- **Modificar Trabajador Virtual**:
  - Método: `PUT`
  - Ruta: `/virtual-workers/{id}`
  - Parámetros:
    - `name` (string, opcional): Nuevo nombre del trabajador virtual.
    - `email` (string, opcional): Nuevo correo electrónico.
    - `status` (string, opcional): Nuevo estado del trabajador virtual.

- **Eliminar Trabajador Virtual**:
  - Método: `DELETE`
  - Ruta: `/virtual-workers/{id}`
  - Parámetros:
    - `id` (int, requerido): Identificador del trabajador virtual.

- **Crear Tarea Automatizada**:
  - Método: `POST`
  - Ruta: `/tasks`
  - Parámetros:
    - `description` (string, requerido): Descripción de la tarea.
    - `frequency` (string, requerido): Frecuencia de ejecución de la tarea.

- **Modificar Tarea Automatizada**:
  - Método: `PUT`
  - Ruta: `/tasks/{id}`
  - Parámetros:
    - `description` (string, opcional): Nueva descripción de la tarea.
    - `frequency` (string, opcional): Nueva frecuencia de ejecución de la tarea.

- **Eliminar Tarea Automatizada**:
  - Método: `DELETE`
  - Ruta: `/tasks/{id}`
  - Parámetros:
    - `id` (int, requerido): Identificador de la tarea.

### 7 - Monitoreo y salud del sistema
El subdominio de Monitoreo y Salud del Sistema incluye las siguientes responsabilidades:

- **Verificación del Estado del Sistema**: Comprobar si el sistema está operativo y saludable.
- **Registro de Logs**: Almacenar y gestionar registros de eventos y errores del sistema.
- **Depuración**: Herramientas y procesos para ayudar en la identificación y solución de problemas.

#### 7.1 - Estructura de Carpetas
La estructura de carpetas para el subdominio de Monitoreo y Salud del Sistema se organiza de la siguiente manera:

- **application/**:
  - Contendrá servicios como `HealthCheckService` y `LoggingService` para coordinar las operaciones del dominio.
  - Ejemplo:
    - `HealthCheckService`: Gestiona la verificación del estado del sistema.
    - `LoggingService`: Gestiona el registro y consulta de logs del sistema.

- **domain/**:
  - Contendrá la lógica de negocio pura, incluyendo entidades, agregados y repositorios.
  - Ejemplo:
    - **Entidades**:
      - `Log` (con atributos como `id`, `timestamp`, `level`, `message`).
    - **Repositorios**:
      - `LogRepository`: Define las operaciones de persistencia para logs.

- **infrastructure/**:
  - Implementará detalles técnicos relacionados con la persistencia y otras integraciones externas.
  - Ejemplo:
    - **Repositorios**:
      - `SQLLogRepository`: Implementa las operaciones definidas en `LogRepository` utilizando SQL.

- **interfaces/**:
  - Definirá los controladores y puntos de entrada al sistema, exponiendo los endpoints relacionados con el monitoreo y salud del sistema.
  - Ejemplo:
    - **Controladores**:
      - `HealthCheckController`: Maneja las solicitudes HTTP para verificar el estado del sistema.
      - `LoggingController`: Maneja las solicitudes HTTP para gestionar logs.
    - **DTOs**: Objetos de transferencia de datos para estructurar las solicitudes y respuestas de los endpoints.

#### 7.2 - Relación con los Endpoints
##### 7.2.1 - Listado
- `/health` (GET): Verificar el estado del sistema.
- `/logs` (GET): Listar logs del sistema.
- `/logs/{id}` (GET): Obtener detalles de un log.
- `/logs` (POST): Crear un nuevo log.
- `/logs/{id}` (PUT): Modificar un log existente.
- `/logs/{id}` (DELETE): Eliminar un log.

##### 7.2.2 - Detalles
- **Verificar Estado del Sistema**:
  - Método: `GET`
  - Ruta: `/health`
  - Descripción: Devuelve el estado actual del sistema (por ejemplo, `OK` o `ERROR`).

- **Listar Logs**:
  - Método: `GET`
  - Ruta: `/logs`
  - Parámetros:
    - `level` (string, opcional): Filtrar logs por nivel (por ejemplo, `ERROR`, `WARNING`, `INFO`).
    - `from` (string, opcional): Fecha y hora de inicio para filtrar logs.
    - `to` (string, opcional): Fecha y hora de fin para filtrar logs.

- **Crear Log**:
  - Método: `POST`
  - Ruta: `/logs`
  - Parámetros:
    - `level` (string, requerido): Nivel del log (`ERROR`, `WARNING`, `INFO`).
    - `message` (string, requerido): Mensaje del log.

- **Modificar Log**:
  - Método: `PUT`
  - Ruta: `/logs/{id}`
  - Parámetros:
    - `level` (string, opcional): Nuevo nivel del log.
    - `message` (string, opcional): Nuevo mensaje del log.

- **Eliminar Log**:
  - Método: `DELETE`
  - Ruta: `/logs/{id}`
  - Parámetros:
    - `id` (int, requerido): Identificador del log.

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