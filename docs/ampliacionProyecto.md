Ampliación del proyecto — Resumen de cambios propuestos

1. Nuevos roles

- System_Admin: Administrador global del sistema. Tiene permisos para crear academias, gestionar cualquier recurso en cualquier academia y asignar roles.

- Company_Admin: Administrador con ámbito a una academia concreta. Puede gestionar todos los recursos dentro de su academia (cursos, turnos, usuarios de la academia, etc.). Debe estar vinculado a 1 academia.

- Staff_secretaria: Rol limitado a las tareas diarias de secretaria (gestión de inscripciones, atención administrativa, gestión de horarios y comunicaciones administrativas dentro de la academia).

- Staff_profesores: Rol que agrupa las operaciones propias del profesorado (gestionar contenidos, consultoría de horarios, evaluación y tareas del profesor). Detalle de las tareas a definir en iteraciones posteriores.

2. Nuevos usuarios y casos especiales

- Cada usuario de la plataforma tendrá una cuenta en `users` y podrá vincularse a uno o varios roles mediante `user_roles`.

- Caso especial: academias con una sola persona. Esta persona podrá recibir múltiples roles (Company_Admin + Staff_secretaria + Staff_profesores) para evitar crear múltiples cuentas. Reglas operativas:

  - Un único usuario puede tener varias asociaciones en `user_roles` (por ejemplo, Company_Admin y Staff_secretaria para la misma academia).

  - La capacidad real para hacer una acción vendrá determinada en tiempo de ejecución por la comprobación del rol relevante y el `academy_id` en el `user_roles`.

  - La creación de nuevas academias estará restringida a `System_Admin` (o a un flujo de onboarding controlado que cree la primera academia y asigne roles iniciales).

3. Renombrado de carpetas y nuevas subcarpetas

- Cambiar la carpeta raíz del dominio de `vlodeiro` a `plataforma`.

- Dentro de `plataforma` proponemos la siguiente estructura DDD:

  - `plataforma/academia/creation`: Módulo responsable de la creación y gestión de academias, onboarding y asignación inicial de roles y permisos.

  - `plataforma/operativa/profesores`: Módulo responsable de las funcionalidades específicas de los profesores (gestión de horarios, contenidos y demás operaciones propias de la operativa docente).

4. Modificaciones y ampliación del modelo de datos

- [Se deja este apartado vacío deliberadamente para revisar la BBDD antes de documentar cambios concretos.]


Notas finales

Este documento recoge los acuerdos preliminares y las decisiones de alto nivel para la ampliación del proyecto. En los siguientes pasos se generarán las migraciones, los modelos/entidades, el middleware de autorización y los endpoints necesarios. Se recomienda crear tests de autorización y flujos de onboarding para academias de una sola persona.

Estructura DDD propuesta (layout de carpetas)

La siguiente estructura muestra cómo organizar los límites de contexto y los módulos según DDD. Cada carpeta representa un contexto con su propia capa de API, servicios, repositorios, modelos y pruebas.

plataforma/
  academia/
    creation/                # Onboarding y creación de academias
      api/                    # Controllers / Blueprints / Endpoints
      service/                # Lógica de dominio y casos de uso (crear, editar, asignar roles)
      repository/             # Repositorios / DAOs / persistence
      model/                  # Entidades del dominio (Academia, OnboardingProcess)
      tests/                  # Unit/integration tests
    management/               # Operaciones administrativas de plataforma (listas, búsqueda, auditoría)
      api/
      service/
      repository/
      tests/

  usuarios/                  # Gestión global de usuarios y autenticación
    api/                      # login, logout, refresh token, endpoints de perfil
    service/                  # creación de usuarios, reset password, verificación
    repository/
    model/                    # User, Role (si no están en el bounded context de datos compartidos)
    tests/

operativa/
  profesores/               # Funcionalidad operativa del profesorado
    api/                     # Endpoints para profesores (horarios, contenidos, evaluaciones)
    service/                 # Casos de uso (gestionar horario, subir contenido, evaluar)
    repository/
    model/                   # Entidades propias del profesor (Profile, Availability, CourseMaterial)
    tests/
  secretaria/               # Operativa administrativa de la academia
    api/
    service/
    repository/
    model/                   # Entidades para secretaria (Inscripcion, Comunicacion, Agenda)
    tests/

shared/                     # Componentes reutilizables y librerías internas
  auth/                      # Middleware de autenticación, JWT helpers
  db/                        # Migrations, shared repositories o helpers de persistencia
  events/                    # Event bus, integración entre contextos
  dto/                       # DTOs compartidos entre módulos
  utils/                     # Utilidades comunes

Notas sobre la organización
- Cada bounded context contiene su propia carpeta `api`, `service`, `repository`, `model` y `tests` para mantener las responsabilidades separadas.
- `shared` contiene infraestructuras que se usan transversalmente (auth, migraciones, utilidades).
- El renombrado físico en el repo moverá `vlodeiro/empresa` y `vlodeiro/secretaria` a `plataforma/academia` y `operativa/secretaria` respectivamente, y añadirá `plataforma/academia/creation` y `operativa/profesores` como nuevas carpetas.
- Mantener interfaces claras entre contextos (ej: contratos HTTP o eventos). Evitar acoplamientos directos a las entidades de otro contexto; usar DTOs o repositorios compartidos en `shared/db`.

Propuesta resumen - trabajador virtual por plataforma

Proponemos un único trabajador virtual para la plataforma que actúe como servicio común y, al mismo tiempo, se presente de forma personalizada para cada academia: mismo motor, pero con nombre, foto y voz propia (por ejemplo “Juan” para la academia A, “Ana” para la B). Esto nos permite ofrecer una experiencia local y familiar para cada centro sin multiplicar la complejidad operativa; las academias que necesiten capacidades muy específicas podrán disponer de workers personalizados, pero la regla general será un worker común con perfiles por academia. Además, el trabajador responderá en función de quién pregunta: un administrador verá respuestas globales, mientras que un profesor o una secretaria recibirá respuestas acotadas a su academia y sus permisos.

