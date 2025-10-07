# Dominios DDD del Proyecto

## Introducción
Este documento describe los dominios y subdominios identificados en el proyecto, siguiendo los principios de Domain-Driven Design (DDD). Cada dominio encapsula una parte específica del sistema, con sus propias responsabilidades y reglas de negocio.

## Dominio Principal
**Gestión de Academias**: El sistema está enfocado en la gestión de academias, proporcionando herramientas para administrar usuarios, cursos, profesores, alumnos, pagos, y otros aspectos clave.

## Subdominios
1. **Gestión de Academias**: Administración general de las academias. Alta y baja de academias, consultas.
2. **Gestión de Usuarios**: Alta, baja, modificación, consulta, autenticación, roles, permisos.
3. **Gestión de Cursos/Tarifas/Aulas/Horarios**: Administración de cursos, tarifas, asignación de aulas, horarios y profesores.
4. **Gestión de Profesores**: Asignación a cursos, gestión de sesiones, listas de asistencia, documentación y anotaciones de cada sesión.
5. **Gestión de Alumnos**: Altas, inscripciones, seguimiento académico, control de pagos.
6. **Gestión de Liquidación de Cuotas**: Liquidación mensual de cuotas.
7. **Gestión de Trabajadores Virtuales**: Vinculación con trabajadores virtuales.
8. **Monitoreo y Salud del Sistema**: Verificación del estado del sistema, logs, depuración.

## Contextos Delimitados
Cada contexto delimitado encapsula una parte del dominio y define un espacio donde las reglas, conceptos y términos tienen un significado bien definido. Los contextos delimitados identificados en este proyecto son:

1. **Gestión de Academias**: 
   - Alta, baja y consultas de academias.

2. **Gestión de Usuarios**: 
   - Alta, baja y modificación de usuarios asociados a academias.
   - Manejo de credenciales, roles y permisos.
   - Control de acceso y gestión de permisos para acceder a recursos específicos del sistema.

3. **Gestión de Cursos/Tarifas/Aulas/Horarios**: 
   - Configuración de tarifas para cursos.
   - Creación y administración de cursos.
   - Asignación de aulas y horarios a cursos.
   - Asignación de profesores a cursos específicos.

4. **Gestión de Profesores**: 
   - Registro de asistencia, documentación y anotaciones de sesiones.

5. **Gestión de Alumnos**: 
   - Registro de alumnos en cursos.
   - Gestión del progreso y desempeño de los alumnos.
   - Registro y seguimiento de pagos realizados/pendientes.

6. **Gestión de Liquidación de Cuotas**: 
   - Liquidación mensual de cuotas, simulación de liquidaciones y cancelaciones para inscripciones específicas.

7. **Gestión de Trabajadores Virtuales**: 
   - Automatización de tareas y configuración de trabajadores virtuales.

8. **Monitoreo y Salud del Sistema**: 
   - Registro de eventos y errores del sistema.
   - Endpoints para comprobar el estado del sistema.

## end-points
### 1 subdominio gestion de academias
#### 1.1 contexto delimitado Administración de academias. Listado end-points
/academies (POST, GET)
/academies/{academyId} (PUT, DELETE)
/academies/{academyId}/schedule (GET)   --horario

### 2 subdominio gestion de usuarios
#### 2.1 contexto delimitado gestion de usuarios. Listado end-point
/users (POST, GET)
/users/{userId} (PUT)
/users/{userId}/credentials (PUT)
/users/{userId}/roles  (PUT)
/users/{userId}/status (PUT)

/academies/{academyId}/users (GET) (filtro opcional ?roles=Profesor_academia,Admin_y_profesor_academia)

/academies/{academyId}/users/{userId} (POST|DELETE) (vincular / desvincular usuario a la academia)


#### 2.1 contexto delimitado autenticacion. Listado end-points
POST /auth/login → inicia sesión; devuelve accessToken (corto) y refreshToken (largo). Registra en UserLoginLog (success/fail), actualiza failed_login_count/locked_until en fallos.

POST /auth/refresh → rota refresh: crea nuevo RefreshToken, marca revoked_at y replaced_by_id del anterior; emite nuevo accessToken.

POST /auth/logout → revoca el RefreshToken usado (revoked_at) y cierra sesión en UserLoginLog.logout_at.

POST /auth/recover → inicia recuperación (email/username); genera token de un solo uso y envía enlace. Responde 200 genérico.

POST /auth/reset → establece nueva contraseña con token; al cambiar password o estado incrementa Usuario.token_version.

GET /auth/me → perfil del usuario autenticado (id, email, roles efectivos, flags).

POST /auth/mfa/challenge / POST /auth/mfa/verify → (opcional) segundo factor.

Notas

accessToken corto (p.ej. 15 min); refreshToken ~30–90 días (persistido como hash).

Incluir token_version en el JWT; si cambia en DB, invalidas todos los tokens previos.


#### 2.2 contexto delimitado Gestión de Permisos y Autorización sobre recursos de API
CRUD de roles/permisos fuera del API (DB directa). La autorización debe ejecutarse en middleware/policies usando los claims del JWT y la tabla de permisos (cacheada). No llamaremos a un endpoint externo por cada request.

Recomendado (interno-only, si eliges PDP centralizado):
/authz/decision (POST) → { subject, action, resource } ⇒ { effect: ALLOW|DENY }

/authz/cache/refresh (POST) (sincronizar permisos en caché)

Aclaración: No expongas CRUD público de roles/permissions. Log de auditoría puedes reutilizar /logs.

### 3 subdominio gestion de Cursos/Tarifas/Aulas/Horarios
#### 3.1 contexto delimitado Tarifas. Listado end-point

/academies/{academyId}/tariffs (GET, POST)
/tariffs/{tariffId} (GET, PUT)

#### 3.2 contexto delimitado Cursos. Listado end-point

/academies/{academyId}/courses (GET, POST)
/courses/{courseId} (GET, PUT)

#### 3.3 contexto delimitado Aulas. Listado end-point

/academies/{academyId}/classrooms (GET, POST)
/classrooms/{classroomId} (GET, PUT, DELETE)

#### 3.4 contexto delimitado Horarios. Listado end-point
/courses/{courseId}/schedule (GET|POST)  --consulta y alta de horario
/courses/{courseId}/schedule/{scheduleId} (GET|PUT|DELETE) -- de cada registro del horario


### 4 subdominio gestion de Profesores
#### 4.1 contexto delimitado Profesores. Listado end-point
/professors/{professorId}/schedule (GET)

/professors/{professorId}/courses/{courseId}/sessions (GET, POST)

/sessions/{sessionId} (GET, PUT)

/sessions/{sessionId}/students/{studentId}/annotations (POST)

/professors/{professorId}/courses/{courseId}/annotations (GET, con filtro tipo)

/professors/{professorId}/courses/{courseId}/students/{studentId}/annotations (GET, con filtro tipo)

/annotations/{annotationId} (GET, PUT)


### 5 subdominio gestion de alumnos
#### 5.1 contexto delimitado gestion de alumnos. Listado end-points

/academies/{academyId}/students (POST, GET)

/students/{studentId} (GET, PUT)

#### 5.2 contexto delimitado Incripcion de alumnos
/students/{studentId}/inscripcions (POST, GET)

/inscripcions/{inscripcionId} (GET, PUT)
/inscripcions/{inscripcionId}/progress (GET) -- opcion filtro por tipo de anotacion

#### 5.2 contexto delimitado movimientos pagos
/inscripcions/{inscripcionId}/movements (GET, POST)
/movements/{movementId} (PUT)
/inscripcions/{inscripcionId}/extract (GET)
/extract/{extractId} (GET)
/extract/{extractId}/movements (GET)

### 6 subdominio gestion liquidacion de cuotas
#### 6.1 contexto liquidaciones. Listado end-points
/courses/{courseId}/liquidacionMensual (POST)
/inscripcions/{inscripcionId}/simulacionLiquidacion (GET)
/inscripcions{inscripcionId}/simulacionCancelacion (GET)
/inscripcions/{inscripcionId}/cancelacion (GET)

### 7 subdominio trabajadores virtuales
Existe 1 trabajador virtual que es el worker administrativo que será el mismo worker para todas las academias, pero cada academia le puede cambiar su nombre, su foto. 
#### 7.1 contexto trabajadores virtuales. Listado end-points
/academies/{academyId}/virtualworkers (GET, POST)
/virtualworkers/{virtualWorkerId} (GET, PUT, DELETE)

### 8 subdominio Monitoreo y Salud del Sistema
#### 8.1 contexto Health & Logs
/health (GET)
/logs (GET, POST)
/logs/{id} (GET, PUT, DELETE)

## Estructura de carpetas 
src/
├── academias/                # Contexto delimitado: Gestión de Academias
│   ├── application/          # Servicios de aplicación (coordinan operaciones del dominio)
│   ├── domain/               # Lógica de negocio pura (entidades, agregados, repositorios)
│   ├── infrastructure/       # Implementaciones técnicas (bases de datos, APIs externas)
│   └── interfaces/           # Controladores y puntos de entrada (endpoints HTTP, DTOs)
│
├── usuarios/                 # Contexto delimitado: Gestión de Usuarios
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── cursos/                   # Contexto delimitado: Gestión de Cursos/Tarifas/Aulas/Horarios
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── profesores/               # Contexto delimitado: Gestión de Profesores
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── alumnos/                  # Contexto delimitado: Gestión de Alumnos
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── cuotas/                   # Contexto delimitado: Gestión de Liquidación de Cuotas
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── trabajadores_virtuales/   # Contexto delimitado: Gestión de Trabajadores Virtuales
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
├── monitoreo/                # Contexto delimitado: Monitoreo y Salud del Sistema
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── interfaces/
│
└── shared/                   # Código compartido entre contextos
    ├── utils/                # Utilidades generales
    ├── exceptions/           # Excepciones comunes
    ├── middleware/           # Middleware compartido
    └── events/               # Eventos compartidos entre contextos