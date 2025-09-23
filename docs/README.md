# Documentación del proyecto workers-api

## Índice
- [Introducción](#introducción)
- [Arquitectura general](#arquitectura-general)
- [Estructura de carpetas](#estructura-de-carpetas)
- [Principales componentes](#principales-componentes)
- [Flujos funcionales](#flujos-funcionales)
- [Endpoints principales](#endpoints-principales)
- [Base de datos](#base-de-datos)
- [Despliegue y configuración](#despliegue-y-configuración)

---

## Introducción
`workers-api` es una API desarrollada en Python con Flask, orientada a la gestión de alumnos, clases y pagos para la secretaría de una empresa educativa. Utiliza SQLAlchemy para la persistencia en MySQL y sigue una arquitectura modular por dominios.

Este proyecto aplica principios de Domain-Driven Design (DDD): el código está organizado por dominios y capas (domain, application, infrastructure, interfaces). Cada dominio agrupa su modelo, casos de uso, repositorios y rutas, lo que facilita el mantenimiento y la escalabilidad.

Dominios principales:
- `vlodeiro/empresa`: dominio responsable de la organización (empresas/academias). Aquí se gestiona el registro de empresas, la configuración global y los usuarios/roles asociados a una academia. Es el punto de entrada para operaciones de onboarding y configuración organizativa.
- `vlodeiro/secretaria`: dominio responsable de la operativa diaria de la academia (alumnos, turnos/clases, inscripciones, pagos, tarifas). Implementa los casos de uso y endpoints que realizan operaciones transaccionales y reglas de negocio.

La separación en estos dominios permite que la lógica de negocio de la secretaría evolucione independientemente de la gestión organizativa, y facilita la introducción de nuevos dominios (por ejemplo: facturación, reporting) sin mezclar responsabilidades.

## Arquitectura general
- **Flask** como framework web principal. Flask es un framework ligero de Python que permite definir rutas, manejar peticiones HTTP y construir aplicaciones web de forma sencilla y modular.
En este proyecto, toda la lógica de la API y la gestión de peticiones se basa en Flask.
- **SQLAlchemy** para ORM y acceso a base de datos MySQL. Usamos SQLAlchemy como herramienta para interactuar con la base de datos MySQL. SQLAlchemy es un ORM (Object Relational Mapper), lo que permite trabajar con la base de datos usando objetos y clases de Python en vez de escribir directamente sentencias SQL.
Así, podemos crear, consultar y modificar datos en MySQL de forma más sencilla y estructurada desde nuestro código Python.
- **Blueprints** para modularizar rutas por dominio. En Flask, los Blueprints son una forma de organizar y modularizar el código de una aplicación dividiéndolo en componentes independientes. En este proyecto, se usan Blueprints para separar las rutas (endpoints) según el dominio (por ejemplo, alumnos, clases, pagos), facilitando el mantenimiento y la escalabilidad del código.
Así, cada grupo de rutas relacionadas se gestiona en un archivo o módulo diferente, y luego se registran en la aplicación principal.
- **Separación en capas:**
  - Dominio (modelos y lógica de negocio)
  - Infraestructura (repositorios y acceso a datos)
  - Interfaces (rutas Flask)
  - Aplicación (servicios y casos de uso)

## Estructura de carpetas
```
workers-api/
├── app.py                  # Punto de entrada principal de la API
├── models.py               # Modelos globales y configuración de SQLAlchemy
├── openapi-rest.yaml       # Especificación OpenAPI REST (actual, versión pública en S3)
├── passenger_wsgi.py       # Integración con Passenger/cPanel
├── requirements.txt        # Dependencias Python
├── vlodeiro/
│   └── secretaria/
│       ├── application/    # Casos de uso y lógica de aplicación
│       ├── domain/         # Modelos de dominio (Alumno, Clase, Turno, Pago)
│       ├── infrastructure/ # Repositorios para MySQL
│       └── interfaces/     # Rutas Flask (Blueprints)
└── tmp/                    # Archivos temporales y de control
```

## Principales componentes
- **app.py:** Configura Flask, SQLAlchemy, registra blueprints y define endpoints generales.
- **models.py:** Define el objeto `db` (SQLAlchemy) y modelos globales si los hay.
- **vlodeiro/secretaria/domain/models.py:** Modelos de dominio como `Alumno`, `Clase`, `Turno`, `Pago`.
- **vlodeiro/secretaria/infrastructure/repositorio_mysql.py:** Repositorios que implementan acceso a datos usando SQLAlchemy.
- **vlodeiro/secretaria/interfaces/flask_routes.py:** Define las rutas HTTP para la secretaría usando Flask Blueprints.
- **vlodeiro/secretaria/application/**: Casos de uso y lógica de negocio (inscribir alumno, registrar pago, etc).
- **openapi-rest.yaml:** Especificación OpenAPI REST, publicada en S3 para integraciones externas y plugins (ChatGPT, Swagger UI, etc).

## Flujos funcionales
- **Gestión de alumnos:** Alta, consulta y persistencia de alumnos.
- **Gestión de clases:** Alta, consulta y persistencia de clases.
- **Gestión de turnos:** Consulta de turnos activos por empresa.
- **Gestión de pagos:** Registro y consulta de pagos de alumnos.
- **Endpoints de salud y debug:** `/health`, `/debug`, `/openapi.yml`.

## Endpoints principales (ver detalle y parámetros en openapi-rest.yaml)
- `/vlodeiro/secretaria/turnos` (GET): Lista los turnos activos.
- `/vlodeiro/secretaria/alumnos` (GET/POST): Consulta y alta de alumnos.
- `/vlodeiro/secretaria/clases` (GET/POST): Consulta y alta de clases.
- `/vlodeiro/secretaria/pagos` (GET/POST): Consulta y registro de pagos.
- `/health` (GET): Estado de la API.
- `/debug` (GET): Prueba de vida de Flask.

## Base de datos
- **MySQL** como motor principal.
- Modelos definidos con SQLAlchemy.
- Tablas principales: `alumno`, `clase`, `turno`, `pago`.

## Despliegue y configuración
- Despliegue en AWS Elastic Beanstalk (Python/Flask) y exposición pública mediante API Gateway REST.
- Especificación OpenAPI REST publicada en S3: https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- Documentación visual e interactiva (Swagger UI) usando la especificación pública de S3.
- Variables de entorno para configuración sensible (API_KEY, credenciales DB, endpoints, etc).
- Requiere instalar dependencias de `requirements.txt`.
## Referencias rápidas

- **API REST producción:** https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod
- **OpenAPI REST (YAML en S3):** https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- **Swagger UI (documentación visual):** https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- Reinicio automático tras despliegue por archivo `tmp/restart.txt`.

---

> Para detalles técnicos de cada módulo, consulta los archivos fuente en cada carpeta.
