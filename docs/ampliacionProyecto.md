Ampliación del proyecto — Resumen de cambios propuestos

Este documento recoge los acuerdos preliminares y las decisiones de alto nivel para la ampliación del proyecto. En los siguientes pasos se generarán las migraciones, los modelos/entidades, el middleware de autorización y los endpoints necesarios. Se recomienda crear tests de autorización y flujos de onboarding para academias de una sola persona.

1. Nuevos roles

- System_Admin: Administrador global del sistema. Tiene permisos para crear academias, gestionar cualquier recurso en cualquier academia.

- Company_Admin: Administrador con ámbito a una academia concreta. Puede gestionar todos los recursos dentro de su academia (cursos, turnos, usuarios de la academia, gestión de inscripciones, atención administrativa, gestión de horarios y comunicaciones administrativas dentro de la academia, etc.). Debe estar vinculado a 1 academia.

- Staff_profesores: Rol que agrupa las operaciones propias del profesorado (gestionar contenidos, consultoría de horarios, evaluación y tareas del profesor). Detalle de las tareas a definir en iteraciones posteriores.

2. Nuevos usuarios y casos especiales

Cada usuario de la plataforma tendrá una cuenta en `users` y estará vinculado a un único rol (representado en `user_roles` o en la tabla de usuarios según la implementación).

-- Caso especial: academias con una sola persona. Aunque técnicamente es posible asignar varios roles, la recomendación operativa es asignar únicamente el rol `Company_Admin` al usuario único de la academia y nosotros en este api por tanto solo permitiremos 1 rol por usuario. 

Motivos:

  - `Company_Admin` engloba las capacidades necesarias para gestionar la academia (crear cursos, gestionar turnos, administrar usuarios y tareas operativas), evitando la necesidad de múltiples cuentas.
  - Simplifica la gestión de permisos y evita ambigüedades en la UX cuando un mismo usuario actúa con varios perfiles.

Reglas operativas:

  - Por diseño operativo, cada usuario tendrá un único rol; en academias de una sola persona ese rol será `Company_Admin`.

  - La capacidad real para hacer una acción vendrá determinada en tiempo de ejecución por la comprobación del rol relevante y del recurso que se quiere usar en `permisosrol`.

  - La creación de nuevas academias estará restringida a `System_Admin` par crear la academia y asigne roles y usuarios.

3. Renombrado de carpetas y nuevas subcarpetas

- Cambiar la carpeta raíz del dominio de `vlodeiro` a `plataforma`.

- Dentro de `plataforma` proponemos la siguiente estructura DDD. Para más detalles, consulta el archivo `documentacion/estructura_ddd.md`.

  - `plataforma/academia/creation`: Módulo responsable de la creación y gestión de academias, onboarding y asignación inicial de roles y permisos.

  - `plataforma/operativa/administradores`: Módulo responsable de las funcionalidades específicas de los administradores de la academia (gestión de horarios, contenidos y demás operaciones propias de la operativa administrativa).

  - `plataforma/operativa/profesores`: Módulo responsable de las funcionalidades específicas de los profesores (gestión de clases, contenidos y demás operaciones propias de la operativa del profesor).

4. Modificaciones y ampliación del modelo de datos

- la definicion y creacion de la bbdd la tenemos en el fichero "create_database.sql"

- de acuerdo con la base de datos, los recursos api rest que vamos a necesitar y los reoles con permiso a ellos son:

  Lista actualizada de recursos y acciones por rol
  
  System_Admin (ID: 1)

    Acceso completo a todos los recursos y acciones.
      Usaremos el comodín * para representar acceso global.

  Company_Admin (ID: 2)

    Recursos:
      academia: Leer, actualizar.

      tarifa: Crear, leer, actualizar, eliminar.
      curso: Crear, leer, actualizar, eliminar.
      aula: Crear, leer, actualizar, eliminar.
      horario_curso: Crear, leer, actualizar, eliminar.
      alumno: Crear, leer, actualizar, eliminar.
      inscripcion: Crear, leer, actualizar, eliminar.

      rol_usuario: Leer.
      usuario: Crear, leer, actualizar, eliminar.
      permisosrol: Leer.

      sesion: Crear, leer, actualizar, eliminar.
      descuentos_tarifa: Crear, leer, actualizar, eliminar.
      familias_alumnos: Crear, leer, actualizar, eliminar.
      anotaciones_alumno_sesion: Crear, leer, actualizar, eliminar.
      pago: Crear, leer, actualizar, eliminar.

      trabajador_virtual: leer, actualizar.

  Staff_profesores (ID: 3)

    Recursos:
      curso: Leer.
      horario_curso: Leer.
      alumno: Leer.
      sesion: Crear, leer, actualizar.
      anotaciones_alumno_sesion: Crear, leer, actualizar, eliminar.





Estructura DDD propuesta (layout de carpetas)

La siguiente estructura muestra cómo organizar los límites de contexto y los módulos según DDD. Cada carpeta representa un contexto con su propia capa de API, servicios, repositorios, modelos y pruebas.

plataforma/
  academia/
    creation/                # Creación de academias
      api/                    # Controllers / Blueprints / Endpoints
      service/                # Lógica de dominio y casos de uso (crear, editar, asignar roles)
      repository/             # Repositorios / DAOs / persistence
      model/                  # Entidades del dominio (Academia)
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
  administrativos/               # Operativa administrativa de la academia
    api/
    service/
    repository/
    model/                   # Entidades para administrativos (Inscripcion, Comunicacion, Agenda)
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
- El renombrado físico en el repo moverá `vlodeiro/empresa` y `vlodeiro/secretaria` a `plataforma/academia` y `operativa/administrativo` respectivamente, y añadirá `plataforma/academia/creation` y `operativa/profesores` como nuevas carpetas.
- Mantener interfaces claras entre contextos (ej: contratos HTTP o eventos). Evitar acoplamientos directos a las entidades de otro contexto; usar DTOs o repositorios compartidos en `shared/db`.

Propuesta resumen - trabajador virtual por plataforma

Proponemos un único trabajador virtual para la plataforma que actúe como servicio común y, al mismo tiempo, se presente de forma personalizada para cada academia: mismo motor, pero con nombre, foto y voz propia (por ejemplo “Juan” para la academia A, “Ana” para la B). Esto nos permite ofrecer una experiencia local y familiar para cada centro sin multiplicar la complejidad operativa; las academias que necesiten capacidades muy específicas podrán disponer de workers personalizados, pero la regla general será un worker común con perfiles por academia. Además, el trabajador responderá en función de quién pregunta: un administrador verá respuestas globales, mientras que un profesor o una secretaria recibirá respuestas acotadas a su academia y sus permisos.


Sección: Visión de la App Android (alto nivel)

La App Android será la interfaz móvil principal para la mayoría de usuarios. A alto nivel funcionará así:

- Pantalla de inicio / login: el usuario se autentica con su cuenta de la plataforma.

- Chat siempre disponible: tras iniciar sesión el usuario tendrá un acceso directo al trabajador virtual de la plataforma (chat permanente). El trabajador se presenta de forma personalizada según la academia (nombre, foto) y responde en función del rol y la academia del usuario.

Esta descripción es de alto nivel y no entra en detalles técnicos; su objetivo es dejar constancia de la experiencia de usuario prevista para la App móvil.
