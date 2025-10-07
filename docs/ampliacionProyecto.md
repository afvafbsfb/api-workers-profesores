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

- eliminaremos la carpeta raíz del dominio de `vlodeiro`

- Dentro de `plataforma` proponemos la siguiente estructura DDD. Para más detalles, consulta el archivo `documentacion/dominios_ddd.md`.

  

4. Modificaciones y ampliación del modelo de datos

- la definicion y creacion de la bbdd la tenemos en el fichero "create_database.sql"

- de acuerdo con la base de datos, los recursos api rest que vamos a necesitar y los roles con permiso a ellos son:

  Lista actualizada de recursos y acciones por rol
  
  System_Admin (ID: 1)

    Acceso completo a todos los recursos y acciones.
      Usaremos el comodín * para representar acceso global.

  Company_Admin (ID: 2)
    Acceso completo a los recursos a nivel de la academia con la que este vinculado.


  Staff_profesores (ID: 3)

    Recursos:
      curso: Leer.
      horario_curso: Leer.
      alumno: Leer.
      sesion: Crear, leer, actualizar.
      anotaciones_alumno_sesion: Crear, leer, actualizar, eliminar.

Propuesta resumen - trabajador virtual por plataforma

Proponemos un único trabajador virtual para la plataforma que actúe como servicio común y, al mismo tiempo, se presente de forma personalizada para cada academia: mismo motor, pero con nombre, foto y voz propia (por ejemplo “Juan” para la academia A, “Ana” para la B). Esto nos permite ofrecer una experiencia local y familiar para cada centro sin multiplicar la complejidad operativa; las academias que necesiten capacidades muy específicas podrán disponer de workers personalizados, pero la regla general será un worker común con perfiles por academia. Además, el trabajador responderá en función de quién pregunta: un administrador verá respuestas globales, mientras que un profesor o una secretaria recibirá respuestas acotadas a su academia y sus permisos.


Sección: Visión de la App Android (alto nivel)

La App Android será la interfaz móvil principal para la mayoría de usuarios. A alto nivel funcionará así:

- Pantalla de inicio / login: el usuario se autentica con su cuenta de la plataforma.

- Chat siempre disponible: tras iniciar sesión el usuario tendrá un acceso directo al trabajador virtual de la plataforma (chat permanente). El trabajador se presenta de forma personalizada según la academia (nombre, foto) y responde en función del rol y la academia del usuario.

Esta descripción es de alto nivel y no entra en detalles técnicos; su objetivo es dejar constancia de la experiencia de usuario prevista para la App móvil.
