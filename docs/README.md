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

## Arquitectura general
- **Flask** como framework web principal.
- **SQLAlchemy** para ORM y acceso a base de datos MySQL.
- **Blueprints** para modularizar rutas por dominio.
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
├── openapi.yml             # Especificación OpenAPI de la API
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

## Flujos funcionales
- **Gestión de alumnos:** Alta, consulta y persistencia de alumnos.
- **Gestión de clases:** Alta, consulta y persistencia de clases.
- **Gestión de turnos:** Consulta de turnos activos por empresa.
- **Gestión de pagos:** Registro y consulta de pagos de alumnos.
- **Endpoints de salud y debug:** `/health`, `/debug`, `/openapi.yml`.

## Endpoints principales
- `/vlodeiro/secretaria/turnos` (GET): Lista los turnos activos.
- `/vlodeiro/secretaria/alumnos` (GET/POST): Consulta y alta de alumnos.
- `/vlodeiro/secretaria/clases` (GET/POST): Consulta y alta de clases.
- `/vlodeiro/secretaria/pagos` (GET/POST): Consulta y registro de pagos.
- `/v1/command` (POST): Endpoint genérico para comandos autenticados.
- `/health` (GET): Estado de la API.
- `/debug` (GET): Prueba de vida de Flask.

## Base de datos
- **MySQL** como motor principal.
- Modelos definidos con SQLAlchemy.
- Tablas principales: `alumno`, `clase`, `turno`, `pago`.

## Despliegue y configuración
- Despliegue automatizado vía `.cpanel.yml` y Passenger en cPanel.
- Variables de entorno para configuración sensible (API_KEY, credenciales DB).
- Requiere instalar dependencias de `requirements.txt`.
- Reinicio automático tras despliegue por archivo `tmp/restart.txt`.

---

> Para detalles técnicos de cada módulo, consulta los archivos fuente en cada carpeta.
